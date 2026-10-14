#!/usr/bin/env python3
"""Bounded interface smoke policy: item persistence plus one feedback branch."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from tools.open_adventure_v0.session import OpenAdventureSession, replay


def choose_recovery(observation: str) -> str:
    """Choose from current visible text; this is not used to detect PTY boundaries."""
    if "already carrying it!" in observation.casefold():
        return "drop lamp"
    return "inventory"


def run_smoke(*, runs_root: Path | None = None) -> dict[str, object]:
    options = {"runs_root": runs_root} if runs_root else {}
    session = OpenAdventureSession(**options)
    commands: list[dict[str, str]] = []
    results = []
    policy_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

    def act(command: str, source: str, *, expect_prompt: bool = True):
        result = session.step(command, controller="interface-smoke-policy",
                              decision_source=source)
        results.append(result)
        commands.append({"command": command,
                         "controller": "interface-smoke-policy",
                         "decision_source": source})
        if expect_prompt and not result.input_boundary_reached:
            raise RuntimeError(f"native input boundary not reached: {result.error}")
        if not expect_prompt and not result.terminated:
            raise RuntimeError(f"expected process termination: {result.error}")
        return result.observation

    initial = session.reset({"experiment_config_version": "open-adventure-online-p1-smoke-v0",
                             "policy": "interface smoke only",
                             "policy_source_sha256": policy_sha256,
                             "policy_scope": "visible-text-only item toggle; no puzzle goal",
                             "seed_control": {"command": "seed 20261014",
                                              "timing": "after startup answer and initial game initialization"}})
    initial_raw = session._raw_observation
    try:
        act("n", "answer the visible startup question")
        act("seed 20261014", "fixed replay seed command")
        act("in", "enter the visible building from the road")
        retry = act("take lamp extra", "trigger native parser rejection and retry boundary")
        if "1- and 2-word commands" not in retry:
            raise RuntimeError("expected native parser length rejection was absent")
        act("take lamp", "try the visible room item")
        carrying = act("inventory", "inspect player-visible inventory feedback")
        if not any(alias in carrying.casefold() for alias in ("lamp", "lantern")):
            raise RuntimeError("inventory did not report the acquired lamp/lantern")
        rejected = act("take lamp", "probe native already-carrying rejection")
        recovery = choose_recovery(rejected)
        if recovery != "drop lamp":
            raise RuntimeError("expected native already-carrying feedback was absent")
        # This branch is decided only after the previous native output is available.
        act(recovery, "visible rejection selected the drop-and-recover branch")
        after_drop = act("inventory", "observe whether drop changed player inventory")
        if any(alias in after_drop.casefold() for alias in ("lamp", "lantern")):
            raise RuntimeError("inventory still reports lamp after native drop")
        act("take lamp", "recover the item after observing it was dropped")
        recovered = act("inventory", "verify the lamp/lantern is carried again")
        if not any(alias in recovered.casefold() for alias in ("lamp", "lantern")):
            raise RuntimeError("inventory did not report the recovered lamp/lantern")
        act("out", "leave the building after the recovery")
        act("look", "observe the room after the item interaction")
        act("quit", "exercise the native yes/no quit question")
        no = act("no", "choose to continue from the native quit question")
        no_result = results[-1]
        if no_result.terminated or not no_result.input_boundary_reached:
            raise RuntimeError("native no response did not return control for another command")
        act("look", "continue after choosing no at the native quit question")
        act("quit", "end the bounded interface smoke")
        end = act("yes", "confirm the native quit prompt", expect_prompt=False)
        if not results[-1].terminated or results[-1].exit_code != 0 or results[-1].error:
            raise RuntimeError("native quit did not finish with exit code zero")
    finally:
        first_status = session.close()

    replay_result = replay(commands, runs_root=runs_root) if runs_root else replay(commands)
    first_outputs = [base64.b64encode(row.raw_output).decode("ascii") for row in results]
    same_outputs = (first_outputs == replay_result["step_outputs_b64"]
                    and base64.b64encode(initial_raw).decode("ascii")
                    == replay_result["initial_observation_raw_b64"])
    meaningful = [item["command"] for item in commands
                  if item["command"] not in {"n", "quit", "no", "yes"}
                  and not item["command"].startswith("seed ")]
    return {
        "classification": "interface smoke policy; not a planning result",
        "first_episode_id": session.episode_id,
        "first_run_dir": str(session.run_dir),
        "initial_observation": initial,
        "meaningful_game_commands": len(meaningful),
        "total_native_inputs": len(commands),
        "feedback_branch_taken": "drop lamp after native already-carrying rejection",
        "counterfactual_branch": choose_recovery("unrelated visible response"),
        "parser_retry_boundary_observed": "1- and 2-word commands" in results[3].observation,
        "quit_no_continued": not no_result.terminated and no_result.input_boundary_reached,
        "first_close": first_status,
        "replay": replay_result,
        "step_outputs_match_replay": same_outputs,
        "first_step_outputs_b64": first_outputs,
        "final_observation": end,
    }


if __name__ == "__main__":
    print(json.dumps(run_smoke(), ensure_ascii=False, indent=2))
