# Exact commands — v4.3 one-day gate

Working directory: `/Users/2003singer/Workspace/Research/character-dynamics-laya-work`.

```sh
cmake -S 'Demo codex-generated' -B '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build' -DCMAKE_BUILD_TYPE=Release -DCHARACTER_DYNAMICS_GIT_REVISION=66ebfe72dc3fd5987a040adb61bec5b5a9a1b646
cmake --build '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build' --target character_dynamics_long_horizon -j4
'/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build/character_dynamics_long_horizon' 1000 5000 1 balanced '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/rule/trace.jsonl' boundaries
```

No-history live and strict replay (each proxy ran in a separate shell session and was stopped after its executable finished):

```sh
python3 'Demo codex-generated/tools/laya_typed_proxy.py' --cassette '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/no_history/live-cassette.jsonl' --device mps --port 8753
'/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build/character_dynamics_long_horizon' 1000 5000 1 balanced '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/no_history/live-trace.jsonl' boundaries --laya-port 8753 --laya-no-history
python3 'Demo codex-generated/tools/laya_typed_proxy.py' --cassette '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/no_history/replay-cassette.jsonl' --replay '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/no_history/live-cassette.jsonl' --device cpu --port 8754
'/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build/character_dynamics_long_horizon' 1000 5000 1 balanced '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/no_history/replay-trace.jsonl' boundaries --laya-port 8754 --laya-no-history
```

History live and strict replay:

```sh
python3 'Demo codex-generated/tools/laya_typed_proxy.py' --cassette '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/history/live-cassette.jsonl' --device mps --port 8755
'/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build/character_dynamics_long_horizon' 1000 5000 1 balanced '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/history/live-trace.jsonl' boundaries --laya-port 8755
python3 'Demo codex-generated/tools/laya_typed_proxy.py' --cassette '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/history/replay-cassette.jsonl' --replay '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/history/live-cassette.jsonl' --device cpu --port 8756
'/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/build/character_dynamics_long_horizon' 1000 5000 1 balanced '/Users/2003singer/Workspace/Research/_character_dynamics_laya_runs/laya_v43_66ebfe7_20260925/history/replay-trace.jsonl' boundaries --laya-port 8756
```

The sandbox denied loopback binds/connects initially; the same exact local proxy and executable invocations then ran with loopback access allowed. The live proxy banners, device fallback and checkpoint temperature warning are recorded in `RESULTS.md`.
