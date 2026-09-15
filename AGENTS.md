# Character Dynamics Lab Workspace Rules

## Scope

- `D:\desk\科研\character-dynamics` owns exploration of dynamic character behavior consistency and conditional behavior prediction in constrained worlds.
- It is independent of the paused `D:\desk\科研\characters` state-stream coupling project. Do not silently merge their questions, sources, or claims.

## First Read

- Read `README.md` first.
- Then read `00_研究设计\README.md` and follow its ownership routing: full mechanism, research questions, open questions, TODO, and implementation status each have one owner.
- For related work, read `01_文献\README.md` before making novelty or gap claims.
- For origin and evidence boundaries, read `90_原始材料\2026-09-01_动态人物世界模拟探索\阅读判断.md`.

## Boundaries

- The executable reference demo is an interface/stress-test artifact, not evidence that the full mechanism or a research hypothesis is validated. Check `00_研究设计\当前实现进度.md` for the code baseline and limitations.
- Do not claim a psychological mechanism, literature gap, benchmark, novelty, training result or publication potential without fresh verification.
- Keep research question, validation engineering and optional game implementation distinct.
- Preserve raw dialogue and do not overwrite it. **Collaboration protocol (user-confirmed 2026-09-05):** long pasted review blocks are presumed to be WebGPT's repository review unless the user labels them otherwise; for project decisions and code/document changes, WebGPT review has the same working authority as the user's direct messages. Short, direct messages from the user are presumed to be the user's own instruction. When ambiguity remains, preserve the uncertainty rather than inventing attribution.

## Sync

- Sync LifeOS only when the project lifecycle, commitment, priority, deadline or waiting state changes.

## Version Control

- After every verified project edit, create a local Git commit and push it to `webgpt-sync`. Do not leave verified changes only in the local worktree.
- The default review loop is: WebGPT reviews the repository → user pastes the review → Codex applies verified changes → Codex commits and pushes to `webgpt-sync` → WebGPT reviews that branch again.
- `main` is protected: never merge or push to `main` unless the user explicitly instructs that specific `main` push or merge. An instruction to commit, publish, sync, or push changes without naming `main` authorizes only `webgpt-sync`.

## Scheduler-native runtime

- Preserve Action-Step Reference v0. Runtime-native work must not add a second clock, let an action advance runtime time, shortcut `W → S`, or let a hidden W event open a character gate.
- Treat W/O/S/P/RunningAction as persistent nodes and deltas/events as the flow. Scheduler-native fixtures use the canonical runtime bridge rather than manually synchronizing timestamps or projecting W facts.
