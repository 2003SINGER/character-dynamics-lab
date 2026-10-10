import unittest

from tools.native_platform_v0.p3.audit_evidence import successful_delivery


class EvidenceAuditTests(unittest.TestCase):
    def test_rejects_unsettled_receipt_even_if_final_goal_looks_settled(self):
        actor = {
            "status": "ACTOR_DELIVERY_SETTLED",
            "native_receipts": [
                {"kind": kind, "receipt_id": f"r-{kind}", "settled": True, "dispatch_succeeded": True}
                for kind in ("get", "move", "drop")
            ],
        }
        actor["native_receipts"][0]["settled"] = False
        with self.assertRaisesRegex(ValueError, "non-settled"):
            successful_delivery(actor, "mutated-fixture")


if __name__ == "__main__":
    unittest.main()
