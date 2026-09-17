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
from detector_core.matching import EvidenceScanner, normalize_text
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

    def test_registry_is_57_agents_and_four_rule_fields(self):
        self.assertEqual(len(self.registry.catalog), 57)
        for tool, entry in self.registry.catalog.items():
            self.assertEqual(
                set(entry),
                {"name", "author_patterns", "text_patterns", "branch_patterns", "label_patterns"},
                tool,
            )
        expected_empty = {
            "Baidu Comate", "DeepSeek Harness", "MiMo Code", "MiniMax Code",
            "Plandex", "Verdent", "Huawei CodeArts", "iFlow CLI",
        }
        actual_empty = {
            tool for tool, entry in self.registry.catalog.items()
            if not any(entry[k] for k in ("author_patterns", "text_patterns", "branch_patterns", "label_patterns"))
        }
        self.assertEqual(actual_empty, expected_empty)

    def test_excluded_candidates_are_not_in_strict_catalog(self):
        removed = (
            "Generic AI", "ChatGPT", "Factory", "CodeRabbit", "PR-Agent", "Qodo",
            "Sourcery", "Serena", "Rulesync", "SpecKit", "Taskmaster", "Superpowers",
            "Specstory", "Tessl", "Paperclip", "DeepSource Autofix", "Fly", "GPT-Engineer",
        )
        for name in removed:
            self.assertNotIn(name, self.registry.catalog)

    def test_canonical_product_names_work_only_in_attribution_grammar(self):
        examples = {
            "Generated with Pi": "Pi",
            "Implemented by Cursor": "Cursor",
            "Written using Copilot": "Copilot",
            "Created via Gemini CLI": "Gemini",
            "Made with Continue": "Continue",
            "Generated with ZCode": "ZCode",
            "Generated with Trae": "Trae",
            "Assisted by Qoder": "Qoder",
            "Developed with Amazon Q Developer": "Amazon Q",
        }
        for text, tool in examples.items():
            with self.subTest(text=text):
                self.assertIn(tool, self.scan(text)[0]["tools"])

        for text in (
            "Raspberry Pi support",
            "Move the cursor left",
            "Please continue processing",
            "Run codegen before build",
            "Factory pattern cleanup",
            "Use Gemini 2.5 Pro API",
            "Developed with Fly",
            "Coded by Codegen Agent",
            "Generated by Warp Agent Mode",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")

    def test_model_names_are_not_standalone_text_rules(self):
        for text in (
            "Generated with Claude Opus 4.6",
            "Generated with GPT-5.3-Codex",
            "Generated with DeepSeek-R1",
            "Generated with Kimi K3",
            "Generated with MiMo-v2.5-pro",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "no_trace_detected")

    def test_model_family_name_does_not_stand_in_for_agent_surface(self):
        self.assertEqual(self.scan("Generated with Gemini 2.5 Pro")[0]["status"], "no_trace_detected")
        self.assertEqual(self.scan("Generated with Gemini")[0]["status"], "no_trace_detected")
        self.assertIn("Gemini", self.scan("Generated with Gemini CLI")[0]["tools"])
        self.assertIn("Gemini", self.scan("Generated with Gemini Code Assist")[0]["tools"])

    def test_structured_model_identity_is_allowed_for_claude(self):
        summary, rows = self.author_scan(
            login="claude", name="Claude Opus 4.6", email="noreply@anthropic.com"
        )
        self.assertIn("Claude Code", summary["tools"])
        self.assertEqual(rows[0]["field"], "author_identity")
        self.assertIn("noreply@anthropic.com", rows[0]["excerpt"])

        human, _ = self.author_scan(
            login="alice", name="Claude Opus 4.6", email="alice@example.com"
        )
        self.assertNotIn("Claude Code", human["tools"])

    def test_fable_is_in_claude_structured_identity_family(self):
        summary, rows = self.author_scan(
            login="claude", name="Claude Fable 5", email="noreply@anthropic.com"
        )
        self.assertIn("Claude Code", summary["tools"])
        self.assertTrue(any("Fable" in row["excerpt"] for row in rows if row["tool"] == "Claude Code"))

        coauthor = "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
        summary, rows = self.scan(coauthor, source="commit", field="message")
        self.assertIn("Claude Code", summary["tools"])
        self.assertTrue(any("Fable" in row["excerpt"] for row in rows if row["tool"] == "Claude Code"))

    def test_author_identity_is_one_normalized_field(self):
        summary, rows = self.author_scan(
            login="copilot-swe-agent[bot]", name="Copilot", email="copilot@github.com"
        )
        self.assertIn("Copilot", summary["tools"])
        copilot_rows = [r for r in rows if r["tool"] == "Copilot"]
        self.assertGreaterEqual(len(copilot_rows), 2)
        self.assertTrue(all(r["field"] == "author_identity" for r in copilot_rows))
        self.assertIn("copilot-swe-agent[bot] | Copilot <copilot@github.com>", copilot_rows[0]["excerpt"])

    def test_human_name_collision_does_not_make_pi_author(self):
        summary, _ = self.author_scan(login="alice", name="Pi", email="human@example.com")
        self.assertNotIn("Pi", summary["tools"])

    def test_coauthor_is_just_another_global_text_attribution_prefix(self):
        text = "Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
        for source, field in (("commit", "message"), ("pr", "body_markdown")):
            with self.subTest(source=source):
                summary, rows = self.scan(text, source=source, field=field)
                self.assertIn("Claude Code", summary["tools"])
                hits = [row for row in rows if row["tool"] == "Claude Code"]
                self.assertGreaterEqual(len(hits), 1)
                self.assertTrue(all(row["rule"] == "text_attribution" for row in hits))

    def test_coauthor_uses_exactly_the_same_substring_pattern_logic_as_other_text(self):
        text = "Co-Authored-By: Amazon Q Developer"
        summary, rows = self.scan(text, source="commit", field="message")
        self.assertIn("Amazon Q", summary["tools"])
        details = {r["detail"] for r in rows if r["tool"] == "Amazon Q"}
        self.assertEqual(details, {"text_pattern:Amazon Q Developer"})

        # Accepted limitation of the deliberately simple unified text matcher:
        # a short ambiguous pattern is not rescued by hidden email/name semantics.
        pi_human = "Co-Authored-By: Pi <human@example.com>"
        self.assertIn("Pi", self.scan(pi_human, source="commit", field="message")[0]["tools"])

    def test_no_coauthor_specific_matcher_remains_in_core(self):
        matching_source = (ROOT / "scripts" / "detector_core" / "matching.py").read_text(encoding="utf-8")
        registry_source = (ROOT / "scripts" / "detector_core" / "registry.py").read_text(encoding="utf-8")
        combined = matching_source + "\n" + registry_source
        for forbidden in (
            "COAUTHOR =",
            "coauthor_matches",
            "render_coauthor",
            "_structured_text_pattern",
            "text_coauthor",
        ):
            self.assertNotIn(forbidden, combined)

    def test_task_url_channel_is_removed(self):
        for text in (
            "https://chatgpt.com/codex/tasks/task_123",
            "See [the task](https://chatgpt.com/codex/tasks/task_123)",
        ):
            with self.subTest(text=text):
                summary, rows = self.scan(text)
                self.assertEqual(summary["status"], "no_trace_detected")
                self.assertEqual(rows, [])

    def test_minimal_markdown_link_normalization_and_surrounding_text(self):
        cases = (
            "Most changes were generated with Claude Code",
            "🤖 Generated with Claude Code",
            "Generated with [Cursor](https://cursor.com)",
            "Developed with the help of CodeBuddy",
            "Developed with assistance from CodeBuddy",
        )
        for text in cases:
            with self.subTest(text=text):
                self.assertEqual(self.scan(text)[0]["status"], "agent_trace_detected")

        # No general Markdown wrapper stripping: the only normalization kept in
        # this candidate is [visible text](URL) -> visible text (URL).
        self.assertEqual(self.scan("Generated with **Codex**")[0]["status"], "no_trace_detected")
        self.assertEqual(
            normalize_text("Generated with [Claude Code](https://claude.com/claude-code)"),
            "Generated with Claude Code (https://claude.com/claude-code)",
        )

    def test_negation_is_deliberately_not_semantically_parsed(self):
        self.assertIn("Codex", self.scan("This PR was not generated with Codex")[0]["tools"])

    def test_overlapping_patterns_are_all_emitted_for_audit(self):
        summary, rows = self.scan("Co-Authored-By: Amp <amp@ampcode.com>", source="commit", field="message")
        self.assertIn("Amp", summary["tools"])
        hits = [r for r in rows if r["tool"] == "Amp" and r["rule"] == "text_attribution"]
        details = {r["detail"] for r in hits}
        self.assertIn("text_pattern:Amp", details)
        self.assertIn(r"text_pattern:Amp <amp@ampcode\.com>", details)
        self.assertGreaterEqual(len(hits), 2)

    def test_branch_and_label_channels(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.metadata("codex/fix", "branches", 1, "head_ref_name")
        scanner.metadata("codex", "labels", 1, "name")
        summary = scanner.summary()
        self.assertIn("Codex", summary["tools"])
        self.assertTrue(summary["metadata_agent_trace"])
        self.assertEqual({r["rule"] for r in rows}, {"branch", "label"})

    def test_actor_attribution(self):
        target, _ = self.scan("Generated with Codex", actor=2)
        other, _ = self.scan("Generated with Codex", actor=99)
        unknown, _ = self.scan("Generated with Codex", actor=None)
        self.assertTrue(target["target_author_agent_trace"])
        self.assertFalse(target["other_actor_agent_trace"])
        self.assertTrue(other["other_actor_agent_trace"])
        self.assertFalse(other["target_author_agent_trace"])
        self.assertTrue(unknown["unknown_actor_agent_trace"])

    def test_non_agent_bot_identity_produces_no_trace(self):
        summary, rows = self.author_scan(login="dependabot[bot]", name="dependabot[bot]")
        self.assertEqual(summary["status"], "no_trace_detected")
        self.assertEqual(summary["tools"], [])
        self.assertEqual(rows, [])

    def test_coding_agent_bot_identity_still_matches(self):
        summary, _ = self.author_scan(login="factory-droid[bot]", name="factory-droid[bot]")
        self.assertIn("Factory Droid", summary["tools"])

    def test_unknown_bot_author_does_not_stop_text_scan(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.identity(
            {"login": "some-new-bot[bot]", "email": "", "name": ""},
            "commit", "a", "login", "email", "name", 2,
        )
        scanner.text("Generated with Codex", "commit", "a", "message", 2)
        self.assertIn("Codex", scanner.summary()["tools"])

    def test_normalize_text_preserves_non_link_characters_and_urls(self):
        self.assertEqual(normalize_text("Generated with future_agent"), "Generated with future_agent")
        self.assertEqual(normalize_text("Generated with future~agent"), "Generated with future~agent")
        self.assertEqual(
            normalize_text("Generated with [Cursor](https://cursor.com)"),
            "Generated with Cursor (https://cursor.com)",
        )

    def test_powered_is_not_an_attribution_verb(self):
        self.assertEqual(self.scan("Powered by Continue")[0]["status"], "no_trace_detected")

    def test_known_noisy_patterns_are_tightened_without_special_case_logic(self):
        self.assertNotIn("Cline", self.author_scan(login="alice", name="Dan Cline", email="a@example.com")[0]["tools"])
        self.assertEqual(self.scan("Generated by Codegen")[0]["status"], "no_trace_detected")
        self.assertEqual(self.scan("Generated by Sweep")[0]["status"], "no_trace_detected")
        self.assertEqual(self.scan("Generated by Jules")[0]["status"], "no_trace_detected")
        self.assertEqual(self.scan("Generated by Warp")[0]["status"], "no_trace_detected")
        self.assertEqual(self.scan("Generated by Warp Agent Mode")[0]["status"], "no_trace_detected")
        self.assertIn(
            "Warp",
            self.scan("Co-Authored-By: Warp <agent@warp.dev>", source="commit", field="message")[0]["tools"],
        )

    def test_branch_path_segment_boundary_is_explicit(self):
        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.metadata("feature/nottrae/agent-123", "branches", 1, "head_ref_name")
        self.assertNotIn("Trae", scanner.summary()["tools"])

        rows2 = []
        scanner2 = EvidenceScanner(self.registry, rows2.append)
        scanner2.begin({"pr_id": 2, "target_author_id": 2})
        scanner2.metadata("user/trae/agent-123", "branches", 2, "head_ref_name")
        self.assertIn("Trae", scanner2.summary()["tools"])


    def test_devin_final_natural_text_rule_is_simple_and_name_safe(self):
        for text in (
            "Generated with Devin",
            "Generated with Devin.",
            "Generated with Devin:",
            "Generated with [Devin](https://devin.ai)",
            "Generated with Devin (Cognition AI)",
        ):
            with self.subTest(text=text):
                self.assertIn("Devin", self.scan(text)[0]["tools"])
        for text in (
            "Generated with Devin Stewart",
            "Generated with Devin Slauenwhite",
            "Generated with Devin (Cognition AI).",
        ):
            with self.subTest(text=text):
                self.assertNotIn("Devin", self.scan(text)[0]["tools"])

    def test_lovable_current_and_historical_author_identities(self):
        current, _ = self.author_scan(login="lovable-dev[bot]", name="lovable-dev[bot]")
        historical, _ = self.author_scan(
            login="gpt-engineer-app[bot]",
            name="gpt-engineer-app[bot]",
            email="159125892+gpt-engineer-app[bot]@users.noreply.github.com",
        )
        generic_old, _ = self.author_scan(login="gpt-engineer", name="GPT Engineer")
        self.assertIn("Lovable", current["tools"])
        self.assertIn("Lovable", historical["tools"])
        self.assertNotIn("Lovable", generic_old["tools"])

    def test_roomote_is_separate_from_historical_roo_code(self):
        roomote, _ = self.author_scan(login="roomote-roomote[bot]", name="roomote-roomote")
        roo, _ = self.author_scan(login="roomote", name="Roo Code", email="roomote@roocode.com")
        self.assertIn("Roomote", roomote["tools"])
        self.assertNotIn("Roo Code", roomote["tools"])
        self.assertIn("Roo Code", roo["tools"])

    def test_warp_oz_identity_is_explicit_not_email_substring_accident(self):
        oz, _ = self.author_scan(login="oz-agent", name="Oz", email="oz-agent@warp.dev")
        warp, _ = self.author_scan(login="warp-agent", name="Warp Agent", email="agent@warp.dev")
        accidental, _ = self.author_scan(login="other", name="Other", email="not-agent@warp.dev")
        self.assertIn("Warp", oz["tools"])
        self.assertIn("Warp", warp["tools"])
        self.assertNotIn("Warp", accidental["tools"])

    def test_new_frozen_author_and_branch_signatures(self):
        seer, _ = self.author_scan(login="seer-by-sentry[bot]", name="seer-by-sentry[bot]")
        replit, _ = self.author_scan(login="replit-agent", name="Replit Agent")
        self.assertIn("Sentry Seer", seer["tools"])
        self.assertIn("Replit Agent", replit["tools"])

        rows = []
        scanner = EvidenceScanner(self.registry, rows.append)
        scanner.begin({"pr_id": 1, "target_author_id": 2})
        scanner.metadata("seer/fix/example", "branches", 1, "head_ref_name")
        self.assertIn("Sentry Seer", scanner.summary()["tools"])

    def test_zcode_is_intentionally_active_from_v33_evidence(self):
        self.assertIn("ZCode", self.scan("Generated with ZCode")[0]["tools"])


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
            c.execute("UPDATE pr_commits SET message='Generated with Codex',author_user_login=NULL,author_name=NULL,committed_date=NULL WHERE pr_id=1")
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
