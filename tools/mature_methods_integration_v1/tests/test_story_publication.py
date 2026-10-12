import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.mature_methods_integration_v1.story_publication import (
    _collect, publish, verify_archive,
)


class StoryPublicationTests(unittest.TestCase):
    def _fixture(self, root: Path):
        runs = root / "runs"
        run = runs / "story-case-a-20261012T120000Z-abcdef"
        (run / "source-snapshot/tools/native_platform_v0/p5").mkdir(parents=True)
        (run / "summary.json").write_text(json.dumps({
            "schema": "native-story-process-run-summary-v1", "case_id": "case-a",
            "status": "INCOMPLETE", "steps_recorded": 0,
            "final_story_process": {"status": "WAITING_FOR_RESPONSE"}}), encoding="utf-8")
        (run / "identity.json").write_text(json.dumps({"case_id": "case-a", "strategy": "gtpyhop"}),
                                           encoding="utf-8")
        (run / "source-snapshot/tools/native_platform_v0/p5/service.py").write_text(
            "def service_entry():\n    return True\n", encoding="utf-8")
        (run / "raw-scoped-db-evidence.json").write_text(
            json.dumps({"scene_id": "scene-1", "ledger": [{"event_type": "P5_STORY_NOTE_ARCHIVED"}],
                        "objects": [{"typeclass": "DefaultObject", "key": "Love note"}]}),
            encoding="utf-8")
        (run / "db-readback-summary.json").write_text(json.dumps({
            "scene_id": "scene-1", "event_count": 1,
            "export_artifact_path": "/private/local/database-export.json",
            "export_artifact_sha256": "a" * 64}), encoding="utf-8")
        (run / "_private").mkdir()
        (run / "_private/raw.txt").write_text("must not be packaged", encoding="utf-8")
        (run / "auth").mkdir()
        (run / "auth/credentials.json").write_text("{}", encoding="utf-8")
        (run / "trace.db").write_bytes(b"database bytes")
        (run / "._metadata").write_bytes(b"AppleDouble")
        (run / "__pycache__").mkdir()
        (run / "__pycache__/x.pyc").write_bytes(b"bytecode")
        return runs, run

    def test_publication_is_explicit_filtered_and_hash_verified(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs, run = self._fixture(root)
            output = root / "public_evidence"
            result = publish([run], runs_root=runs, publication_root=output,
                             project_root=root, timestamp="20261012T140000Z")
            publication = Path(result["publication"])
            index = json.loads((publication / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "VERIFIED")
            member_paths = [row["path"] for row in index["members"]]
            self.assertIn("source-snapshot/tools/native_platform_v0/p5/service.py",
                          next(path for path in member_paths if path.endswith("service.py")))
            self.assertTrue(any(path.endswith("raw-scoped-db-evidence.json") for path in member_paths))
            self.assertEqual(index["member_count"], 4)
            self.assertEqual(len(index["excluded"]), 6)
            self.assertEqual(index["database_readbacks"][0]["event_count"], 1)
            self.assertTrue(index["database_readbacks"][0]["path_omitted"])
            self.assertNotIn("/private/local", json.dumps(index["database_readbacks"]))
            self.assertEqual(verify_archive(Path(result["archive"]), index, root)["status"], "VERIFIED")
            with tarfile.open(result["archive"], "r:gz") as archive:
                names = {member.name for member in archive.getmembers()}
            self.assertEqual(names, {row["path"] for row in index["members"]})
            self.assertFalse(any("_private" in name or "/auth/" in name or name.endswith(".db")
                                 for name in names))

    def test_only_direct_story_children_are_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs, run = self._fixture(root)
            outside = root / "other"
            outside.mkdir()
            with self.assertRaises(ValueError):
                publish([outside], runs_root=runs, publication_root=root / "pub", project_root=root,
                        timestamp="20261012T140000Z")
            with self.assertRaises(ValueError):
                publish([], runs_root=runs, publication_root=root / "pub", project_root=root,
                        timestamp="20261012T140000Z")

    def test_credential_like_content_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs = root / "runs"
            run = runs / "story-secret-20261012T120000Z-abcdef"
            run.mkdir(parents=True)
            (run / "evidence.txt").write_text("Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456",
                                               encoding="utf-8")
            with self.assertRaises(ValueError):
                _collect([run], root)

    def test_existing_publication_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runs, run = self._fixture(root)
            output = root / "public_evidence"
            target = output / "story-process-v1-20261012T140000Z"
            target.mkdir(parents=True)
            marker = target / "keep.txt"
            marker.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                publish([run], runs_root=runs, publication_root=output,
                        project_root=root, timestamp="20261012T140000Z")
            self.assertEqual(marker.read_text(encoding="utf-8"), "existing")

    def test_tar_verifier_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive_path = root / "unsafe.tar.gz"
            with tarfile.open(archive_path, "w:gz") as archive:
                import io
                payload = b"x"
                info = tarfile.TarInfo("../escape")
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
            with self.assertRaises(ValueError):
                verify_archive(archive_path, {"members": []}, root)


if __name__ == "__main__":
    unittest.main()
