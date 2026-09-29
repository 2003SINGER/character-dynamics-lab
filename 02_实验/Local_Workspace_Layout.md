# 本地工作区布局与迁移记录

整理日期：2026-09-29

## 唯一工作区与 Git 状态

- 本机唯一 canonical checkout：`/Users/2003singer/Workspace/Research/character-dynamics-lab`。
- 活动分支：`webgpt-sync`，迁移基线 `0a7d7a25d2c5a995f029dfc8bafa2352f15176d0`。旧 `character-dynamics-lab` 的本地分支 `main` (`e9ad2ebf329e8259b35f3ee0ef0492485d85c3ff`) 与 `data-ownership-cleanup` (`c23df18424c6da3303e36112048d4f41891859a2`) 已在此 checkout 恢复，旧仓库 refs 另存于 `refs/archive/old-lab/`。这些本地 refs 不改变远端分支。
- 旧主仓库 `.git` 完整归档（含 config、refs、reflogs、objects 与 worktree 登记）位于 `outputs/local_migrations/20260929/git-archives/old-character-dynamics-lab-dotgit.tar`。旧的 prunable `/private/tmp/character-dynamics-living-calibration` 登记只保留在该归档内。此归档不包含 `outputs/external_assets_2026-09-06/` 中三个数据仓库自己的 `.git` 元数据。
- `/private/tmp/laya-v4-rule-baseline` 是原有 detached linked worktree；迁移后仍指向 canonical checkout，HEAD 保持 `81694a923fbcddf73f40fe9f090ced9163d5571c`。

## 数据与实验条件

合并只统一仓库根路径，不合并实验条件。`_local_data/`、`outputs/`、`02_实验/` 中原有数据和运行产物保持 relative path、条件名和 run ID；目标路径有相同文件时，仅在 SHA-256 相同后去重，不同内容不得互相覆盖。版本化的 `outputs/` 文件以活动分支文件为准，旧的不同版本可从 `data-ownership-cleanup` 或 `refs/archive/old-lab/heads/data-ownership-cleanup` 读取。`outputs/laya_runs/` 的原始 Laya 运行文件不改写。`.workbuddy/` 是本机私有工作记忆，保留在仓库根的原位置并由 `.gitignore` 忽略。

原 laya-work checkout 的根 `build/` 与 `Demo codex-generated/build/` 缓存整体移至 `outputs/local_migrations/20260929/build_caches/`。这些缓存只供历史查阅，不作为迁后构建结果；运行产物目录内部的 build 文件未移动。

## 审计材料与旧路径校验

- `pre_migration_inventory.tsv` 保存迁移前 9,797 条普通 worktree 文件路径、Git 状态、大小和 SHA-256；其中记录的原始根路径保持不变。该清单排除了 `.git` 目录；初始扫描错误地同时排除了嵌套 `.git`，因此不涵盖三个数据仓库的 Git 内部文件。
- `before_state.txt` 保存迁移前 refs、状态和 worktree；`old_lab_payload_moves.tsv` 记录旧 lab 所有 ignored/untracked 本地文件的源路径、目的路径、SHA-256 与同卷移动结果。
- `final_path_mapping.tsv` 将上述 9,797 条清单记录逐条映射到 canonical 相对路径或 Git `revision:path`；`post_migration_inventory.tsv` 是包含 nested Git 恢复与验证日志的迁后文件核验清单（不对自身做递归哈希）。嵌套 Git 存活对象的补充映射在 `nested_git_survivors.tsv`。

## 嵌套 Git 元数据恢复边界

旧 `outputs/external_assets_2026-09-06/` 含 JerichoWorld、FarmQuest、LIGHT 三个嵌套 Git 仓库。迁移清单排除了 `.git`，因此没有记录这些嵌套仓库的内部文件。2026-09-29 对 staging 路径执行清理时，命令在带 macOS `uchg` 标记的 pack 文件处报告 `Operation not permitted`，并移除了 staging 其余内容及三个仓库的部分 `.git` 元数据；随后只将残存 `outputs/` 同卷移动至 `staging_remainder/`，未再次删除。完整命令、影响范围和已知限制见[清理事故记录](../outputs/local_migrations/20260929/cleanup_attempt.txt)；幸存的 9 个 `.pack`、`.idx`、`.rev` 文件及其 SHA-256 见 `outputs/local_migrations/20260929/nested_git_survivors.tsv`，原字节仍保存在 `staging_remainder/`。

独立恢复后，三个 canonical 数据目录均有可用的浅 Git 仓库：每库仅暴露一个从幸存 pack 恢复的 commit，以 `recovered-from-surviving-pack` 为 HEAD/ref，并将缺失父历史标为 shallow；pack 校验、Git fsck、tracked tree 对照和工作树状态均通过。恢复细节、commit/tree IDs、逐文件对照和来源限制见 `outputs/local_migrations/20260929/nested_git_recovery/README.md`。这是可用性恢复，不是原 `.git` 元数据的字节级恢复：原 HEAD、refs、config、reflogs、remotes、时间戳及完整父历史不可恢复；数据集来源标记也不等于精确 commit provenance。普通数据文件和幸存 pack 字节仍已保留。

原运行证据保持字节不变。特别是 `outputs/laya_runs/laya_v43_66ebfe7_20260925/SHA256SUMS` 保留旧 checkout 的绝对源码路径和 Hugging Face cache 路径；其自身 SHA-256 为 `7e29908f18a8e3825182eed87ffd9aba07869e07fd6bb09bc1923adc65fbceb2`。验证时只在管道中把旧 checkout 路径前缀映射到 canonical 路径，不编辑证据文件：

```sh
(
  cd outputs/laya_runs/laya_v43_66ebfe7_20260925 || exit
  sed 's#  /Users/2003singer/Workspace/Research/character-dynamics-laya-work/#  /Users/2003singer/Workspace/Research/character-dynamics-lab/#' \
    SHA256SUMS | shasum -a 256 -c -
)
```

其余外部模型缓存路径保持原值。迁移不修改冻结 artifact，不启动模型或新实验；项目当前暂停边界继续有效。
