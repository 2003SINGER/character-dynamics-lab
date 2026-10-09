# P1 Evennia evidence and limits

Run: `final-state-20261010` (paths under `runs/final-state-20261010/`). The game database and
virtual environment live only in the ignored `_local_data/native_platform_v0/evennia/` tree.

## Reproduction state

- Isolated runtime: Apple Silicon Python 3.12.14; Evennia 6.0.0; Django 6.0.9; Twisted 24.11.0.
- The resolved environment is pinned in `tools/native_platform_v0/evennia/requirements.lock`.
- Native initialization used `evennia --init nativep1`; initial `evennia migrate` applied all
  Evennia migrations successfully.
- Parent's browser ran the native in-game command `batchcode evadventure.build_techdemo`; browser
  output confirmed `Batchfile 'evadventure.build_techdemo' applied.` No custom room/NPC was written
  in place of the official builder.
- Exact object readback: `#4 Techdemo Hub` (`EvAdventureRoom`), `#7 Combat Arena`
  (`EvAdventurePvPRoom`), `#10 Training Dummy` (`EvAdventureMob`) located in `#7`, and `#13 Dungeon
  start room` (`EvAdventureDungeonStartRoom`). The parent separately audited the browser movement of
  `P1BrowserToken #3` using native `get`/`drop` commands.
- Browser URL: `http://127.0.0.1:14001/webclient/`. Current login is `p1admin`, an Evennia
  superuser retained by the parent for browser testing; no ordinary account was created. Its
  password is intentionally absent from this file and all logs.
- Actual final process state and PID: Portal `61250`, Server `62143`; captured in `status.log`.
  `info.log` and `listeners.log` show all external listeners bound to `127.0.0.1`; game index is
  disabled. Stop only this instance with `bash tools/native_platform_v0/evennia/stop_loopback.sh`.

## NPC tick evidence

The parent set `Training Dummy #10`'s official handler state to `roam` and created the
`typeclasses.evadventure_ai_ticker.EvAdventureAITicker` script (5 second interval). The ticker only
calls the stock `.ai.run()` and records tick count, state, source room and destination room. The
standalone JSON evidence in `runs/final-state-20261010/movement.json` contains 40 recent transitions;
for example:

- tick 23: `#4 Techdemo Hub → #2 Limbo`
- tick 24: `#2 Limbo → #4 Techdemo Hub`
- tick 25: `#4 Techdemo Hub → #7 Combat Arena`

The observed roaming behavior is limited to the EvAdventure map and its random exits. It is not
evidence of psychological realism or broad life simulation. The upstream state machine may switch
to combat when a player is in the same room.

## Upstream defect and adapted result

The pre-shim Evennia server log is preserved as `server.log`. It records repeated
`NameError: name 'random' is not defined` at EvAdventure `npcs.py:331` in `ai_roam`. The installed
source imports `from random import choice` but calls `random.choice`. The recorded SHA-256 is
`9a84dd3683cd5761b2eaaffb2b326561950cd6b54e457a42ecc5173e208b6e6f`; the same file remained
unchanged after the adapter was added. Import excerpts and the failing source lines are preserved as
`evadventure_npcs_imports.log` and `evadventure_npcs_roam.log`.

The authorized compatibility shim sets `evadventure_npcs.random = random` inside the local ticker
module. It does not change the wheel or any FSM method. After that shim, the persisted transition
events show repeated movement. Report the unmodified upstream NPC FSM as `FAIL` and this local shim
configuration as `ADAPTED_PASS`.

## Failed attempts and capture gaps

- A first non-PTY `evennia start` repeatedly skipped the superuser prompt and ended in a Django
  `RecursionError`; the tool response was truncated and no raw file was saved. Starting in a PTY
  created `p1admin` successfully but the Portal failed with `[Errno 2] No such file or directory:
  'twistd'`. Adding the isolated venv's `bin` directory to `PATH` fixed startup. Reproduction start
  logs thereafter are saved separately in unique run directories.
- Initial successful migration stdout was visible in the tool response (`Applying ... OK`) but was
  not persisted as a raw file at that time. A later tracked bootstrap validation was run against
  the existing venv and database; actual pip/migrate stdout+stderr is saved at
  `runs/bootstrap-validate-20261010T1718Z/bootstrap.log`. It reports all lock packages already
  satisfied, `No migrations to apply`, and an upstream Django warning about model changes without
  migrations. No `makemigrations` was run.
- A brief nonstandard Python Telnet attempt with a separate Django-created superuser did not build
  any world objects; its command response was `Command 'batchcode evadventure.build_techdemo' is
  not available.` The temporary helper was removed. The temporary `p1builder` superuser was deleted
  by exact ID/name after verifying it had no login record; it was created for this experiment, not
  a user account. The native builder was then run successfully through the parent's existing
  browser session. Do not treat the Telnet attempt as a valid native builder invocation.
- The first movement JSON query ran outside the game directory and failed with `No module named
  'server'`; that failure is preserved in `movement_capture_failure.log`. The successful read was
  repeated from the generated game directory and saved as valid JSON.

Raw Evennia logs, process info, loopback listeners, versions, source provenance, and movement JSON
are stored under `runs/final-state-20261010/`; the real bootstrap verification output is under
`runs/bootstrap-validate-20261010T1718Z/bootstrap.log`. Do not overwrite a run directory;
bootstrap/start/stop scripts create unique `RUN_ID` directories and refuse reuse.
