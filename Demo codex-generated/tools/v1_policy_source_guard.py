"""Guard the V1 policy against reintroducing raw continuous-state utility terms."""
import re, sys
from pathlib import Path

path = Path(sys.argv[1])
bad = re.compile(r"state\.(fatigue|boredom|satisfaction|task_pressure|anxiety|screen_strain|hunger|bathroom_urge)\s*[*/+-]\s*0?\.?\d")
violations=[]
for n,line in enumerate(path.read_text().splitlines(),1):
    if bad.search(line) and "commitment_can_bias_study" not in line and "urgent_threshold" not in line:
        violations.append(f"{n}: {line.strip()}")
if violations:
    raise SystemExit("raw V1 policy coupling found:\n" + "\n".join(violations))
print("v1 policy source guard: PASS")
