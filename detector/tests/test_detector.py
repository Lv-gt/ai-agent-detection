import ast
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from detector_core.input_db import detect_one, preflight
from detector_core.matching import EvidenceScanner, attribution_line
from detector_core.registry import Registry
from detector_core.util import readonly


def fixture(root):
    root.mkdir()
    c = sqlite3.connect(root / "pr_agent_inputs.sqlite3")
    c.executescript("""
    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE target_prs(
        pr_id INTEGER PRIMARY KEY,repo_id INTEGER,pr_number INTEGER,expected_author_id INTEGER,
        collection_status TEXT,commit_total_count INTEGER,commit_observed_count INTEGER,
        commit_observation_status TEXT,label_observed_count INTEGER,label_event_observed_count INTEGER
    );
    CREATE TABLE pr_details(
        pr_id INTEGER PRIMARY KEY,repo_id INTEGER,pr_number INTEGER,author_database_id INTEGER,
        author_login TEXT,author_name TEXT,author_email TEXT,body_markdown TEXT,head_ref_name TEXT,
        created_at TEXT,collected_at_utc TEXT
    );
    CREATE TABLE pr_commits(
        pr_id INTEGER,ordinal INTEGER,sha TEXT,message TEXT,author_name TEXT,author_email TEXT,
        author_user_login TEXT,author_user_database_id INTEGER,committed_date TEXT,
        PRIMARY KEY(pr_id,ordinal)
    );
    CREATE TABLE pr_labels(pr_id INTEGER,ordinal INTEGER,name TEXT,PRIMARY KEY(pr_id,ordinal));
    CREATE TABLE pr_label_events(
        pr_id INTEGER,ordinal INTEGER,label_name TEXT,created_at TEXT,actor_database_id INTEGER,
        PRIMARY KEY(pr_id,ordinal)
    );
    """)
    c.execute("INSERT INTO metadata VALUES('schema_version','standalone-test')")
    bodies = [
        "Generated with Kimi Code",
        "https://chatgpt.com/codex/tasks/task_123",
        "Support Qwen Code models",
        "",
        "Generated with Claude Code",
        "Generated with Alibaba Lingma",
    ]
    for i in range(1, 7):
        repo, author = ((10, 20) if i <= 2 else (10, 21) if i <= 4 else (11, 22))
        unavailable = i == 5
        status = "terminal_unavailable" if unavailable else "completed"
        obs = "incomplete" if i == 4 else "complete"
        c.execute(
            "INSERT INTO target_prs VALUES(?,?,?,?,?,?,?,?,?,?)",
            (i, repo, i, author, status, 1, 1, obs, 0, 0),
        )
        if not unavailable:
            c.execute(
                "INSERT INTO pr_details VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (i, repo, i, author, "renamed-user", "Human", None, bodies[i - 1], "feature",
                 "2026-01-01T00:00:00Z", "2026-09-01T00:00:00Z"),
            )
            c.execute(
                "INSERT INTO pr_commits VALUES(?,?,?,?,?,?,?,?,?)",
                (i, 1, "sha" + str(i), "plain change", "Human", None, "human", author,
                 "2026-01-01T00:00:00Z"),
            )
    c.commit()
    c.close()


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def scan(self, body, actor=2):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.text(body, "pr", 1, "body_markdown", actor)
        return scanner.summary(), rows

    def test_added_agent_text_aliases(self):
        names = [
            "Kimi Code", "Kimi CLI", "Qwen Code", "CodeBuddy", "Trae", "Alibaba Lingma",
            "Baidu Comate", "MiMo Code", "MiniMax Code", "OpenCode",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(self.scan("Generated with " + name)[0]["status"], "agent_trace_detected")

    def test_plain_mentions_and_model_only_are_ignored(self):
        for text in ("Support Kimi Code", "Generated with GLM-5", "Generated with DeepSeek", "Generated with ChatGPT", "Generated with AI"):
            with self.subTest(text=text):
                summary, rows = self.scan(text)
                self.assertEqual(summary["status"], "no_trace_detected")
                self.assertEqual(rows, [])

    def test_r3_matches_basic_attribution_phrase_in_surrounding_text(self):
        expected = {
            "Most changes were generated with Claude Code": "Claude Code",
            "This PR was generated with Kimi Code": "Kimi Code",
            "This PR was not generated with Codex": "Codex",
        }
        for text, tool in expected.items():
            with self.subTest(text=text):
                self.assertIn(tool, self.scan(text)[0]["tools"])

    def test_no_section_level_context_parser(self):
        # There is deliberately no section-level semantic parser. A matching
        # attribution phrase is detected even under an Examples heading.
        summary, rows = self.scan("# Examples\nGenerated with Kimi Code")
        self.assertIn("Kimi Code", summary["tools"])
        self.assertTrue(rows)
        self.assertNotIn("accepted", rows[0])
        self.assertNotIn("reason", rows[0])

    def test_task_url_validation(self):
        self.assertIn("Codex", self.scan("https://chatgpt.com/codex/tasks/task_123")[0]["tools"])
        bad = [
            "http://chatgpt.com/codex/tasks/task_123",
            "https://chatgpt.com.evil.test/codex/tasks/123",
            "https://chatgpt.com/codex/tasks/",
            "https://user@chatgpt.com/codex/tasks/123",
        ]
        for url in bad:
            with self.subTest(url=url):
                self.assertEqual(self.scan(url)[0]["status"], "no_trace_detected")

    def test_task_url_preserves_literal_characters_and_markdown_targets(self):
        url = "https://chatgpt.com/codex/tasks/task_123"
        summary, rows = self.scan(url)
        self.assertIn("Codex", summary["tools"])
        r4 = [row for row in rows if row["rule"] == "R4"]
        self.assertEqual(r4[0]["detail"], url)
        self.assertEqual(r4[0]["excerpt"], url)

        for text in (
            f"[Open task]({url})",
            f"See [the task]({url}) for details",
        ):
            with self.subTest(text=text):
                summary, rows = self.scan(text)
                self.assertIn("Codex", summary["tools"])
                r4 = [row for row in rows if row["rule"] == "R4"]
                self.assertEqual(r4[0]["detail"], url)

    def test_r3_format_normalization_preserves_literal_underscore_and_tilde(self):
        self.assertEqual(attribution_line("Generated with future_agent"), "Generated with future_agent")
        self.assertEqual(attribution_line("Generated with future~agent"), "Generated with future~agent")
        self.assertEqual(attribution_line("https://example.com/~user/task_123"), "https://example.com/~user/task_123")

    def test_r3_common_markdown_line_prefixes(self):
        for text in (
            "- Generated with Claude Code",
            "+ Generated with Claude Code",
            "* Generated with Claude Code",
            "1. Generated with Claude Code",
            "2) Generated with Claude Code",
            "> Generated with Claude Code",
            "> - Generated with Claude Code",
        ):
            with self.subTest(text=text):
                self.assertIn("Claude Code", self.scan(text)[0]["tools"])

    def test_r3_decorative_footer_prefixes_preserve_original_evidence(self):
        for text in (
            "🤖 Generated with Claude Code",
            "✨ Generated with Claude Code",
            "> 🤖 Generated with Claude Code",
            "- 🤖 Generated with Claude Code",
        ):
            with self.subTest(text=text):
                summary, rows = self.scan(text)
                self.assertIn("Claude Code", summary["tools"])
                r3 = [row for row in rows if row["rule"] == "R3"]
                self.assertTrue(r3)
                self.assertEqual(r3[0]["excerpt"], text)

    def test_r3_does_not_require_end_of_line_after_agent_name(self):
        self.assertIn("Claude Code", self.scan("Generated with Claude Code - verified")[0]["tools"])

    def test_multi_tool_and_markdown_link(self):
        self.assertEqual(len(self.scan("Generated with Kimi Code\nGenerated with Qwen Code")[0]["tools"]), 2)
        self.assertIn("Claude Code", self.scan("Generated with [Claude Code](https://claude.ai/code)")[0]["tools"])
        self.assertIn("Codex", self.scan("Generated with **Codex**")[0]["tools"])

    def test_non_agent_registry_items_are_removed(self):
        self.assertIn("ChatGPT", self.registry.identity(name="ChatGPT"))
        self.assertFalse(self.registry.identity(name="AI Assistant"))
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.metadata("ai-generated", "labels", 1, "name")
        self.assertEqual(scanner.summary()["status"], "no_trace_detected")
        for text in (
            "Generated with ChatGPT",
            "Generated with Rulesync",
            "Generated with SpecKit",
            "Generated with Taskmaster",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")
        for removed in ("Generic", "Rulesync", "SpecKit", "Taskmaster"):
            self.assertNotIn(removed, self.registry.catalog)

    def test_literal_identity_behavior(self):
        r = self.registry
        self.assertIn("Codex", r.identity(name="Codex (gpt-5.2-codex)"))
        self.assertTrue(r.identity(login="factory-droid[bot]"))
        self.assertFalse(r.identity(email="codex@openaiXcom"))
        self.assertFalse(r.identity(name="Jean-Claude Martin"))
        self.assertFalse(r.identity(name="Claude"))

    def test_structured_identity_remains_broader_than_free_text(self):
        r = self.registry
        self.assertIn("Claude Code", r.identity(name="Claude Sonnet 4.5"))
        self.assertIn("Copilot", r.identity(login="copilot-swe-agent[bot]"))
        self.assertIn("Gemini", r.identity(login="gemini-cli"))
        self.assertIn("Gemini", r.identity(name="Gemini 2.5 Pro"))
        self.assertIn("Cursor", r.identity(email="cursoragent@cursor.com"))
        self.assertIn("Qwen Coder", r.identity(login="qwen-coder"))

        # The same broad brand/model names are deliberately not R3 text aliases.
        for text in (
            "Generated with Claude",
            "Generated with Copilot",
            "Generated with Gemini",
            "Generated with Cursor",
            "Generated with Qwen Coder",
        ):
            self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")

    def test_coauthor(self):
        self.assertIn("Claude Code", self.scan("Co-Authored-By: Claude <noreply@anthropic.com>")[0]["tools"])

    def test_broad_brand_or_model_names_are_not_text_evidence(self):
        cases = [
            "Generated with Claude",
            "Generated with Copilot",
            "Generated with Gemini",
            "Generated with Cursor",
            "Generated with Qwen Coder",
        ]
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")

    def test_agent_specific_text_names_are_detected(self):
        expected = {
            "Generated with Claude Code": "Claude Code",
            "Generated with GitHub Copilot Coding Agent": "Copilot",
            "Generated with Copilot cloud agent": "Copilot",
            "Generated with Gemini CLI": "Gemini",
            "Generated with Gemini Code Assist agent mode": "Gemini",
            "Generated with Cursor Agent": "Cursor",
            "Generated with Cursor Cloud Agent": "Cursor",
            "Generated with Qwen Code": "Qwen Code",
        }
        for text, tool in expected.items():
            with self.subTest(text=text):
                self.assertIn(tool, self.scan(text)[0]["tools"])

    def test_actor_attribution(self):
        target, _ = self.scan("Generated with Codex", actor=2)
        other, _ = self.scan("Generated with Codex", actor=99)
        unknown, _ = self.scan("Generated with Codex", actor=None)
        self.assertTrue(target["target_author_agent_trace"])
        self.assertFalse(target["other_actor_agent_trace"])
        self.assertTrue(other["other_actor_agent_trace"])
        self.assertFalse(other["target_author_agent_trace"])
        self.assertTrue(unknown["unknown_actor_agent_trace"])

    def test_metadata_not_personal_attribution(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.metadata("codex/fix", "branches", 1, "head_ref_name")
        result = scanner.summary()
        self.assertTrue(result["metadata_agent_trace"])
        self.assertFalse(result["target_author_agent_trace"])

    def test_non_agent_automation_is_neutral(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.identity(
            {"login": "dependabot[bot]", "email": "", "name": "dependabot[bot]"},
            "commit", "a", "login", "email", "name", 2,
        )
        result = scanner.summary()
        self.assertEqual(result["status"], "no_trace_detected")
        self.assertEqual(result["known_non_agent_automation_actor_count"], 1)

    def test_coding_agent_bot_takes_precedence(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.identity(
            {"login": "factory-droid[bot]", "email": "", "name": "factory-droid[bot]"},
            "commit", "a", "login", "email", "name", 2,
        )
        result = scanner.summary()
        self.assertIn("Factory Droid", result["tools"])
        self.assertEqual(result["known_non_agent_automation_actor_count"], 0)

    def test_unknown_bot_is_neutral_and_does_not_stop_text_scan(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.identity(
            {"login": "some-new-bot[bot]", "email": "", "name": ""},
            "commit", "a", "login", "email", "name", 2,
        )
        scanner.text("Generated with Codex", "commit", "a", "message", 2)
        result = scanner.summary()
        self.assertIn("Codex", result["tools"])
        self.assertEqual(result["unknown_bot_actor_count"], 1)


class Pipeline(unittest.TestCase):
    def command(self, *args, ok=True):
        process = subprocess.run(
            [sys.executable, str(ROOT / "scripts/cli.py"), *map(str, args)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90,
        )
        if ok:
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        else:
            self.assertNotEqual(process.returncode, 0, process.stdout + process.stderr)
        return process

    def test_preflight_and_deep_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"
            fixture(source)
            light = preflight(source, Registry().config)
            deep = preflight(source, Registry().config, deep_check=True)
            self.assertEqual(light["target_count"], 6)
            self.assertEqual(light["input_integrity"], "not_run")
            self.assertEqual(deep["input_integrity"], "ok")

    def test_end_to_end_parallel_resume_audit_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"
            fixture(source)
            for workers in (1, 4):
                self.command("detect", source, root / str(workers), "--workers", workers, "--shard-size", 2)

            def rows(out):
                with readonly(out / "detection.sqlite3") as c:
                    return [tuple(r) for r in c.execute("SELECT * FROM pr_results ORDER BY pr_id")]

            self.assertEqual(rows(root / "1"), rows(root / "4"))
            resumed = self.command("detect", source, root / "4", "--workers", 4, "--shard-size", 2)
            self.assertIn("Detection 3/3 shards", resumed.stdout)
            self.command("audit", root / "4")
            self.command("export", root / "4")
            self.assertTrue((root / "4" / "exports" / "pr_labels.csv.gz").exists())
            with readonly(root / "4" / "detection.sqlite3") as c:
                payload = json.loads(c.execute("SELECT payload FROM pr_results WHERE pr_id=4").fetchone()[0])
                self.assertEqual(payload["commit_observation_status"], "incomplete")
                self.assertNotIn("candidate_count", payload)
                self.assertNotIn("accepted_count", payload)

    def test_sample_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"
            fixture(source)
            self.command("detect", source, root / "out", "--sample-size", 2, "--workers", 1)
            with readonly(root / "out" / "detection.sqlite3") as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM pr_results").fetchone()[0], 2)

    def test_noncompleted_pr_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"
            fixture(source)
            self.command("detect", source, root / "out", "--workers", 1)
            with readonly(root / "out" / "detection.sqlite3") as c:
                self.assertEqual(c.execute("SELECT status FROM pr_results WHERE pr_id=5").fetchone()[0], "unavailable")

    def test_pr_author_and_body_target_attribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"
            fixture(source)
            c = sqlite3.connect(source / "pr_agent_inputs.sqlite3")
            c.execute("UPDATE pr_details SET author_database_id=NULL,body_markdown='Generated with Codex' WHERE pr_id=1")
            c.commit(); c.close()
            with readonly(source / "pr_agent_inputs.sqlite3") as c:
                scanner = EvidenceScanner(Registry(), lambda row: None)
                result = detect_one(c, c.execute("SELECT * FROM target_prs WHERE pr_id=1").fetchone(), scanner)
                self.assertTrue(result["target_author_agent_trace"])
                self.assertTrue(result["author_identity_missing"])

    def test_other_commit_actor_is_not_attributed_to_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"
            fixture(source)
            c = sqlite3.connect(source / "pr_agent_inputs.sqlite3")
            c.execute("UPDATE pr_details SET body_markdown='' WHERE pr_id=1")
            c.execute(
                "UPDATE pr_commits SET message='Generated with Codex',author_user_database_id=999 WHERE pr_id=1"
            )
            c.commit(); c.close()
            with readonly(source / "pr_agent_inputs.sqlite3") as c:
                scanner = EvidenceScanner(Registry(), lambda row: None)
                result = detect_one(c, c.execute("SELECT * FROM target_prs WHERE pr_id=1").fetchone(), scanner)
                self.assertTrue(result["other_actor_agent_trace"])
                self.assertFalse(result["target_author_agent_trace"])

    def test_historical_label_events_are_not_part_of_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"
            fixture(source)
            c = sqlite3.connect(source / "pr_agent_inputs.sqlite3")
            c.execute("UPDATE pr_details SET body_markdown='' WHERE pr_id=1")
            c.execute("INSERT INTO pr_label_events VALUES(1,1,'codex','2026-01-01T00:00:00Z',20)")
            c.commit(); c.close()
            with readonly(source / "pr_agent_inputs.sqlite3") as c:
                scanner = EvidenceScanner(Registry(), lambda row: None)
                result = detect_one(c, c.execute("SELECT * FROM target_prs WHERE pr_id=1").fetchone(), scanner)
                self.assertEqual(result["status"], "no_trace_detected")

    def test_lock_prevents_two_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"; fixture(source)
            out = root / "out"; out.mkdir()
            (out / ".running.lock").write_text("busy", encoding="utf-8")
            self.command("detect", source, out, "--workers", 1, ok=False)

    def test_resume_after_interruption(self):
        from unittest.mock import patch
        from detector_core import runner
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"; fixture(source)
            out = root / "out"
            original = runner.work

            def interrupted(job):
                if job[2] == 1:
                    raise KeyboardInterrupt()
                return original(job)

            with patch.object(runner, "work", side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    runner.run(source, out, workers=1, shard_size=2)
            self.assertFalse((out / ".running.lock").exists())
            self.assertTrue((out / "shards" / "0000000.done.json").exists())
            self.command("detect", source, out, "--workers", 4, "--shard-size", 2)

    def test_corrupted_completed_shard_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"; fixture(source)
            out = root / "out"
            self.command("detect", source, out, "--workers", 1)
            shard = out / "shards" / "0000000.results.jsonl"
            shard.write_text(shard.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
            self.command("detect", source, out, "--workers", 1, ok=False)

    def test_changed_source_is_rejected_for_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"; fixture(source)
            out = root / "out"
            self.command("detect", source, out, "--workers", 1)
            c = sqlite3.connect(source / "pr_agent_inputs.sqlite3")
            c.execute("UPDATE pr_details SET body_markdown='Generated with Codex' WHERE pr_id=3")
            c.commit(); c.close()
            self.command("detect", source, out, "--workers", 1, ok=False)

    def test_numeric_identity_conflict_blocks_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "input"; fixture(source)
            c = sqlite3.connect(source / "pr_agent_inputs.sqlite3")
            c.execute("UPDATE pr_details SET author_database_id=999 WHERE pr_id=1")
            c.commit(); c.close()
            self.command("detect", source, root / "out", "--workers", 1, ok=False)
            self.assertFalse((root / "out" / "detection.sqlite3").exists())

    def test_null_fields_skip_only_that_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"; fixture(source)
            c = sqlite3.connect(source / "pr_agent_inputs.sqlite3")
            c.execute("UPDATE pr_details SET body_markdown=NULL,head_ref_name=NULL,author_login=NULL WHERE pr_id=1")
            c.execute("UPDATE pr_commits SET message='Generated with Codex',author_user_login=NULL,author_name=NULL,committed_date=NULL WHERE pr_id=1")
            c.execute("UPDATE target_prs SET label_observed_count=NULL,commit_total_count=10000 WHERE pr_id=1")
            c.commit(); c.close()
            with readonly(source / "pr_agent_inputs.sqlite3") as c:
                scanner = EvidenceScanner(Registry(), lambda row: None)
                result = detect_one(c, c.execute("SELECT * FROM target_prs WHERE pr_id=1").fetchone(), scanner)
                self.assertIn("Codex", result["tools"])
                self.assertEqual(result["commit_observed_count"], 1)

    def test_no_network_or_hash_imports(self):
        forbidden = {"requests", "httpx", "urllib.request", "hashlib"}
        for path in (ROOT / "scripts").rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    self.assertFalse(forbidden & {alias.name for alias in node.names})
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, forbidden)


if __name__ == "__main__":
    unittest.main()
