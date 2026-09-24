#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Offline replay checks for catalog migration; never contacts a real hub."""

from copy import deepcopy
import unittest
import urllib.error

import migrate_hexapod_catalog as migration


class FakeHub:
    url = "https://offline.invalid"

    def __init__(self):
        self.calls = []
        self.items = []
        self.messages = {}
        self.scenes = {}
        self.builds = []
        for build_id, version in ((migration.FIRST, "current"), (migration.MAIN, "v1"), (migration.METAL, "v5")):
            versions = [{"name": version}]
            if build_id == migration.FIRST:
                versions.append({"name": migration.AS_BUILT_FIRST})
            self.builds.append({"id": build_id, "defaultBranch": "main", "branches": [
                {"name": "main", "defaultVersion": version, "versions": versions}]})
            scene = {"name": build_id, "source": "producer.py", "meshes": [], "instances": [
                {"id": "chassis", "partType": "chassis_bottom"},
                {"id": "coxa", "partType": "coxa_link"},
                {"id": "tibia", "partType": "tibia_tube"}]}
            self.scenes[migration.scene_path(migration.source(build_id, "main", version))] = scene
            if build_id == migration.FIRST:
                self.scenes[migration.scene_path(migration.source(build_id, "main", migration.AS_BUILT_FIRST))] = deepcopy(scene)
        self.root_only_id = migration.MAIN + "/root-only-study"
        self.builds.append({"id": self.root_only_id, "defaultBranch": "main", "branches": [
            {"name": "main", "defaultVersion": "v9", "versions": [{"name": "v8"}, {"name": "v9"}]}]})
        self.before = {"source": "old.py", "instances": [], "meshes": []}
        self.after = {"source": "new.py", "instances": [], "meshes": []}
        self.scenes[migration.scene_path(migration.source(self.root_only_id, "main", "v8"))] = self.before
        self.scenes[migration.scene_path(migration.source(self.root_only_id))] = self.after

    def request(self, path, body=None, method="GET"):
        self.calls.append((method, path, deepcopy(body)))
        if method == "GET":
            if path == "/__buildviz/catalog":
                return {"schema": 1, "items": deepcopy(self.items)}
            if path == "/builds/index.json":
                return {"builds": deepcopy(self.builds)}
            if path in self.scenes:
                return deepcopy(self.scenes[path])
            raise urllib.error.HTTPError(path, 404, "absent", {}, None)
        if method == "POST" and path == "/__buildviz/catalog":
            self.items.extend(deepcopy(body["items"]))
            return {"ok": True}
        if method == "PATCH" and path == "/__buildviz/revisions/metadata":
            key = (body["buildId"], body["branch"], body["version"])
            updated = not (body["ifMessageMissing"] and self.messages.get(key))
            if updated:
                self.messages[key] = body["message"]
            return {"ok": True, "updated": updated, "message": self.messages[key]}
        raise AssertionError(f"Unexpected request {method} {path}")


def fixture():
    hub = FakeHub()
    items, evidence = migration.assembly_entries(hub, hub.builds)
    ref = migration.source(hub.root_only_id, "main", "v9")
    note, note_evidence = migration.revision_note(hub.after, hub.before, "v8", "Example")
    plan = {"planVersion": migration.PLAN_VERSION, "url": hub.url,
        "catalogItems": items, "catalogBefore": {"schema": 1, "items": []},
        "assemblySelectionEvidence": evidence,
        "revisionUpdates": [{**ref, "message": note, "ifMessageMissing": True, "evidence": note_evidence}]}
    hub.calls.clear()
    return hub, plan


class MigrationReplayTests(unittest.TestCase):
    def test_all_primary_history_is_covered_without_replacing_notes(self):
        branch = {"defaultVersion": "new"}
        old = {"name": "old", "pushedAt": "2026-06-01T00:00:00Z"}
        for build_id in (migration.FIRST, migration.MAIN, migration.METAL):
            self.assertTrue(migration.needs_description(build_id, branch, old, "2026-09-01"))
            self.assertFalse(migration.needs_description(build_id, branch,
                {**old, "message": "Original note"}, "2026-09-01"))
        self.assertFalse(migration.needs_description("another-study", branch, old, "2026-09-01"))
        self.assertTrue(migration.needs_description("another-study", {"defaultVersion": "old"}, old, "2026-09-01"))

    def test_summary_uses_singular_for_one_remaining_type(self):
        self.assertIn("1 other component type", migration.friendly(["a", "b", "c", "d", "e"]))
        self.assertNotIn("1 other component types", migration.friendly(["a", "b", "c", "d", "e"]))

    def test_primary_baseline_describes_the_full_robot(self):
        note, _ = migration.revision_note({"instances": [], "meshes": []}, None, None,
            "Knee, tibia and foot", migration.MAIN)
        self.assertIn("Full STS robot assembly", note)
        self.assertNotIn("Knee, tibia and foot", note)

    def test_source_summary_cannot_replace_reference(self):
        _, plan = fixture()
        for record in plan["assemblySelectionEvidence"].values():
            self.assertEqual(record["source"], "producer.py")
            self.assertIsInstance(record["reference"], dict)
            self.assertTrue(record["reference"]["version"])

    def test_apply_replays_pins_root_fallback_and_conditional_patch(self):
        hub, plan = fixture()
        result = migration.apply(hub, plan)
        writes = [(method, path, body) for method, path, body in hub.calls if method != "GET"]
        self.assertEqual([method for method, _, _ in writes], ["POST", "PATCH"])
        self.assertEqual(writes[1][2]["version"], "v9")
        self.assertTrue(writes[1][2]["ifMessageMissing"])
        self.assertTrue(result["revisions"][0]["result"]["updated"])
        first_write = next(n for n, call in enumerate(hub.calls) if call[0] != "GET")
        self.assertTrue(all(call[0] != "GET" for call in hub.calls[first_write:]))
        self.assertEqual(len(hub.items), 9)
        self.assertIn(("GET", migration.scene_path(migration.source(hub.root_only_id)), None), hub.calls)

    def test_replay_is_idempotent_and_preserves_existing_note(self):
        hub, plan = fixture()
        migration.apply(hub, plan)
        key = (hub.root_only_id, "main", "v9")
        hub.messages[key] = "Owner's original note"
        hub.calls.clear()
        result = migration.apply(hub, plan)
        self.assertFalse(any(method == "POST" for method, _, _ in hub.calls))
        self.assertEqual(hub.messages[key], "Owner's original note")
        self.assertFalse(result["revisions"][0]["result"]["updated"])

    def test_old_report_rejected_before_requests(self):
        hub, plan = fixture()
        plan.pop("planVersion")
        with self.assertRaisesRegex(ValueError, "Outdated migration plan"):
            migration.apply(hub, plan)
        self.assertEqual(hub.calls, [])

    def test_bad_reference_rejected_before_requests(self):
        hub, plan = fixture()
        plan["assemblySelectionEvidence"]["hexapod-1"]["reference"] = "producer.py"
        with self.assertRaisesRegex(ValueError, "Invalid pinned assembly reference"):
            migration.apply(hub, plan)
        self.assertEqual(hub.calls, [])

    def test_changed_pin_prevents_all_writes(self):
        hub, plan = fixture()
        ref = plan["assemblySelectionEvidence"]["hexapod-1"]["reference"]
        hub.scenes[migration.scene_path(ref)]["source"] = "changed.py"
        with self.assertRaisesRegex(ValueError, "Pinned assembly scene changed"):
            migration.apply(hub, plan)
        self.assertTrue(all(method == "GET" for method, _, _ in hub.calls))

    def test_changed_revision_skips_only_that_note(self):
        hub, plan = fixture()
        hub.scenes[migration.scene_path(migration.source(hub.root_only_id))]["source"] = "changed.py"
        result = migration.apply(hub, plan)
        self.assertIn("skipped", result["revisions"][0]["result"])
        self.assertFalse(any(method == "PATCH" for method, _, _ in hub.calls))
        self.assertEqual(len(hub.items), 9)

    def test_old_default_never_reads_new_default_mirror(self):
        hub, plan = fixture()
        hub.builds[-1]["branches"][0]["defaultVersion"] = "v10"
        result = migration.apply(hub, plan)
        self.assertIn("unavailable", result["revisions"][0]["result"]["skipped"])
        self.assertNotIn(("GET", migration.scene_path(migration.source(hub.root_only_id)), None), hub.calls)
        self.assertFalse(any(method == "PATCH" for method, _, _ in hub.calls))


if __name__ == "__main__":
    unittest.main()
