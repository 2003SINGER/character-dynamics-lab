# Native Evennia P1 reproduction

This is a local platform reproduction of Evennia's own EvAdventure tech demo. It preserves the
stock room, NPC, and `AIHandler` state/action code. The only project adapter is a five-second
Evennia `DefaultScript` that calls each live EvAdventure mob's `.ai.run()` and records tick and
location transitions. A narrow compatibility shim supplies the missing `random` module name in
Evennia 6.0.0's `evadventure.npcs` module; the installed wheel and FSM methods remain unchanged.

## Environment and scope

- Python: Apple Silicon Python 3.12.14.
- Evennia: 6.0.0; Django 6.0.9; Twisted 24.11.0. Full installed package set is pinned in
  [requirements.lock](requirements.lock), copied from `pip freeze` in the isolated venv.
- Virtual environment and generated game/SQLite database: `_local_data/native_platform_v0/evennia/`
  (ignored local data).
- Tracked integration and reproduction code: this directory.
- Runtime evidence and non-secret command logs:
  `outputs/native_platform_p1p2_v0/p1_evennia_20261010/`.
- Summary/evidence: `outputs/native_platform_p1p2_v0/p1_evennia_20261010/P1_EVIDENCE.md`;
  captured status/listeners/source hash/movement JSON are under
  `outputs/native_platform_p1p2_v0/p1_evennia_20261010/runs/final-state-20261010/`.
- The actual rerun of bootstrap against the existing environment is logged at
  `outputs/native_platform_p1p2_v0/p1_evennia_20261010/runs/bootstrap-validate-20261010T1718Z/bootstrap.log`.
- No old project world was imported. Game index publication is disabled.

## Reproduce

From the project root:

```sh
bash tools/native_platform_v0/evennia/bootstrap.sh
bash tools/native_platform_v0/evennia/start_loopback.sh
```

`bootstrap.sh` creates the Python 3.12 venv if absent, installs the pinned lock, initializes the
native Evennia scaffold only if absent, installs the loopback settings overlay and ticker class,
and applies migrations. It does not reset an existing database or run the world builder again.

The native game command is run by a logged-in in-game builder account, such as through the browser
webclient at `http://127.0.0.1:14001/webclient/`:

```text
batchcode evadventure.build_techdemo
```

Evennia reports `Batchfile 'evadventure.build_techdemo' applied.` The four native CODE blocks build
the Techdemo Hub, Combat Arena and stock Training Dummy, plus the dungeon start area. Do not run it
again against the existing world because it is a creation batchfile, not an idempotent migration.

To enable the stock roaming state and periodic call adapter, run these two in-game `py` commands:

```text
py from evennia import search_object; search_object("Training Dummy")[0].ai.set_state("roam")
py from evennia import create_script; create_script("typeclasses.evadventure_ai_ticker.EvAdventureAITicker", key="native-p1-evadventure-ai-ticker")
```

Read persisted evidence without modifying the game:

```sh
cd _local_data/native_platform_v0/evennia/nativep1
DJANGO_SETTINGS_MODULE=server.conf.settings ../venv/bin/python -m django shell -c 'from evennia.objects.models import ObjectDB; n=ObjectDB.objects.get(id=10); print(n.db_location_id, n.attributes.get("ai_state", category="ai_state"), n.attributes.get("native_p1_tick_count", category="native_p1"), n.attributes.get("native_p1_tick_events", category="native_p1", default=[]))'
```

The player UI can move objects with the stock Evennia `get` and `drop` commands. The NPC remains an
official `EvAdventureMob` and roams through its stock exits; this does not establish psychological
realism or broad NPC autonomy. When a player is in the mob's room, the upstream state machine may
switch it into combat instead.

## Addresses and process control

- Browser webclient: `http://127.0.0.1:14001/webclient/`
- Telnet: `127.0.0.1:14000`
- Websocket: `127.0.0.1:14002`
- Evennia AMP: `127.0.0.1:14005`; internal webserver port: `127.0.0.1:14006`
- Start: `bash tools/native_platform_v0/evennia/start_loopback.sh`
- Stop only this instance: `bash tools/native_platform_v0/evennia/stop_loopback.sh`
- Inspect PIDs: from the game directory, `PATH="../venv/bin:$PATH" ../venv/bin/evennia status`

The current browser login is an isolated Evennia superuser used to run the official builder.
No ordinary player account was prepared or tested in this run; the native connection screen
does advertise account creation. Its private credential is not written to source or output
logs. Use an ordinary account for a later permission-level playtest.

## Limits and failures

The first seven ticks using the stock `ai_roam` failed. Evennia 6.0.0's installed `npcs.py` imports
`choice` directly but calls `random.choice`, producing `NameError: name 'random' is not defined`.
This remains a native, unmodified failure. The adapter's `npcs.random = random` shim makes the
official handler callable without editing the wheel or replacing any state/action method. Report
that result as `ADAPTED_PASS`, never as an unmodified native pass. Preserved native server traceback
and movement records are in the output directory.

The upstream source labels EvAdventure AI work in progress. The successful evidence is limited to
the exact observed roaming transitions in this techdemo, not a claim that the full Evennia game
implements continuous autonomous life simulation.
