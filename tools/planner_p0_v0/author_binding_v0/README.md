# Author Binding v0

This isolated offline prototype compiles one explicit, versioned P0 author
binding into (a) the existing Sabre A atomic renderer plus event bookkeeping
fluents and (b) the repository `TypedIR` `EventCount` / `EventOrder` AST. It
does not parse natural language. The descriptor contains the author text,
hardness, fixture role bindings, absolute deadline, derived subgoals,
assumptions, and residual obligations. Derived subgoals are recorded as
planner aids; they never become author hard clauses by themselves.

Each compilation retains the full descriptor, pinned fixture ID and digest,
role-to-entity IDs from that fixture's own scene metadata, and hashes of the
Sabre renderer and TypedIR monitor source files. Its per-clause projection map
names both outputs plus authority/time assumptions and any residual. Actor
labels identify roles; actor IDs are copied from the pinned scene record.

The supported author contract is deliberately narrow: exact-once delivery,
B storm observation, and meeting witness in a closed absolute window `[0,T]`,
plus delivery-before-meeting and observation-before-meeting. The two order
constraints are the existing existential `EXISTS_DISTINCT_PAIR` semantics
under `StrictOrder.EVENT_KEY`; this renderer realizes the P0 pair through
serial one-minute actions and event-time guards. Other order directions,
repeat counts, arbitrary relations, soft evaluators, and relationship semantics
stay residual or unscored. Any unsupported hard clause blocks planner
projection; a soft residual is reported separately and does not strengthen the
hard goal.

Sabre's additional numeric event counters and timestamps are candidate-model
bookkeeping initialized only for the clean initial state of one of the six
committed P0 fixtures. DROP, storm LOOK, and successful MEET update these
counters at the action's pre-action minute. Guards encode exact-once and the
two supported event orders. They do not mutate native world state and do not
authenticate native events. The event goal is a planning projection, not proof
that a plan was dispatched or settled. This version does not support live
replanning, arbitrary snapshots, route-repair prefix initialization, B-macro
planning, or automatic dispatch. Before dispatch, the host integration must
call `assert_plan_binding_current` with the plan's binding ID, version, and
content digest; this prototype does not wire that guard into a live runner.

Fixture identity is validated against role aliases and IDs in the committed
run's separate scene record. Actor IDs come from that record; they are not
invented from actor labels. Receipt evaluation accepts only one of six
allowlisted committed `run.json` files, re-hashes its complete bytes at each
consumption, and then runs this compilation's own TypedIR constraints. Ordinary
receipt-shaped dictionaries, `source="native"`, `settled=true`, or a receipt
ID are not authentication. The SHA pins detect fixture drift relative to this
checkout; they do not cryptographically prove who produced the original native
ledger or withstand a coordinated repository/code change. Missing, modified,
or incomplete pinned evidence is `INDETERMINATE`. Candidate planner effects
and symbolic state are never accepted as monitor evidence.

The native ledger stamps successful primitive settlements at pre-action minute
`t`; post-action snapshots advance to `t+1`. The compiler therefore permits a
required settlement at `T`, while preserving the native `now < 24` action cap
and the native cloud-seed `now <= 22` bound. `deadline_minute` is compiled into
both the Sabre action guards and the TypedIR closed window.

Planner outcomes keep separate labels: `SEARCH_BUDGET`,
`NO_PLAN_IN_EXPORTED_DOMAIN`, and `UNBOUND_OR_RESIDUAL`. A found plan is only
`PLAN_FOUND_NOT_EXECUTION_EVIDENCE`; native execution and receipt evaluation
remain separate. Sabre action effects are compiled from the same binding as
monitor constraints, but that common source is not proof of compiler
correctness; focused negative tests and the independent TypedIR monitor remain
necessary.

Run offline contracts (no server, no live native actions):

```sh
python3 -B -m unittest discover -s tools/planner_p0_v0/author_binding_v0/tests -p 'test_*.py' -v
```

The same command is included in `planner-p0-contracts.yml`. Live native runs,
search-budget changes, automatic dispatch, and broader DSL support are outside
this prototype.
