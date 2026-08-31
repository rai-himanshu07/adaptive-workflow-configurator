from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from workflow_configurator import core
from workflow_configurator.analysis import collect_mcp_security


def upstream_payloads() -> dict[str, bytes]:
    current_revision = "b" * 40
    commit_tree_sha = "c" * 40
    reviewed = {
        "sha": "d" * 40,
        "truncated": False,
        "tree": [
            {
                "path": "skills/codebase-memory-mcp/SKILL.md",
                "type": "blob",
                "sha": "1" * 40,
            },
            {
                "path": "skills/mcp-security-audit/SKILL.md",
                "type": "blob",
                "sha": "2" * 40,
            },
            {
                "path": "agents/existing.agent.md",
                "type": "blob",
                "sha": "3" * 40,
            },
            {
                "path": "plugins/removed/plugin.json",
                "type": "blob",
                "sha": "4" * 40,
            },
        ],
    }
    current = {
        "sha": current_revision,
        "truncated": False,
        "tree": [
            {
                "path": "skills/codebase-memory-mcp/SKILL.md",
                "type": "blob",
                "sha": "5" * 40,
            },
            {
                "path": "skills/mcp-security-audit/SKILL.md",
                "type": "blob",
                "sha": "2" * 40,
            },
            {
                "path": "agents/existing.agent.md",
                "type": "blob",
                "sha": "6" * 40,
            },
            {
                "path": "skills/new-skill/SKILL.md",
                "type": "blob",
                "sha": "7" * 40,
            },
        ],
    }
    commit = {
        "sha": current_revision,
        "commit": {
            "committer": {"date": "2026-08-31T00:00:00Z"},
            "tree": {"sha": commit_tree_sha},
        },
    }
    return {
        "current_commit": json.dumps(commit).encode(),
        "current_tree": json.dumps(current).encode(),
        "reviewed_tree": json.dumps(reviewed).encode(),
    }


def blob_payload(sha: str, content: str) -> bytes:
    encoded = content.encode("utf-8")
    return json.dumps(
        {
            "sha": sha,
            "size": len(encoded),
            "encoding": "base64",
            "content": base64.b64encode(encoded).decode("ascii"),
        }
    ).encode("utf-8")


class UpstreamTrackingTests(unittest.TestCase):
    def test_delta_report_is_metadata_only_deduplicated_and_cacheable(self) -> None:
        checked = datetime(2026, 8, 31, tzinfo=timezone.utc)
        report = core.build_upstream_report(
            upstream_payloads(),
            checked_at=checked,
        )
        self.assertEqual("review-required", report.status)
        self.assertEqual(4, report.pending_count)
        self.assertEqual(1, len(report.added))
        self.assertEqual(1, len(report.removed))
        self.assertEqual(2, len(report.changed))
        self.assertEqual(
            ["skills/codebase-memory-mcp/SKILL.md"],
            [item["path"] for item in report.monitored_changes],
        )
        rendered = core.render_upstream_report(report)
        self.assertEqual(
            1,
            rendered.count("skills/codebase-memory-mcp/SKILL.md"),
        )
        self.assertNotIn("content", json.dumps(report.to_dict()).lower())
        self.assertFalse(
            core.update_check_due(report, now=checked + timedelta(hours=23))
        )
        self.assertTrue(
            core.update_check_due(report, now=checked + timedelta(hours=25))
        )

        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary) / "upstream.json"
            core.save_cached_report(report, cache)
            loaded = core.load_cached_report(cache)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(report.checksum, loaded.checksum)
            self.assertEqual(report.to_dict(), loaded.to_dict())
            self.assertIn("checksum", loaded.to_dict())
            self.assertNotIn("signature", loaded.to_dict())

            legacy = report.to_dict()
            legacy["schema"] = 1
            legacy.pop("checksum")
            legacy["signature"] = hashlib.sha256(
                json.dumps(
                    legacy,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            cache.write_text(json.dumps(legacy), encoding="utf-8")
            migrated = core.load_cached_report(cache)
            self.assertIsNotNone(migrated)
            assert migrated is not None
            self.assertEqual(2, migrated.to_dict()["schema"])

            core.save_cached_report(report, cache)
            tampered = json.loads(cache.read_text(encoding="utf-8"))
            tampered["checked_at"] = "2099-01-01T00:00:00+00:00"
            cache.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaisesRegex(core.UpstreamError, "checksum"):
                core.load_cached_report(cache)
            core.save_cached_report(report, cache)
            brief = Path(temporary) / "review.md"
            core.export_review_brief(report, brief)
            text = brief.read_text(encoding="utf-8")
            self.assertIn("## Review boundaries", text)
            self.assertIn("Do not install or enable anything", text)
            self.assertIn("Metadata checksum", text)

    def test_review_service_isolated_diff_and_baseline_lifecycle(self) -> None:
        checked = datetime(2026, 8, 31, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cache = root / "cache" / "upstream.json"
            ledger = root / "state" / "reviews.json"
            service = core.UpstreamUpdateService(
                cache_path=cache,
                ledger_path=ledger,
            )
            self.assertIsNone(service.report)
            self.assertIn(
                service.baseline_revision,
                service.catalog_request_urls()["reviewed_tree"],
            )

            report = service.accept_catalog_payloads(
                upstream_payloads(),
                checked_at=checked,
            )
            self.assertEqual(4, len(service.review_items(outstanding_only=True)))
            self.assertEqual(report, service.report)
            self.assertEqual(2, json.loads(cache.read_text())["schema"])

            for item in service.review_items():
                payloads: dict[str, bytes] = {}
                if item.reviewed_sha is not None:
                    payloads["reviewed_blob"] = blob_payload(
                        item.reviewed_sha,
                        f"old {item.path}\n",
                    )
                if item.current_sha is not None:
                    payloads["current_blob"] = blob_payload(
                        item.current_sha,
                        f"new {item.path}\n",
                    )
                review = service.build_asset_review(item, payloads)
                self.assertIn("UNTRUSTED UPSTREAM CONTENT", core.render_asset_review(review))
                self.assertIn(item.path, review.diff)
                with self.assertRaisesRegex(core.UpstreamError, "rationale"):
                    service.record_review(review, "watch", "")
                decision = service.record_review(
                    review,
                    "watch",
                    "Reviewed and deferred pending a demonstrated local need.",
                    reviewed_at=checked,
                )
                self.assertEqual(item.state_key, decision.state_key)

            self.assertEqual((), service.review_items(outstanding_only=True))
            self.assertTrue(service.can_advance_baseline())
            self.assertEqual("b" * 40, service.advance_baseline())
            self.assertIsNone(service.report)

            reloaded = core.UpstreamUpdateService(
                cache_path=cache,
                ledger_path=ledger,
            )
            self.assertEqual("b" * 40, reloaded.baseline_revision)
            self.assertIsNone(reloaded.report)
            self.assertIn(
                "b" * 40,
                reloaded.catalog_request_urls()["reviewed_tree"],
            )

    def test_asset_review_rejects_mismatched_or_oversized_blob_metadata(self) -> None:
        report = core.build_upstream_report(upstream_payloads())
        item = next(
            candidate
            for candidate in core.upstream_review_items(report)
            if candidate.change == "changed"
        )
        payloads = {
            "reviewed_blob": blob_payload(item.reviewed_sha or "", "old\n"),
            "current_blob": blob_payload(item.current_sha or "", "new\n"),
        }
        bad = json.loads(payloads["current_blob"])
        bad["sha"] = "0" * 40
        payloads["current_blob"] = json.dumps(bad).encode()
        with self.assertRaisesRegex(core.UpstreamError, "requested SHA"):
            core.build_asset_review(item, payloads)

    def test_report_accepts_an_explicit_local_reviewed_baseline(self) -> None:
        baseline = "a" * 40
        report = core.build_upstream_report(
            upstream_payloads(),
            reviewed_revision=baseline,
        )
        self.assertEqual(baseline, report.reviewed_revision)
        removed = report.removed[0]
        self.assertIn(baseline, removed["url"])
        self.assertIn(
            baseline,
            core.upstream_request_urls(baseline)["reviewed_tree"],
        )

    def test_mixed_or_truncated_upstream_snapshots_are_rejected(self) -> None:
        payloads = upstream_payloads()
        current = json.loads(payloads["current_tree"])
        current["sha"] = "e" * 40
        payloads["current_tree"] = json.dumps(current).encode()
        with self.assertRaisesRegex(core.UpstreamError, "different upstream snapshots"):
            core.build_upstream_report(payloads)

        payloads = upstream_payloads()
        reviewed = json.loads(payloads["reviewed_tree"])
        reviewed["truncated"] = True
        payloads["reviewed_tree"] = json.dumps(reviewed).encode()
        with self.assertRaisesRegex(core.UpstreamError, "truncated"):
            core.build_upstream_report(payloads)


class McpAuditTests(unittest.TestCase):
    def test_generated_mcp_configuration_passes_redacted_audit(self) -> None:
        generated = core.build_mcp_config(("postgres", "context7"))
        audit = core.audit_mcp_configuration(
            generated,
            scope="proposed",
            selected_servers=("postgres", "context7"),
        )
        self.assertEqual([], audit["findings"])
        from_package = core.audit_mcp_configuration(
            {
                "servers": {
                    "tool": {
                        "type": "stdio",
                        "command": "uvx",
                        "args": ["--from", "package==1.2.3", "tool"],
                        "sandboxEnabled": True,
                    }
                }
            },
            scope="proposed",
            reviewed_servers=("tool",),
        )
        self.assertEqual([], from_package["findings"])
        windows_shell = core.audit_mcp_configuration(
            {
                "servers": {
                    "tool": {
                        "type": "stdio",
                        "command": r"C:\Windows\System32\cmd.exe",
                        "args": ["/c", "run-server"],
                        "sandboxEnabled": True,
                    }
                }
            },
            scope="proposed",
            reviewed_servers=("tool",),
        )
        self.assertIn(
            "mcp.command.shell-wrapper",
            {item["code"] for item in windows_shell["findings"]},
        )

    def test_bad_mcp_configuration_reports_boundaries_without_secret_values(self) -> None:
        secret = "top-secret-value-123456"
        audit = core.audit_mcp_configuration(
            {
                "servers": {
                    "danger": {
                        "type": "stdio",
                        "command": "bash",
                        "args": ["-c", "run-server"],
                        "env": {"API_TOKEN": secret},
                        "sandboxEnabled": False,
                    },
                    "floating": {
                        "type": "stdio",
                        "command": "uvx",
                        "args": ["unversioned-mcp"],
                    },
                    "remote": {
                        "type": "http",
                        "url": "http://example.com/mcp",
                    },
                }
            },
            scope="workspace",
        )
        codes = {item["code"] for item in audit["findings"]}
        for code in (
            "mcp.server.unreviewed",
            "mcp.command.shell-wrapper",
            "mcp.secret.literal",
            "mcp.sandbox.missing",
            "mcp.dependency.floating",
            "mcp.transport.insecure",
        ):
            self.assertIn(code, codes)
        self.assertNotIn(secret, json.dumps(audit))

    def test_duplicate_user_and_workspace_scope_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "project"
            (target / ".vscode").mkdir(parents=True)
            workspace = {"servers": {"context7": {"type": "http", "url": "https://mcp.context7.com/mcp"}}}
            (target / ".vscode" / "mcp.json").write_text(
                json.dumps(workspace),
                encoding="utf-8",
            )
            user = root / "user-mcp.json"
            user_secret = "user-secret-value-123456"
            user.write_text(
                json.dumps(
                    {
                        "servers": {
                            **workspace["servers"],
                            "private": {
                                "type": "stdio",
                                "command": "uvx",
                                "args": ["private-mcp"],
                                "env": {"TOKEN": user_secret},
                                "sandboxEnabled": True,
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            audit = collect_mcp_security(
                target,
                proposed=None,
                selected_servers=("context7",),
                require_sandbox=True,
                user_paths=(user,),
            )
            codes = {item["code"] for item in audit["findings"]}
            self.assertIn("mcp.scope.duplicate", codes)
            self.assertIn("mcp.secret.literal", codes)
            self.assertNotIn(user_secret, json.dumps(audit))

    def test_project_analysis_exposes_only_redacted_findings(self) -> None:
        secret = "analysis-secret-value-123456"
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "project"
            (target / ".vscode").mkdir(parents=True)
            (target / ".vscode" / "mcp.json").write_text(
                json.dumps(
                    {
                        "servers": {
                            "unknown": {
                                "type": "stdio",
                                "command": "uvx",
                                "args": ["unknown-mcp"],
                                "env": {"TOKEN": secret},
                                "sandboxEnabled": False,
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch(
                "workflow_configurator.analysis.vscode_user_mcp_paths",
                return_value=(),
            ):
                report = core.analyze_project(
                    target,
                    core.WorkflowConfig(
                        workflow="existing",
                        stack_profiles=(),
                        with_context_settings=False,
                    ),
                )
            codes = {
                item["code"]
                for item in report.facts["mcp_security"]["findings"]
            }
            self.assertIn("mcp.secret.literal", codes)
            self.assertNotIn(secret, report.to_json())


class PluginExportTests(unittest.TestCase):
    def test_local_plugin_export_is_preview_gated_hashed_and_no_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "genai-workflow-core"
            plan = core.preview_local_plugin(destination)
            self.assertFalse(destination.exists())
            self.assertEqual("genai-workflow-core", plan.plugin_name)
            self.assertEqual(8, len(plan.files))
            preview = core.render_plugin_preview(plan)
            self.assertIn("does not install", preview)
            self.assertIn("# AppSec Reviewer", preview)
            result = core.export_local_plugin(plan)
            self.assertEqual("exported", result["status"])
            self.assertTrue((destination / "plugin.json").is_file())
            manifest = json.loads(
                (destination / "plugin.json").read_text(encoding="utf-8")
            )
            self.assertEqual("agents/", manifest["agents"])
            self.assertNotIn("hooks", manifest)
            self.assertNotIn("mcpServers", manifest)
            integrity = json.loads(
                (destination / "INTEGRITY.json").read_text(encoding="utf-8")
            )
            for record in integrity["files"]:
                content = (destination / record["path"]).read_bytes()
                self.assertEqual(
                    record["sha256"],
                    hashlib.sha256(content).hexdigest(),
                )
            with self.assertRaisesRegex(
                core.PluginExportError, "refusing overwrite"
            ):
                core.preview_local_plugin(destination)

    def test_plugin_export_never_removes_a_destination_created_after_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "genai-workflow-core"
            plan = core.preview_local_plugin(destination)
            destination.mkdir()
            marker = destination / "user-owned.txt"
            marker.write_text("keep\n", encoding="utf-8")
            with self.assertRaisesRegex(core.PluginExportError, "refusing overwrite"):
                core.export_local_plugin(plan)
            self.assertEqual("keep\n", marker.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
