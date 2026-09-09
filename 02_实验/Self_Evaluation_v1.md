# Self-Evaluation v1

v1 reports mechanism vectors and hard gates rather than a naturalness score.
The current implementation consumes the frozen paired deadline and commitment
fixture traces. Believability and external validity remain unscored.

Run with `tools/self_evaluation_v1.py --deadline <csv> --commitment <csv> --out <json> --source-revision <git-revision>`.

The commitment fixture includes both completion boundaries: observable typed
self-action feedback closes the commitment (`none`), while the same world
completion with feedback hidden leaves it `active`. The recorded run is
provenance-bound to revision `a3a4488`; all eight hard gates are true.
