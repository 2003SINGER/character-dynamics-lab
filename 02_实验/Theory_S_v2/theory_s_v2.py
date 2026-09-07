"""Theory-S v2: learnable parameterization of the existing state mechanism.

This consolidates the earlier per-field dynamics, v1/v1.2 transition plumbing,
and T14/T20 conditional-linear readout. It does not define a new psychological
topology. X and S are compatibility schemas whose semantics remain hypotheses.
"""
from __future__ import annotations

from dataclasses import dataclass
import torch
from torch import Tensor, nn
import torch.nn.functional as F

X_FIELDS = ("effort_load", "goal_relevance", "positive_conduciveness",
            "negative_conduciveness", "social_opportunity", "recovery_cue")
STATE_FIELDS = ("fatigue", "engagement", "tension")
# Must remain identical to Replay/replay_features_v1.py FEATURE_NAMES.
FEATURE_NAMES = ("goal_progress", "stimulation", "recovery", "hunger_relief",
                 "bathroom_relief", "short_term_reward", "environment_control",
                 "context_relevance", "has_target", "target_in_scene",
                 "target_visible_in_O", "target_in_inventory", "repeated_acquire")
FEATURE_VERSION = "replay-raw-features-v1"
# Soft semantic identity anchors.  Zero means uncertain/free, not fixed zero.
SEMANTIC_SIGN_PRIOR = torch.tensor([
    [1, 0, 0, 0, 0, -1],  # fatigue: effort up, recovery down
    [0, 1, 1, 0, 1, 0],   # engagement: goal/positive/social involvement
    [0, 0, 0, 1, 0, -1],  # tension: negative up, recovery down
], dtype=torch.float32)


@dataclass(frozen=True)
class TheorySConfig:
    state_dim: int = 3
    x_dim: int = 6
    feature_dim: int = len(FEATURE_NAMES)
    alpha_init: float = 0.80


class TheoryS(nn.Module):
    """Per-field bounded relaxation plus the existing conditional readout.

    ``theta`` is the base T14/T20 action-feature weight. ``b``, ``beta``,
    ``alpha`` and ``W`` are the Phase-B dynamic-state parameters. The caller
    supplies O/P-derived candidate features; this module never receives source
    candidates or A*.
    """

    def __init__(self, config: TheorySConfig | None = None):
        super().__init__()
        self.config = config or TheorySConfig()
        if self.config.state_dim != 3 or self.config.x_dim != 6:
            raise ValueError("v2 compatibility contract is 3 S fields and 6 X fields")
        d = self.config.feature_dim
        self.theta = nn.Parameter(torch.zeros(d))
        self.b = nn.Parameter(torch.zeros(3))
        self.beta = nn.Parameter(torch.zeros(3, 6))
        a = min(max(float(self.config.alpha_init), 1e-4), 1 - 1e-4)
        self.alpha_raw = nn.Parameter(torch.full((3,), torch.logit(torch.tensor(a))))
        self.w_sa = nn.Parameter(torch.zeros(3, d))
        self.register_buffer("semantic_sign_prior", SEMANTIC_SIGN_PRIOR.clone())

    @property
    def alpha(self) -> Tensor:
        return torch.sigmoid(self.alpha_raw)

    @property
    def eta(self) -> Tensor:
        return 1.0 - self.alpha

    @property
    def neutral_state(self) -> Tensor:
        """Field-specific equilibrium used to center the behavioral modulation."""
        return torch.sigmoid(self.b)

    def transition(self, state: Tensor, x: Tensor) -> Tensor:
        """S_t = alpha*S_(t-1) + (1-alpha)*sigmoid(b + beta*X_t)."""
        if state.shape[-1] != 3 or x.shape[-1] != 6:
            raise ValueError("state must end in 3 and x in 6 dimensions")
        target = torch.sigmoid(self.b + x @ self.beta.transpose(-1, -2))
        return self.alpha * state + self.eta * target

    def logits(self, state: Tensor, candidate_features: Tensor,
               z_base: Tensor | None = None) -> Tensor:
        """Return candidate logits [batch, candidates] using canonical features."""
        if state.shape[-1] != 3 or candidate_features.shape[-1] != len(FEATURE_NAMES):
            raise ValueError("state/features do not match the v1 replay contract")
        base = candidate_features @ self.theta
        centered_state = state - self.neutral_state
        coupling = torch.einsum("bs,sd,bkd->bk", centered_state, self.w_sa, candidate_features)
        return base + coupling if z_base is None else z_base + coupling

    def semantic_anchor_loss(self, margin: float = 0.0) -> Tensor:
        """Soft sign prior; default is violation-only, with no effect-size floor."""
        known = self.semantic_sign_prior != 0
        signed = self.semantic_sign_prior * self.beta
        return F.relu(torch.as_tensor(margin, device=self.beta.device, dtype=self.beta.dtype) - signed[known]).pow(2).mean()

    def conditional_nll(self, state: Tensor, candidate_features: Tensor,
                        gold_index: Tensor, z_base: Tensor | None = None) -> Tensor:
        return F.cross_entropy(self.logits(state, candidate_features, z_base), gold_index)

    def forward(self, state: Tensor, x: Tensor, candidate_features: Tensor,
                gold_index: Tensor | None = None, z_base: Tensor | None = None):
        next_state = self.transition(state, x)
        logits = self.logits(next_state, candidate_features, z_base)
        if gold_index is None:
            return next_state, logits
        return next_state, logits, F.cross_entropy(logits, gold_index)

    def set_phase(self, phase: str) -> None:
        """Phase A learns theta only; Phase B freezes theta and learns dynamics/readout."""
        if phase not in {"A", "B"}:
            raise ValueError("phase must be A or B")
        self.theta.requires_grad_(phase == "A")
        for p in (self.b, self.beta, self.alpha_raw, self.w_sa):
            p.requires_grad_(phase == "B")

    def effective_parameter_report(self) -> dict[str, int]:
        return {"raw_parameter_count": sum(p.numel() for p in self.parameters()),
                "effective_trainable_degree_count": sum(p.numel() for p in self.parameters() if p.requires_grad),
                "active_edges": 3 * 6 + 3 * len(FEATURE_NAMES), "frozen_edges": 0}


def unroll(model: TheoryS, initial_state: Tensor, x_sequence: Tensor,
           candidate_features: Tensor, gold_index: Tensor,
           detach_state: bool = False, semantic_anchor_weight: float = 0.0,
           semantic_anchor_margin: float = 0.0) -> tuple[Tensor, Tensor]:
    """Unroll [time,batch,*] and sum candidate-set NLL over time."""
    state = initial_state
    losses = []
    states = []
    for t in range(x_sequence.shape[0]):
        state = model.transition(state, x_sequence[t])
        if detach_state:
            state = state.detach()
        states.append(state)
        losses.append(model.conditional_nll(state, candidate_features[t], gold_index[t]))
    total = torch.stack(losses).sum()
    if semantic_anchor_weight:
        total = total + float(semantic_anchor_weight) * model.semantic_anchor_loss(semantic_anchor_margin)
    return torch.stack(states), total


def synthetic_gradient_smoke(seed: int = 7, steps: int = 10) -> dict[str, object]:
    """Multi-step candidate-NLL trainability regression; never a research run."""
    torch.manual_seed(seed)
    model = TheoryS()
    model.set_phase("B")
    t, batch, candidates, d = steps, 2, 4, len(FEATURE_NAMES)
    x = torch.rand(t, batch, 6)
    features = torch.rand(t, batch, candidates, d)
    gold = torch.randint(0, candidates, (t, batch))
    initial = torch.full((batch, 3), .2)
    anchor_weight = 0.05
    before_states, before_loss = unroll(model, initial, x, features, gold,
                                       semantic_anchor_weight=anchor_weight,
                                       semantic_anchor_margin=0.05)
    optim = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=0.08)
    for _ in range(8):
        optim.zero_grad(); _, loss = unroll(model, initial, x, features, gold, semantic_anchor_weight=anchor_weight, semantic_anchor_margin=0.05); loss.backward(); optim.step()
    after_states, after_loss = unroll(model, initial, x, features, gold, semantic_anchor_weight=anchor_weight, semantic_anchor_margin=0.05)
    optim.zero_grad(); _, final_loss = unroll(model, initial, x, features, gold, semantic_anchor_weight=anchor_weight, semantic_anchor_margin=0.05); final_loss.backward()
    grad_norms = {name: float(param.grad.norm()) for name, param in
                  (("b", model.b), ("beta", model.beta), ("alpha", model.alpha_raw), ("w_sa", model.w_sa))}
    assert float(after_loss.detach()) < float(before_loss.detach())
    assert bool(torch.all((after_states >= 0) & (after_states <= 1)))
    assert all(value > 0 for value in grad_norms.values())
    assert model.theta.grad is None
    return {"initial_nll": float(before_loss.detach()), "final_nll": float(after_loss.detach()),
            "gradient_path": grad_norms, "bounded_state": True, "candidate_nll": True,
            "multi_step": True, "theta_frozen_in_phase_b": True,
            "semantic_anchor_weight": anchor_weight}


if __name__ == "__main__":
    print(synthetic_gradient_smoke())
