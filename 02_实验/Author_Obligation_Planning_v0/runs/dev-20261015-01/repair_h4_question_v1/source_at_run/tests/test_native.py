import unittest
from dataclasses import replace

from tools.open_adventure_v0.session import StepResult
from tools.author_obligation_planning_v0.native import _receipt_events, UnknownNativeEvent, run_episode


def receipt(command, text):
    return StepResult(episode_id="synthetic", sequence=4, command=command,
                      intended_bytes=b"x", sent_bytes=b"x", before_observation="",
                      raw_output=text.encode(), observation=text, input_boundary_reached=True,
                      terminated=False, exit_code=None, timed_out=False, error=None)


class NativeContracts(unittest.TestCase):
    def test_complete_receipt_creation_not_presence(self):
        created = receipt("wave rod", "A crystal bridge now spans the fissure.")
        self.assertEqual([e.name for e in _receipt_events(created, before_room="EASTBANK")], ["create_bridge"])
        looked = receipt("look", "You're on east bank of fissure. A crystal bridge spans the fissure.")
        self.assertEqual(_receipt_events(looked, before_room="EASTBANK"), [])

    def test_arrival_requires_a_real_room_transition(self):
        west = receipt("look", "You are on the west side of the fissure in the Hall of Mists.")
        self.assertEqual(_receipt_events(west, before_room="WESTBANK"), [])
        self.assertEqual([e.name for e in _receipt_events(west, before_room="EASTBANK")], ["arrive_west"])
        east = receipt("over", "You are on the east bank of a fissure slicing clear across the hall.")
        self.assertEqual([e.name for e in _receipt_events(east, before_room="WESTBANK")], ["return_east"])

    def test_incomplete_or_ambiguous_reply_cannot_create_an_event(self):
        row = receipt("wave rod", "A crystal bridge now spans the fissure.")
        self.assertEqual(_receipt_events(replace(row, input_boundary_reached=False), before_room="EASTBANK"), [])
        with self.assertRaises(UnknownNativeEvent):
            _receipt_events(receipt("wave rod", "Unrecognized feedback"), before_room="EASTBANK")
        with self.assertRaises(UnknownNativeEvent):
            _receipt_events(replace(row, sent_bytes=b"y"), before_room="EASTBANK")

    def test_execution_requires_explicit_guard(self):
        with self.assertRaises(RuntimeError):
            run_episode("A1", execute_native=False)


if __name__ == "__main__":
    unittest.main()
