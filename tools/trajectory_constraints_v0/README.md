# Typed Trajectory Constraints V0 — reference package

Status: `READY_FOR_INDEPENDENT_REVIEW` (self-authored executable reference; not closed).

This stdlib-only package specifies four contracts: a pinned observable registry, a closed temporal AST, a finite-trace monitor, and deterministic editor compilation. It is independent of Runtime/C++, the Director, planning, LLMs, and any game execution. The project’s current C++ dynamics are not assumed to have polynomial certificates. `acceptance_manifest.json` maps admission rows to tests and records deliberate nonclaims.

Run the deterministic contract suite from the repository root:

```sh
PYTHONPATH=tools python3 -m unittest discover -s tools/trajectory_constraints_v0/tests -v
```

## Core API

- `types.py`: `Registry`, `RegistryEntry`, `TypeSpec`, `ValueRef`, `StableEntity`, `Owner`, `ValueKind`, `TimeMode`, `exact_time`.
- `ast.py`: pointwise `CompareValue`/`Not`/`And`/`Or`; `TemporalConstraint`; event counts and order; `NumericBand`; `TimeWeightedMeanDifference`; `EnumTransitionSequence`; tagged `ast_to_json`/`ast_from_json`.
- `trace.py`: trusted committed `Point`, `Segment`, `Event`, and append-only `Trace`.
- `compiler.py`: `compile_constraint`, `detect_hard_conflict`, `verify_migration`.
- `monitor.py`: `evaluate`, `MonitorSession`, five verdicts and evidence-rich `MonitorResult`.
- `editor.py`: point, milestone, event, enum-sequence, DAG, and explicit envelope compilation.
- `projectors.py` and `evaluation.py`: callable pure projectors and explicit dispatch over synthetic snapshots for task progress, W holding, actor belief, and factive observer knowledge. This is not a production Runtime/C++ evaluator binding. `registered_field_v1` is a typed fixture lookup, not proof that production fields have been connected.

Time is exact simulation minutes (`int`, decimal `str`, or `Fraction`); floats, booleans, NaN, and infinity are rejected. Entity identity is `(entity_type, stable_id)`, never display name. Model-scoped ACTOR_S observables require an immutable model pin. Registry versions cannot be overwritten. Evaluators must use the explicit allowlist in `types.py`; a name is not executable Python.

## Minimal JSON shape

```json
{
  "registry": {
    "entries": [{
      "observable_id": "world.city.food_stock_kg",
      "version": "1",
      "owner": "WORLD",
      "subject_type": "City",
      "args": {"city": "City"},
      "value": {"kind": "REAL", "unit": "kg", "lower": "0", "upper": "100000", "enum_values": [], "element_type": null},
      "evaluator_id": "registered_field_v1",
      "reads": ["City.food_stock_kg"],
      "time_mode": "CERTIFIED_POLYNOMIAL",
      "missing_policy": "INDETERMINATE",
      "model_pin": null
    }]
  },
  "constraint": {
    "$type": "NumericBand",
    "constraint_id": "food-band",
    "ref": {"$type": "ValueRef", "observable_id": "world.city.food_stock_kg", "version": "1", "args": {"city": {"$entity": ["City", "city-1", "Town", false]}}, "expected_owner": "WORLD"},
    "window": {"$type": "Window", "start": {"$fraction": [0, 1]}, "end": {"$fraction": [120, 1]}, "left_closed": true, "right_closed": true},
    "lower": {"$fraction": [800, 1]}, "upper": {"$fraction": [1200, 1]}, "unit": "kg",
    "lower_at_end": null, "upper_at_end": null,
    "anchor": {"$type": "Anchor", "kind": {"$enum": ["AnchorKind", "SCENARIO_START"]}, "absolute_time": null, "event_type": null, "event_filter": null},
    "trigger": null, "hard": true
  }
}
```

The Python AST encoder/decoder is the authoritative round-trip representation; the example illustrates its tags, exact fractions, explicit units, owner, and interval closure. `AT` points, within-window milestones (`EVENTUALLY`), event occurrence, event ordering, numeric bands, and enum transitions have distinct constructors. Numeric bands must name their unit explicitly, even when it matches the registered observable.

## Monitoring and limits

`EVENTUALLY` can conclude on a witness. `ALWAYS` only concludes SATISFIED at window completion with coverage; a counterexample or known witness masks irrelevant unknowns under pointwise Boolean semantics. A missing historical value is `INDETERMINATE`, while an unresolved future is `PENDING`. A trigger that never occurs returns `NOT_ACTIVATED`; `EACH` yields one result per event ID. Exact duplicate ledger event IDs are counted once; conflicting duplicates or reordered events are rejected.

Signals are not interpolated by default. Piecewise-constant values hold from a committed point to the next update. `POINT_ONLY` supports only AT/zero-width bands. Certified local polynomials have degree at most two and exact extrema/integrals. Generic interval bounds can certify a whole-band pass or a definite violation, but a bound merely crossing the threshold is `INDETERMINATE`; it is not a witness. Weighted means integrate by duration over fully covered certified segments and require positive-duration, non-overlapping windows. No pass is inferred from sparse endpoints.

Evidence must match the registry time mode: BOOL/ENUM state cannot use numeric segments; POINT_ONLY cannot use segments; INTERVAL_BOUNDS accepts only bound certificates; PIECEWISE_CONSTANT REAL accepts only degree-zero or singleton-bound segments. Weighted means are restricted to certified-polynomial traces. Non-point bands on piecewise REAL traces are rejected in V0 rather than guessed from samples. LINEAR/HOLD envelopes require at least two control points; HOLD uses half-open intervals and treats the final control point as the end marker, while POINT_ONLY emits actual point constraints.

The monitor treats accepted points/segments as a synthetic trusted-evidence abstraction. It validates declared shapes, domains, types, and coverage, but does not independently prove that a producer's polynomial/bounds certificate corresponds to World or model dynamics. A production adapter would need a separately validated oracle/commit path. Piecewise-constant values require an explicit per-reference `seal_values_through(ref, time)` declaration before a held value or a no-more-changes temporal conclusion can be used; exact timestamp samples remain point facts without such a seal.

The monitor does not implement full PDDL3 or STL compliance. It is a narrow finite-trace project contract. Window closure is explicit; integration endpoints have measure zero. `COMPATIBILITY_UNKNOWN` is returned unless a narrow hard-conflict proof is available. Monitor checkpoints contain monitor activation bookkeeping only and are not world/runtime snapshots.

The task-progress projector requires `target > 0` and `0 <= done <= target`; it never repairs invalid data by clamping. Factive observer knowledge additionally requires a true W fact and admitted evidence provenance; actor belief alone is not knowledge. No trust/relationship observable is registered. Natural-language annotations are non-semantic. The destroy-event acceptance case demonstrates that reachability evidence is separate: an unresolved future temporal goal remains `PENDING`; no planner or feasibility solver is implemented.
