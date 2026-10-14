# Open Adventure 1.22: build and native short replays

## Fixed upstream and isolated build

- Official project: https://gitlab.com/esr/open-adventure
- Tag object: `1.22` → `a58e03033307122cd56cb2c60259c377b49230dd`
- Peeled source commit: `e6160529e70a8c7a06b9a5f190d69aa35c4c62f5`
- Isolated source checkout: `_local_data/external_games/open_adventure/upstream` (detached at the peeled commit)
- License: BSD-2-Clause, as declared by the upstream Makefile and `COPYING`; local `COPYING` SHA-256: `1736e44e3dd4fab08c3291434c45ccf7f6933704ed0648516afb056641fcf306`
- The newest build/check capture is [BUILD_TEST_LOGS.json](BUILD_TEST_LOGS.json); it preserves separate raw stdout/stderr and exit codes for both commands, host/tool versions, and source hashes. Its build and `make check` exit codes are both `0`; the resulting executable SHA-256 is `7d465d17437ba4974980b00302aed02ab153efa3da7fe89f1eceb5dd0b92b549`.
- Generated `dungeon.c` and `dungeon.h` were produced by the unmodified upstream `make_dungeon.py` from `adventure.yaml`; no rules, NPC code, templates, or generated source were hand-edited. They remain only in the ignored local checkout.

Host/tool versions: macOS 27.0.1, arm64; Python 3.12.14; PyYAML 6.0.3; Apple clang 21.0.0; GNU Make 3.81. The build uses Command Line Tools' existing system libedit; no package was installed. Upstream tracked-source snapshot SHA-256 recorded around each episode: `6eec67f3b0dffc072bb2b00d0e377335e6e9e13182bb4a8b2d72c6fa199b5b77` across 256 tracked files; all three run manifests report the same before/after snapshot.

Build command:

Run from the project root, with the already installed isolated Evennia venv's
`bin` directory first on PATH for the upstream Python/YAML generator (on
another machine, provide an isolated Python with PyYAML). The SDK include
path is macOS-specific. No global Python or package configuration is changed.

```sh
env PATH="$PWD/_local_data/native_platform_v0/evennia/venv/bin:$PATH" \
  make -B -C _local_data/external_games/open_adventure/upstream \
  CC=clang LIBS=-ledit \
  INC=-I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include
```

Exit code: `0`. Captured stdout:

```text
./make_dungeon.py
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g  -I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include  -c main.c
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g  -I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include  -c init.c
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g  -I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include  -c actions.c
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g  -I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include  -c score.c
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g  -I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include  -c misc.c
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g  -I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include  -c saveresume.c
./make_dungeon.py
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g   -c dungeon.c
clang -std=c99 -Wall -Wextra -Werror -D_DEFAULT_SOURCE -DVERSION=\"1.22\" -O2 -D_FORTIFY_SOURCE=2 -fstack-protector-all  -g   -o advent main.o init.o actions.o score.o misc.o saveresume.o dungeon.o  -ledit
```

## Official upstream tests

Command:

```sh
env PATH="$PWD/_local_data/native_platform_v0/evennia/venv/bin:$PATH" \
  make -C _local_data/external_games/open_adventure/upstream check \
  CC=clang LIBS=-ledit \
  INC=-I/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include
```

Exit code: `0`; result: `115 tests, 0 failures`. The upstream Makefile also attempted optional `pylint`, `cppcheck`, and `spellcheck` checks. They were unavailable and explicitly ignored by upstream (`@-`); the functional test suite completed.

Captured command output:

```text
/bin/sh: pylint: command not found
make: [pylint] Error 127 (ignored)
make: cppcheck: No such file or directory
make: [cppcheck] Error 1 (ignored)
make: spellcheck: No such file or directory
make: [spellcheck] Error 1 (ignored)
...................................................................................................................
115 tests, 0 failures.
```

The thin wrapper's focused tests: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tools.open_adventure_v0.tests.test_runner -v` → 8 tests, all passed. They cover fixed source identity, all acceptance gates, and failure/timeout evidence retention; the mocked timeout/main-flow checks do not launch the game or add an episode.

## Three upstream-fixture episodes

Each record contains the fixture input, normalized stdin actually sent, complete raw stdout/stderr, exit codes, host/Python version, binary SHA-256, and source manifests. All three episodes used the then-current executable SHA-256 `9be0dea71ef185969f729f6c5544e8b9d67f1d59fa2221b61a4c1fc41c23f122`. Later forced builds produced different executable hashes (`0fa9466406df6485dfb93656229df621ae75b15a104f65b25f163194e91500b3`, then `7d465d17437ba4974980b00302aed02ab153efa3da7fe89f1eceb5dd0b92b549` in the raw build capture). Existing episode evidence remains attributed to `9be0...c23f122` and was not rerun. Each episode starts a fresh process, sends the upstream fixture's fixed in-game `seed` command, then directly reruns the same executable with the same stdin. No state is inferred from hidden game fields. The game itself decides which commands after a terminal event it consumes.

| Episode | Upstream fixture | Exit | Output bytes | stdout SHA-256 | Direct replay |
|---|---|---:|---:|---|---|
| Bird and jade | `tests/dropcagedbird.log` | 0 | 2,786 | `417634ff10b823ecb5e9225af1b347a54ec28ad96ce5454645b323222857e5f2` | byte-identical |
| Pirate takes treasure | `tests/pirate_carry.log` | 0 | 6,097 | `c4a3bc4c8bb255df4182776b32e3ae9405f317a089062c1941963b3513902f22` | byte-identical |
| Dwarf process | `tests/dwarf.log` | 0 | 6,407 | `a47d9904cead619b8b952aeea61ee83767c4045af4bda70dff1a7652246a8c9b` | byte-identical |

Run folders:

- `runs/native-bird-free-and-carry-20261014T010515Z-842eac/`
- `runs/native-pirate-carry-20261014T010515Z-10819a/`
- `runs/native-dwarf-process-20261014T010515Z-012dc0/`

These are complete scripted episodes, not a live per-turn control API. The `-o` mode accepts a full stdin transcript, so this adapter records episode-level output and does not claim to expose a separate observation after each command.
