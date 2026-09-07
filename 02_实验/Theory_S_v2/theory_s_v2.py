"""Dataset-neutral, literature-constrained Theory-S v2 module.

This is a trainable research operator, not a fitted psychological model.  It
keeps candidate generation outside the module: action features are supplied
by the caller and no source candidate list or A* field is read here.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import torch
from torch import Tensor, nn
import torch.nn.functional as F

X_FIELDS = ("effort_load", "goal_relevance", "positive_conduciveness",
            "negative_conduciveness", "social_opportunity", "recovery_cue")
STATE_FIELDS = ("fatigue", "engagement", "tension")
ACTION_FEATURES = ("stimulation", "social", "conflict", "recovery")

# Rows are S and columns are X.  1/-1 are permitted signed edges; zero is a
# structural absence.  The signs are an explicit hypothesis, not a result.
TOPOLOGY_XS = torch.tensor([
    [1, 0, 0, 1, 0, -1],  # fatigue
    [0, 1, 1, 0, 1, 0],   # engagement
    [0, 1, 0, 1, 0, -1],  # tension
], dtype=torch.float32)
# Rows are S and columns are action-feature basis dimensions.
TOPOLOGY_SA = torch.tensor([
    [-1, 0, 0, 1],  # fatigue suppresses stimulation, supports recovery
    [1, 1, 0, 0],   # engagement supports stimulation/social
    [0, 0, 1, 0],   # tension supports conflict
], dtype=torch.float32)


def _signed_weight(raw: Tensor, topology: Tensor) -> Tensor:
    """Positive magnitude + fixed sign, with structural zeros."""
    return topology.to(raw.device) * F.softplus(raw) * (topology != 0).to(raw.dtype)


@dataclass(frozen=True)
class TheorySConfig:
    state_permutation: tuple[int, ...] = (0, 1, 2)
    alpha_init: float = 0.80


class TheoryS(nn.Module):
    """Bounded state transition and action-score coupling.

    ``x`` is [batch, 6], ``state`` [batch, 3], ``action_features`` [batch, 4],
    and ``z_base`` [batch].  The action feature vector is an explicit caller
    input, so the module cannot accidentally inspect candidate IDs or A*.
    """

    def __init__(self, config: TheorySConfig | None = None):
        super().__init__()
        self.config = config or TheorySConfig()
        perm = self.config.state_permutation
        if sorted(perm) != list(range(3)):
            raise ValueError("state_permutation must be a permutation of 0..2")
        self.register_buffer("topology_xs", TOPOLOGY_XS[list(perm)].clone())
        self.register_buffer("topology_sa", TOPOLOGY_SA[list(perm)].clone())
        self.w_xs_raw = nn.Parameter(torch.zeros(3, 6))
        self.w_sa_raw = nn.Parameter(torch.zeros(3, 4))
        a = min(max(float(self.config.alpha_init), 1e-4), 1 - 1e-4)
        self.alpha_raw = nn.Parameter(torch.full((3,), torch.logit(torch.tensor(a))))

    @property
    def w_xs(self) -> Tensor:
        return _signed_weight(self.w_xs_raw, self.topology_xs)

    @property
    def w_sa(self) -> Tensor:
        return _signed_weight(self.w_sa_raw, self.topology_sa)

    @property
    def alpha(self) -> Tensor:
        return torch.sigmoid(self.alpha_raw)

    def transition(self, state: Tensor, x: Tensor) -> Tensor:
        if state.shape[-1] != 3 or x.shape[-1] != 6:
            raise ValueError("state must end in 3 and x in 6 dimensions")
        pre = self.alpha * state + x @ self.w_xs.transpose(-1, -2)
        return torch.sigmoid(pre)

    def score(self, state: Tensor, action_features: Tensor, z_base: Tensor | float = 0.0) -> Tensor:
        if state.shape[-1] != 3 or action_features.shape[-1] != 4:
            raise ValueError("state must end in 3 and action_features in 4 dimensions")
        coupling = (state @ self.w_sa) * action_features
        return torch.as_tensor(z_base, dtype=state.dtype, device=state.device) + coupling.sum(-1)

    def forward(self, state: Tensor, x: Tensor, action_features: Tensor,
                z_base: Tensor | float = 0.0) -> tuple[Tensor, Tensor]:
        next_state = self.transition(state, x)
        return next_state, self.score(next_state, action_features, z_base)

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())


def permuted_s(config: TheorySConfig | None = None) -> TheoryS:
    """Equal-capacity Permuted-S control with identical X/action basis."""
    base = config or TheorySConfig()
    return TheoryS(TheorySConfig(state_permutation=(1, 2, 0), alpha_init=base.alpha_init))


def topology_report(model: TheoryS) -> dict[str, object]:
    return {
        "state_fields": list(STATE_FIELDS), "x_fields": list(X_FIELDS),
        "action_features": list(ACTION_FEATURES),
        "xs_nonzero": int((model.topology_xs != 0).sum().item()),
        "sa_nonzero": int((model.topology_sa != 0).sum().item()),
        "parameter_count": model.parameter_count(),
    }


def synthetic_gradient_smoke(seed: int = 7) -> dict[str, object]:
    """Run a tiny differentiable check; no dataset or formal training involved."""
    torch.manual_seed(seed)
    model = TheoryS()
    control = permuted_s()
    x = torch.rand(8, 6)
    state = torch.rand(8, 3)
    action_features = torch.rand(8, 4)
    z_base = torch.zeros(8)
    next_state, logits = model(state, x, action_features, z_base)
    loss = F.binary_cross_entropy_with_logits(logits, torch.rand(8))
    loss.backward()
    assert model.w_xs_raw.grad is not None and model.w_sa_raw.grad is not None
    assert model.alpha_raw.grad is not None
    assert torch.all((next_state >= 0) & (next_state <= 1))
    assert model.parameter_count() == control.parameter_count()
    assert int((model.topology_xs != 0).sum()) == int((control.topology_xs != 0).sum())
    assert int((model.topology_sa != 0).sum()) == int((control.topology_sa != 0).sum())
    assert not torch.equal(model.topology_xs, control.topology_xs)
    return {"loss": float(loss.detach()), "parameter_count": model.parameter_count(),
            "gradient_path": {"w_xs": float(model.w_xs_raw.grad.norm()),
                              "w_sa": float(model.w_sa_raw.grad.norm()),
                              "alpha": float(model.alpha_raw.grad.norm())},
            "bounded_state": True, "no_candidate_leakage": True}


if __name__ == "__main__":
    print(synthetic_gradient_smoke())
