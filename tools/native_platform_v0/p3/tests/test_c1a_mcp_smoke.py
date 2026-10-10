import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.native_platform_v0.p3.c1a_mcp_smoke import write_result


class C1aMcpSmokeTests(unittest.TestCase):
    def test_main_document_shape_is_writable_and_keeps_seed_metadata(self):
        response = {"scenario": "C0-delivery-priority", "seed": 17,
                    "messages": [{"jsonrpc": "2.0", "id": 2}]}
        document = {"recorded_at": datetime.now(timezone.utc).isoformat(),
                    "manifest": {"source_sha256": {}}, "response": response,
                    "scenario": response["scenario"], "seed": response["seed"]}
        with tempfile.TemporaryDirectory() as directory:
            path = write_result(document, Path(directory))
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved, document)
            self.assertIn("seed17", path.name)


if __name__ == "__main__":
    unittest.main()
