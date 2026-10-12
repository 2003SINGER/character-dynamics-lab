import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from tools.mature_methods_integration_v1.verify_evidence import verify


class RelocatableEvidenceVerifierTests(unittest.TestCase):
    def _publication(self, root: Path, *, omit=(), extra=(), summary_override=None):
        publication = root / "external-review-copy"
        publication.mkdir()
        archive_name = "mature-methods-s1-s4-evidence.tar.gz"
        archive = publication / archive_name
        summary = b"bounded evidence summary\n" if summary_override is None else summary_override
        payload = b"raw evidence fixture\n"
        index = {
            "archive_members": [{
                "path": "fixture/run/payload.json",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }],
        }
        index_bytes = json.dumps(index, sort_keys=True).encode("utf-8") + b"\n"
        embedded = {
            "fixture/run/payload.json": payload,
            "02_实验/Mature_Methods_Integration_v1/runs/publication-final-r2-20261012T085500Z/index.json": index_bytes,
            "02_实验/Mature_Methods_Integration_v1/runs/publication-final-r2-20261012T085500Z/summary.md": b"bounded evidence summary\n",
        }
        for name in omit:
            embedded.pop(name, None)
        for name, contents in extra:
            embedded[name] = contents
        with tarfile.open(archive, "w:gz") as tar:
            for name, contents in embedded.items():
                info = tarfile.TarInfo(name)
                info.size = len(contents)
                tar.addfile(info, io.BytesIO(contents))
        (publication / "index.json").write_bytes(index_bytes)
        (publication / "summary.md").write_bytes(summary)
        archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
        (publication / "archive.sha256").write_text(f"{archive_hash}  {archive_name}\n")
        return publication

    def test_relocated_archive_verifies_without_original_run_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            publication = self._publication(Path(temp))
            result = verify(publication)
            self.assertEqual(result["status"], "VERIFIED")
            self.assertFalse(result["check_originals"])

    def test_missing_embedded_summary_is_rejected(self):
        summary_member = "02_实验/Mature_Methods_Integration_v1/runs/publication-final-r2-20261012T085500Z/summary.md"
        with tempfile.TemporaryDirectory() as temp:
            publication = self._publication(Path(temp), omit=(summary_member,))
            result = verify(publication)
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(any("index and summary pair" in error for error in result["errors"]))

    def test_relocated_summary_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            publication = self._publication(Path(temp), summary_override=b"changed summary\n")
            result = verify(publication)
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(any("differs from relocated external file" in error
                                for error in result["errors"]))

    def test_arbitrary_nonindexed_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            publication = self._publication(Path(temp), extra=(("unlisted/private.txt", b"x"),))
            result = verify(publication)
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(any("unexpected non-indexed" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
