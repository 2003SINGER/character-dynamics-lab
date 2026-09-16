"""Minimal explicit ResearchDynamicsV1 candidate (development-only)."""
from dataclasses import dataclass, asdict
import json

MODEL_ID = "ResearchDynamicsV1"

@dataclass(frozen=True)
class Personality:
    recovery_sensitivity: float = 1.0
    deadline_sensitivity: float = 1.0
    stimulation_preference: float = 1.0

@dataclass
class State:
    fatigue: float = 0.0
    task_pressure: float = 0.0
    boredom: float = 0.0
    satisfaction: float = 0.0

    def _clip(self):
        for k, v in asdict(self).items():
            setattr(self, k, min(1.0, max(0.0, v)))

    def step(self, *, minutes: float, action: str = "idle", task_progress: float = 0.0,
             deadline_signal: float = 0.0, reward: float = 0.0,
             personality: Personality = Personality()) -> dict:
        dt = max(0.0, minutes) / 60.0
        before = asdict(self)
        effort = {"study": .10, "screen": .07, "work": .09}.get(action, .01)
        recovery = {"rest": .16, "sleep": .24}.get(action, .0) * personality.recovery_sensitivity
        stimulation = {"screen": .08, "social": .12, "study": .03}.get(action, .01)
        self.fatigue += dt * (effort - recovery)
        self.task_pressure += dt * (.10 * deadline_signal * personality.deadline_sensitivity - .16 * task_progress)
        self.boredom += dt * (.10 - stimulation * personality.stimulation_preference)
        self.satisfaction += dt * (.12 * reward + .05 * task_progress - .03 * effort)
        self._clip()
        return {"before": before, "after": asdict(self), "minutes": minutes, "action": action}

    def policy(self, candidates, personality=Personality()):
        """Observable candidate scoring; no hidden world or evaluation label."""
        scores = {}
        for action in candidates:
            score = 0.0
            if action == "study": score += 1.4 * self.task_pressure
            if action in {"rest", "sleep"}: score += 1.2 * self.fatigue
            if action in {"social", "screen"}: score += 0.9 * self.boredom
            if action == "idle": score += 0.2 * self.satisfaction
            scores[action] = score
        peak = max(scores.values(), default=0.0)
        return {k: (v / peak if peak else 0.0) for k, v in scores.items()}

    def zones(self):
        return {k: ("high" if v >= .70 else "low" if v <= .30 else "mid")
                for k, v in asdict(self).items()}

def run_intervention(name: str) -> dict:
    s = State()
    rows = [s.step(minutes=60, action="study", deadline_signal=1.0)]
    if name == "correct_recovery":
        rows.append(s.step(minutes=60, action="sleep"))
    elif name == "permuted":
        rows.append(s.step(minutes=60, action="sleep", task_progress=1.0))
    elif name == "stale_o":
        rows.append(s.step(minutes=60, action="study", deadline_signal=0.0))
    else:
        rows.append(s.step(minutes=60, action="idle"))
    return {"dynamics_model_id": MODEL_ID, "intervention": name,
            "state_trace": rows, "final_state": asdict(s)}

if __name__ == "__main__":
    print(json.dumps({n: run_intervention(n) for n in
                      ("zero", "correct_recovery", "permuted", "stale_o")}, indent=2))
