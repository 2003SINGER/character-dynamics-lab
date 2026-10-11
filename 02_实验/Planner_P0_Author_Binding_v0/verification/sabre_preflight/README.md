# Author Binding Sabre preflight

Offline parser/search check for the newly rendered candidate domains. This is
not a native run, dispatch, execution, or receipt; it only proves these three
exported inputs parse and solve under the existing local Sabre build.

Reproduce the three rendered inputs from the repository root. This snippet
only compiles to memory and prints the domains; it does not write files. It
uses the pinned `direct-clean-A` fixture, the default binding at deadline 24,
the same binding at deadline 8, and a delivery-only binding with one hard
`p0_delivery` event clause:

```python
from dataclasses import replace
from pathlib import Path

from tools.planner_p0_v0.author_binding_v0.compiler import (
    AuthorClause, compile_binding, p0_author_binding,
)

root = Path.cwd()
cases = [
    ("default", p0_author_binding(24)),
    ("deadline-8", p0_author_binding(8)),
    ("delivery-only", replace(
        p0_author_binding(24),
        clauses=(AuthorClause("deliver", "event_once",
                              event="p0_delivery", actor="A"),),
        derived_subgoals=(), assumptions=(), residual_obligations=(),
    )),
]
for name, binding in cases:
    result = compile_binding(binding, repo_root=root,
                             fixture_id="direct-clean-A")
    assert result.sabre_problem is not None
    print(f"--- {name} ---")
    print(result.sabre_problem)
```

The matching rendered inputs are checked in beside this note. To run them:

```sh
JAVA='_local_data/planner_p0_v0/jdk/jdk-17.0.20.1+1/Contents/Home/bin/java'
CP='_local_data/planner_p0_v0/sabre/bin'
for case in default deadline-8 delivery-only; do
  "$JAVA" -Xms64m -Xmx1g -Xss8m \
    -Duser.language=en -Duser.country=US -Duser.timezone=UTC \
    -cp "$CP" edu.uky.cs.nil.sabre.Main -v \
    -p "02_实验/Planner_P0_Author_Binding_v0/verification/sabre_preflight/$case.problem" \
    -m bf -c t -h h+ -el 1 -vl 200 -gl 5000 -tl 5000 -atl 24 -ctl 2
done
```

These are the existing fixed limits: Sabre v0.8.0, best-first, temporal cost,
sum-graph heuristic, epistemic limit 1, search/space/time limits 200/5000/5000,
author temporal limit 24, character limit 2. No limits were raised to obtain
success. All three returned `Result: Success!`, utility 1:

| Input | Visited / generated | Plan actions | Goal |
|---|---:|---|---|
| `default.problem` | 13 / 230 | dispatch, get, move A, drop, move B, cloud seed, wait A, look B, meet | delivery=1, meeting=1, storm observation(B)=1 |
| `deadline-8.problem` | 11 / 212 | same as default | same; meeting is stamped at pre-action minute 8, permitted by closed [0,8] |
| `delivery-only.problem` | 4 / 39 | dispatch, get, move A, drop | delivery=1 only; no storm or meeting strengthening |

Native search durations reported 14 ms, 11 ms, and 5 ms respectively. These
are single local preflights, not performance measurements or evidence of
planner quality. The default/deadline plans include weather seeding because
it is an environmental feasibility action in this fixture, not an author
clause.

Parent-level raw rerun logs are [default](parent-default.txt),
[deadline 8](parent-deadline-8.txt), and [delivery-only](parent-delivery-only.txt).
The parent reran with JVM `-Xss1m`; the earlier run above used `-Xss8m`. This
is a JVM stack-size difference only, not a change to Sabre's search limits.

Input SHA-256:

```text
default.problem        678f39d7d1e7ee5f903b831e31037a2ff7606a7d6d95eea95c495f3d224fd981
deadline-8.problem     300c30956104852512e0c0e22bd994eebeabce6d4112a57a9d01369fcd7f894a
delivery-only.problem  3c565ae609519c63697d9869eddd7c3df2a01e34cdddad1134ad768cc3f41a5f
```

Renderer/source identifiers at preflight:

```text
author_binding_v0/compiler.py       ddd9caa68fb3c6eb0779fb0db5f2a0917dce145cb6d2ff58ee8fcdac4f826f4d
baseline_gate_v0/sabre_export.py    8845bf57d70f11ae03f2c38d894f47d235404d5e20bfd678ec81474cc417261e
integration_v0/monitor.py           d0df705ae69e7faf6831b99508303c8c15cd1ec421e088d5d905408c8b81f260
```

The 22/22 focused contract test log is `../author_binding_tests.txt`. No live
server/native scenario was started and no old evidence directory was written.
