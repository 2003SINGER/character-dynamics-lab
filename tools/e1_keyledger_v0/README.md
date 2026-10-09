# E1 Key Ledger v0: local development implementation

This package implements the authorized E1-1 finite development artifact. It is
not a formal experiment, a training run, an E0 modification, or evidence for a
behavioral claim. The governing boundary is
[E1 protocol](../../00_研究设计/E1_KeyLedger_LocalAgency_Protocol_v0.md).

## Components

- fixtures.py copies E0-P01 into the twelve K × B-policy × deadline conditions
  and adds E1-only observation, goal, policy-contract, and scheduler fields.
- executor.py reuses E0 physical start/settlement semantics and adds the
  single request_tool operator with a separately versioned event and receipt.
- policy.py constructs actor-only inputs and implements the deterministic B
  chooser. A and B receive their own O, goals, public catalog, and published
  contract. They never receive W or the other actor's O.
- planner.py is A-local h=0 uniform-cost search. Hypothetical future loan-key
  bindings remain typed LoanKey symbols in the forecast plan; only a later
  real observation may ground an executable action to key1.
- oracle.py contains the independent handwritten O_world and O_fixedB
  state searches. Their returned paths remain evaluator outputs and are not
  used as A policy inputs.
- monitor_bridge.py validates every E0 event through the original TypedIR
  bridge and separately validates E1 request event, receipt, provenance, and
  contiguous seal coverage before adapting the E0 goal monitor.
- runner.py runs all twelve development conditions, writes a non-overwriting
  run directory, and records input snapshots/hashes, decisions, assumptions,
  oracle outputs, budget stops, actual trace, evidence and source hashes.

## Run

From the project root:

```sh
PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1 python3 -B -m tools.e1_keyledger_v0.runner \
  --case all --run-id dev-YYYYMMDD-HHMMSS \
  --output-root runs/e1_keyledger_v0/dev \
  --max-expansions 10000 --wall-seconds 2.0
```

Use an unused run ID. Existing output is never overwritten. An incomplete
solver is recorded as INCOMPLETE_BUDGET; a correctness mismatch is FAIL.
Neither is converted into a pass by retrying with a larger budget.

Development unit checks:

```sh
PYTHONPATH=tools PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s tools/e1_keyledger_v0/tests -v
```

The run manifest is marked DEV_ONLY and includes formal_experiment=false.
The twelve expected verdicts are hand-derived protocol checks, not measured
results. Strong AND/OR, learning, and formal E1-2 are outside this package.
