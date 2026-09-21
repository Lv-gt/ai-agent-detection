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
from detector_core.matching import EvidenceScanner, normalize_target, normalize_text
from detector_core.registry import Registry
from detector_core.util import readonly


def fixture(root):
    root.mkdir()
    c = sqlite3.connect(root / "pr_agent_inputs.sqlite3")
    c.executescript("""
    CREATE TABLE target_prs(
        pr_id INTEGER PRIMARY KEY,repo_id INTEGER,pr_number INTEGER,expected_author_id INTEGER,
        collection_status TEXT
    );
    CREATE TABLE pr_details(
        pr_id INTEGER PRIMARY KEY,repo_id INTEGER,pr_number INTEGER,author_database_id INTEGER,
        author_login TEXT,author_name TEXT,author_email TEXT,body_markdown TEXT,head_ref_name TEXT
    );
    CREATE TABLE pr_commits(
        pr_id INTEGER,sha TEXT,message TEXT,author_name TEXT,author_email TEXT,
        author_user_login TEXT,author_user_database_id INTEGER,
        PRIMARY KEY(pr_id,sha)
    );
    CREATE TABLE pr_labels(pr_id INTEGER,name TEXT,PRIMARY KEY(pr_id,name));
    CREATE TABLE pr_label_events(
        pr_id INTEGER,ordinal INTEGER,label_name TEXT,created_at TEXT,actor_database_id INTEGER,
        PRIMARY KEY(pr_id,ordinal)
    );
    """)
    bodies = [
        "Generated with Kimi Code",
        "https://chatgpt.com/codex/tasks/task_123",
        "Support Qwen Code models",
        "",
        "Generated with Claude Code",
        "Generated with Lingma",
    ]
    for i in range(1, 7):
        repo, author = ((10, 20) if i <= 2 else (10, 21) if i <= 4 else (11, 22))
        unavailable = i == 5
        status = "terminal_unavailable" if unavailable else "completed"
        c.execute(
            "INSERT INTO target_prs VALUES(?,?,?,?,?)",
            (i, repo, i, author, status),
        )
        if not unavailable:
            c.execute(
                "INSERT INTO pr_details VALUES(?,?,?,?,?,?,?,?,?)",
                (i, repo, i, author, "renamed-user", "Human", None, bodies[i - 1], "feature"),
            )
            c.execute(
                "INSERT INTO pr_commits VALUES(?,?,?,?,?,?,?)",
                (i, "sha" + str(i), "plain change", "Human", None, "human", author),
            )
    c.commit()
    c.close()


class Rules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = Registry()

    def scan(self, body, actor=2, source="pr", field="body_markdown"):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.text(body, source, 1, field, actor)
        return scanner.summary(), rows

    def author_scan(self, login="", name="", email="", actor=2):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.identity(
            {"login": login, "name": name, "email": email},
            "commit", "sha", "login", "email", "name", actor,
        )
        return scanner.summary(), rows

    def test_registry_inventory_is_exact(self):
        self.assertEqual(len(self.registry.catalog), 56)
        self.assertEqual(self.registry.counts, {
            "agents": 56,
            "identity": 150,
            "branch": 13,
            "label": 2,
            "raw_message_signature": 2,
            "agent_specific": 165,
            "complete_executable_inventory": 167,
        })
        self.assertTrue(all(any((
            entry["identity_patterns"], entry["branch_patterns"],
            entry["label_patterns"], entry["raw_message_signatures"],
        )) for entry in self.registry.catalog.values()))

    def test_registry_has_only_new_rule_fields(self):
        for tool, entry in self.registry.catalog.items():
            self.assertEqual(set(entry), {
                "name", "identity_patterns", "branch_patterns", "label_patterns", "raw_message_signatures"
            }, tool)
        source = (ROOT / "scripts/detector_core/registry.py").read_text(encoding="utf-8")
        self.assertNotIn("author_patterns", source)
        self.assertNotIn("text_patterns", source)

    def test_excluded_candidates_are_not_in_catalog(self):
        for name in (
            "Baidu Comate", "Generic AI", "ChatGPT", "Factory", "CodeRabbit", "PR-Agent", "Qodo",
            "Sourcery", "Serena", "Rulesync", "SpecKit", "Taskmaster", "Superpowers",
            "Specstory", "Tessl", "Paperclip", "DeepSource Autofix", "Fly", "GPT-Engineer",
        ):
            self.assertNotIn(name, self.registry.catalog)

    def test_global_grammar_inventory(self):
        grammar = self.registry.grammar
        for verb in ("built", "made", "coded", "produced", r"co(?:[ \t]+|-)?authored", r"co(?:[ \t]+|-)?developed"):
            self.assertIn(verb, grammar["verb_patterns"])
        self.assertEqual(grammar["connectors"], ["by", "with", "using", "via"])
        self.assertEqual(grammar["hyphenated_prefixes"], ["generated-by", "co-authored-by", "co-developed-by"])
        self.assertEqual(grammar["bridge_patterns"], [
            r"assistance[ \t]+from", r"the[ \t]+assistance[ \t]+of",
            r"help[ \t]+from", r"the[ \t]+help[ \t]+of",
        ])

    def test_basic_attribution_uses_shared_identity_table(self):
        examples = {
            "Generated with ZCode": "ZCode",
            "Implemented by Cursor": "Cursor",
            "Authored with Kiro": "Kiro",
            "Developed using Claude Code": "Claude Code",
            "Written via Qoder": "Qoder",
            "Built by Augment Code": "Augment Code",
            "Made with Continue": "Continue",
            "Coded using Windsurf": "Windsurf",
            "Produced by ZCode": "ZCode",
            "Assisted by Junie": "Junie",
        }
        for text, tool in examples.items():
            with self.subTest(text=text):
                summary, rows = self.scan(text)
                self.assertIn(tool, summary["tools"])
                self.assertIn("identity", summary["categories"])
                self.assertTrue(any(r["rule"] == "attribution" for r in rows if r["tool"] == tool))

    def test_optional_colon_is_implemented_in_matcher(self):
        for text in (
            "Generated by ZCode", "Generated by: ZCode",
            "Generated-by ZCode", "Generated-by: ZCode",
            "Co-authored by Kiro", "Co-authored by: Kiro",
            "Co-authored-by Kiro", "Co-authored-by: Kiro",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "agent_trace_detected")
        rules = json.loads((ROOT / "config/rules/agents.json").read_text(encoding="utf-8"))
        self.assertNotIn("colon_pattern", rules["attribution_grammar"])
        self.assertNotIn("optional_colon", rules["attribution_grammar"])

    def test_coauthored_and_codeveloped_variants(self):
        for text in (
            "Co-authored with Kiro",
            "Co authored with Kiro",
            "Coauthored by Kiro",
            "Co developed using Claude Code",
            "Codeveloped via Qoder",
            "Co-developed-by: Qoder <noreply@qoder.com>",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "agent_trace_detected")

    def test_bridge_patterns_are_consumed_before_target(self):
        examples = {
            "Authored with assistance from Codex": "Codex",
            "Developed with the assistance of Junie": "Junie",
            "Built with help from Qoder": "Qoder",
            "Built with the help of Augment Code": "Augment Code",
        }
        for text, tool in examples.items():
            with self.subTest(text=text):
                summary, rows = self.scan(text)
                self.assertIn(tool, summary["tools"])
                self.assertTrue(any(f"identity_pattern:{tool}" in r["detail"] or r["tool"] == tool for r in rows))

    def test_markdown_link_normalization_preserves_target_start(self):
        summary, _ = self.scan("Generated with [Cursor](https://cursor.com)")
        self.assertIn("Cursor", summary["tools"])
        self.assertEqual(
            normalize_text("Generated with [Cursor](https://cursor.com)"),
            "Generated with Cursor (https://cursor.com)",
        )

    def test_outer_markdown_emphasis_is_removed_from_target(self):
        for text in (
            "Generated with **Cursor**",
            "Generated with __Cursor__",
            "Generated with *Cursor*",
            "Generated with _Cursor_",
            "Generated with ***Cursor***",
            "Generated with **Cursor** assistance",
        ):
            with self.subTest(text=text):
                self.assertIn("Cursor", self.scan(text)[0]["tools"])
        self.assertEqual(normalize_target("**Cursor** assistance"), "Cursor assistance")
        self.assertEqual(self.scan("Generated with `Cursor`")[0]["status"], "no_trace_detected")

    def test_attribution_prefix_requires_a_separator(self):
        for text in (
            "Generated withCodex",
            "Generated byCodex",
            "Generated-byCodex",
            "Co-developed-byQoder",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")
        for text in (
            "Generated with Codex",
            "Generated with:Codex",
            "Generated with : Codex",
            "Generated-by:ZCode",
            "Co-developed-by:Qoder",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "agent_trace_detected")

    def test_native_identity_and_attribution_share_same_patterns(self):
        native, native_rows = self.author_scan(name="ZCode", email="noreply@z.ai")
        text, text_rows = self.scan("Generated with ZCode")
        self.assertIn("ZCode", native["tools"])
        self.assertIn("ZCode", text["tools"])
        self.assertTrue(any(r["detail"].startswith("identity_pattern:ZCode") for r in native_rows))
        self.assertTrue(any(r["detail"].startswith("identity_pattern:ZCode") for r in text_rows))

    def test_rendered_identity_is_login_pipe_name_email(self):
        summary, rows = self.author_scan(
            login="copilot-swe-agent[bot]", name="Copilot", email="copilot@github.com"
        )
        self.assertIn("Copilot", summary["tools"])
        self.assertTrue(all(r["field"] == "author_identity" for r in rows if r["tool"] == "Copilot"))
        self.assertTrue(any("copilot-swe-agent[bot] | Copilot <copilot@github.com>" in r["excerpt"] for r in rows))

    def test_plain_mentions_do_not_trigger_text_identity(self):
        for text in (
            "Support Qwen Code models",
            "Cursor integration docs",
            "Raspberry Pi support",
            "https://chatgpt.com/codex/tasks/task_123",
            "Powered by Continue",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")

    def test_unregistered_model_names_do_not_trigger(self):
        for text in (
            "Generated with Claude Opus 4.6",
            "Generated with GPT-5.3-Codex",
            "Generated with DeepSeek-R1",
            "Generated with Kimi K3",
            "Generated with Gemini 2.5 Pro",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")

    def test_raw_message_signatures_are_identity_evidence(self):
        cases = {
            "🤖 Plandex → implement parser": "Plandex",
            "Replit-Commit-Author: Agent": "Replit Agent",
        }
        for message, tool in cases.items():
            with self.subTest(message=message):
                summary, rows = self.scan(message, source="commit", field="message")
                self.assertIn(tool, summary["tools"])
                self.assertEqual(summary["categories"], ["identity"])
                hit = [r for r in rows if r["tool"] == tool]
                self.assertTrue(hit)
                self.assertTrue(all(r["rule"] == "raw_message_signature" for r in hit))

    def test_raw_message_signatures_are_commit_message_only(self):
        for message in ("🤖 Plandex → implement parser", "Replit-Commit-Author: Agent"):
            with self.subTest(message=message):
                self.assertEqual(self.scan(message, source="pr", field="body_markdown")[0]["status"], "no_trace_detected")

    def test_overlapping_identity_patterns_are_all_emitted(self):
        summary, rows = self.scan("Co-developed-by: Qoder <noreply@qoder.com>", source="commit", field="message")
        self.assertIn("Qoder", summary["tools"])
        details = {r["detail"] for r in rows if r["tool"] == "Qoder"}
        self.assertTrue(any("identity_pattern:Qoder;" in d for d in details))
        self.assertTrue(any(r"identity_pattern:Qoder <noreply@qoder\.com>" in d for d in details))

    def test_branch_and_label_channels(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.metadata("codex/fix", "branches", 1, "head_ref_name")
        scanner.metadata("codex", "labels", 1, "name")
        summary = scanner.summary()
        self.assertIn("Codex", summary["tools"])
        self.assertEqual(set(summary["categories"]), {"branch", "label"})
        self.assertTrue(summary["metadata_agent_trace"])
        self.assertEqual({r["rule"] for r in rows}, {"branch", "label"})

    def test_branch_path_segment_boundary_is_explicit(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.metadata("feature/nottrae/agent-123", "branches", 1, "head_ref_name")
        self.assertNotIn("Trae", scanner.summary()["tools"])
        scanner.metadata("user/trae/agent-123", "branches", 1, "head_ref_name")
        self.assertIn("Trae", scanner.summary()["tools"])

    def test_actor_attribution_for_identity_evidence(self):
        target, _ = self.scan("Generated with Codex", actor=2)
        other, _ = self.scan("Generated with Codex", actor=99)
        unknown, _ = self.scan("Generated with Codex", actor=None)
        self.assertTrue(target["target_author_agent_trace"])
        self.assertTrue(other["other_actor_agent_trace"])
        self.assertTrue(unknown["unknown_actor_agent_trace"])

    def test_non_agent_bot_identity_produces_no_trace(self):
        summary, rows = self.author_scan(login="dependabot[bot]", name="dependabot[bot]")
        self.assertEqual(summary["status"], "no_trace_detected")
        self.assertEqual(rows, [])

    def test_known_coding_agent_identities_match(self):
        examples = (
            ("factory-droid[bot]", "", "", "Factory Droid"),
            ("seer-by-sentry[bot]", "", "", "Sentry Seer"),
            ("replit-agent", "Replit Agent", "", "Replit Agent"),
            ("lovable-dev[bot]", "", "", "Lovable"),
        )
        for login, name, email, tool in examples:
            with self.subTest(tool=tool):
                self.assertIn(tool, self.author_scan(login, name, email)[0]["tools"])

    def test_no_old_reverse_text_matching_logic_remains(self):
        matching_source = (ROOT / "scripts/detector_core/matching.py").read_text(encoding="utf-8")
        registry_source = (ROOT / "scripts/detector_core/registry.py").read_text(encoding="utf-8")
        combined = matching_source + "\n" + registry_source
        for forbidden in ("ATTRIBUTION_PHRASE", "text_matches", "author_matches", "author_patterns", "text_patterns"):
            self.assertNotIn(forbidden, combined)
        self.assertIn("attribution_targets", combined)
        self.assertIn("identity_matches", combined)

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
            light = preflight(source)
            deep = preflight(source, deep_check=True)
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
            self.assertTrue((root / "4" / "exports" / "pr_results.csv.gz").exists())
            with readonly(root / "4" / "detection.sqlite3") as c:
                payload = json.loads(c.execute("SELECT payload FROM pr_results WHERE pr_id=4").fetchone()[0])
                self.assertNotIn("candidate_count", payload)
                self.assertNotIn("accepted_count", payload)

    def test_result_payload_carries_only_detection_conclusions(self):
        expected = {
            "pr_id", "repo_id", "pr_number", "target_author_id", "collection_status", "status",
            "tools", "categories", "evidence_count", "unavailable_reason",
            "target_author_agent_trace", "target_author_tools",
            "other_actor_agent_trace", "other_actor_tools",
            "unknown_actor_agent_trace", "unknown_actor_tools",
            "metadata_agent_trace", "metadata_tools",
        }
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "input"; fixture(source)
            with readonly(source / "pr_agent_inputs.sqlite3") as c:
                scanner = EvidenceScanner(Registry(), lambda row: None)
                result = detect_one(c, c.execute("SELECT * FROM target_prs WHERE pr_id=1").fetchone(), scanner)
        self.assertEqual(set(result), expected)

    def test_evidence_carries_no_per_run_duplicates(self):
        expected = {
            "pr_id", "rule", "tool", "source_kind", "source_object_id", "field", "line",
            "excerpt", "detail", "actor_id", "actor_relation", "event_time",
        }
        rows = []
        scanner = EvidenceScanner(Registry(), rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.text("Generated with Codex", "commit", "sha", "message", 2)
        self.assertEqual(set(rows[0]), expected)

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
            c.execute(
                "UPDATE pr_commits SET message='Generated with Codex',"
                "author_user_login=NULL,author_name=NULL WHERE pr_id=1"
            )
            c.commit(); c.close()
            with readonly(source / "pr_agent_inputs.sqlite3") as c:
                scanner = EvidenceScanner(Registry(), lambda row: None)
                result = detect_one(c, c.execute("SELECT * FROM target_prs WHERE pr_id=1").fetchone(), scanner)
                self.assertIn("Codex", result["tools"])
                self.assertEqual(result["status"], "agent_trace_detected")

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
