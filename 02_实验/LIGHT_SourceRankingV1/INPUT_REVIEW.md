# SourceRankingV1 实现验收与下一动作

日期：2026-10-06。状态：**INPUT / TRAINER_SYNTHETIC / EXECUTION_PARENT_AUDIT_PASS / REAL_FIT_RUNNING**；实现为 `READY_FOR_INDEPENDENT_REVIEW`，不是 `CLOSED`。冻结投影仍为 `training_authorized=false`；单独的 `SOURCE_CONDITIONAL_DEVELOPMENT` 执行记录已准入。这不升级 actor-visible / Runtime policy / formal test / 心理有效性。

本页唯一维护投影/训练器实现验收与当前下一动作。[README](README.md)冻结任务、通道和拟训练规格，保留冻结时的未准入状态，不随实现进度改写；[LIGHT 来源审计](../../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)拥有 source/observation 的未准入结论。以下投影证据和合成训练证据分别成立，不等于演员可见观察契约、Paper-0 或真实数据上的预测通过。

## 修订与执行证据

主代理发现并要求修正两处会破坏比较的问题：初稿 `context_only` 去掉 persona，混淆历史增益；初版 feature entry 接受 upstream schema 而不是 projected schema。最终对照静态条件相同（只有命名消融例外）；[project_inputs.py](project_inputs.py)的唯一模型入口 `features(projected_row)`读明确允许字段，不读标签、provenance、admission。核心 partner command 污染或私有 extra feature key 会拒绝，不依赖“调用者不会传错”。

- [9 个合成测试](test_project_inputs.py)与 `py_compile` 通过。覆盖真实 projected schema、metadata 毒访问、gold mutation noninterference、core/diagnostic 隔离与空 turn 保留、正控、非法 schema/role/type/ref/split、支持集重数和内部空格保持、重复 source key、固定 hash、existing/overlap/symlink/outside-root 路径拒绝。
- 真实 CLI 成功生成全量输出；再次调用同一默认路径返回 **1 / refusing existing output**，产物 hash 不变。该预期拒绝不是一个新的成功生成。
- 主代理独立逐行构造预期投影，不调用 projector；全量比对输出字段、history views、provenance、split 与源行。两种 view × 有/无 context 的 feature entry 均做 metadata 毒访问检查，合法 prior dialogue 改动为正控。重新计算 manifest 的全部 split/episode/actor/group/depth/role-channel/eligibility 计数及 cohort/source-key digest；全部相符。
- 全部 13,463 行保留。train / validation / excluded bucket9 = **9,530 / 2,717 / 1,216**；episode 各 **3,490 / 986 / 468**，不跨 split。唯一支持标签各 **9,488 / 2,707 / 1,211**，歧义各 **42 / 10 / 5**，缺席与坏支持均 0。这里只是监督 eligibility 计数；没有训练或评分 bucket9，也没有删掉歧义记录。
- 在 **9,397** 个 target prefixes 中存在 prior partner raw command：core 全部置 null，diagnostic 原样保持。group 总数仍 **116,961**，不是 unique events。保留结构/role 仍可能带来源信息，不声称合法 `H^obs` 或完全去除未验证信息。

## 本机可复核产物

路径：`outputs/light_source_ranking_v1_20261006/contract_v1/`（Git 忽略）。包括 projected JSONL、manifest 和协议/code/test 的原字节 snapshots；不改旧 source、旧 fits 或 cohort。

| 文件 / 项 | SHA-256 |
|---|---|
| 固定 upstream before-turn JSONL | `b414f176bf7c6d0e1f47536bab8c251ae7d39ead5b40550310127294f74e5646` |
| projected_inputs.jsonl（74,463,375 bytes） | `2d839c62ddf2194b1968fe5b22913db9950aa10bd3647fe2179745b6b4efcef5` |
| protocol_snapshot.md | `5318bffe1f417e6ceb5dc5284fbcbb011808117f775d1225f66d61195528e3cf` |
| project_inputs_snapshot.py | `9c1850e38320ef459b38cc2740cbec6ff948036f8f564c9567f18aebbedc42d4` |
| test_project_inputs_snapshot.py | `748504e2167aa09c9b972cf1d8cc0d30b4abc01ad767ce814aaa318c63edc966` |
| 独立 parent audit script | `20beeaac0d6e7a089873a7d7700cbf1ab909eed710b5515fcbfdfe9915617e90` |

独立 verifier 在 `outputs/light_source_ranking_v1_20261006/parent_contract_audit_v1.py`。首次核验因重复计算固定大文件 hash 而主动中断；缓存该固定 hash 后重跑退出 0。未覆盖产物或将中断计为 PASS。它只适用于此 pinned artifact / snapshots；后续源码修改须建立新 contract 与新的验收记录。

```sh
python3 02_实验/LIGHT_SourceRankingV1/test_project_inputs.py
python3 outputs/light_source_ranking_v1_20261006/parent_contract_audit_v1.py
# 新生成必须选择尚不存在的路径，不能覆盖 contract_v1。
python3 02_实验/LIGHT_SourceRankingV1/project_inputs.py \
  --output outputs/light_source_ranking_v1_20261006/contract_recheck_new
```

合成测试已注册 CI。全量本地材料被忽略，**CI 不执行本机全量数据验收**；不能把 CI 绿当作独立人类准入。

## 历史阶段：40ddbb0 的训练器合成功能验收

[train.py](train.py)已实现冻结的九个条件：context-only、last2、learned pool、GRU core、三个命名消融、partner raw command diagnostic 和 uniform。学习条件实际执行 Adam / cross-entropy 更新，不是把手写分数改名为训练；uniform 无参数。训练器不接入 Runtime。

- [20 个合成合同测试](test_train.py)全部通过。涵盖独立 hash oracle、metadata/label noninterference、合法通道正控、mask 的文本及 presence bits、pool permutation / GRU order / last2 padding、八个学习条件的 encoder/head 梯度与参数更新、训练 loss 下降、validation 无梯度与错误 split 拒绝、earliest-min checkpoint 深复制、同 seed 复现、candidate-order tie ranks、非等长 episode 的 row-weighted cluster bootstrap、九条件同一有序 cohort、输出/符号链接拒绝及 provenance。合成 loss 下降只证明更新路径，不证明真实任务有效。
- 主代理另存一次完整 CLI 合成运行：8 个生成行，固定 seeds 7/19/31、15 epochs；24 个学习 checkpoint + 3 个 uniform 条件运行。独立 verifier 不调用训练器的训练/指标/汇总 helpers，重新构造特征、加载全部 checkpoint，核对 **360 条 epoch 记录、216 条逐行预测**、NLL/top1/MRR、参数量、earliest-min selection、两项主比较及六个 depth strata 的 seed-average / episode bootstrap。全部相符；它仍复用模型类加载参数，不声称第二套完全独立的神经网络实现。
- 再次使用同一 output 路径退出 1 / `refusing existing output`；随后独立核验全部输出 hash 不变。报告文件、逐行预测、checkpoint 与实际 code/test/protocol/input 原字节 snapshots 均被 provenance 覆盖；provenance 不对自身做循环 hash。snapshot 中的 INPUT_REVIEW 是运行前历史状态，不冒充更新后的本页。
- 只读核验 pinned 真实输入的 13,463 行、hash、split 与 source/cohort digest 通过；真实拟合入口随后按预期拒绝。没有真实 source 拟合、bucket9 评分、超参数搜索或旧 fit 重算。

本机产物（Git 忽略）：`outputs/light_source_ranking_v1_20261006/trainer_synthetic_parent_v1/`；独立核验脚本 `outputs/light_source_ranking_v1_20261006/parent_trainer_audit_v1.py`。

| 项 | SHA-256 |
|---|---|
| 40ddbb0 的 train.py snapshot（不是后续 live source） | `d6aa61f48ddce875c4d763680cf0028cad0e243e60ee190bbff62e39c248a037` |
| test_train.py | `2684094f830a84caf9313db4b2c7e3ff056cdecad3c3d344c591ed7535f3ca46` |
| parent trainer audit script | `ca9e56bf1f245d2ea4eafcc7c9e31bef1c10c809ca9be40cbad890d33768ea6a` |
| synthetic provenance.json | `97aa9caa749f5f8556b06617fe01435f194065d0ac5012bcacc4070a1bcccf3e` |

```sh
/opt/homebrew/opt/python@3.12/bin/python3.12 02_实验/LIGHT_SourceRankingV1/test_train.py
/opt/homebrew/opt/python@3.12/bin/python3.12 outputs/light_source_ranking_v1_20261006/parent_trainer_audit_v1.py \
  outputs/light_source_ranking_v1_20261006/trainer_synthetic_parent_v1
# 新合成运行需换未存在的路径；不加载真实输入。
/opt/homebrew/opt/python@3.12/bin/python3.12 02_实验/LIGHT_SourceRankingV1/train.py \
  --synthetic --out outputs/light_source_ranking_v1_20261006/trainer_synthetic_recheck_new
```

本机 Python 3.12 / torch 2.14.0 / numpy 2.5.3；CI 独立 job 使用 Python 3.12 / torch 2.14.0+cpu / numpy 2.5.3，仅执行合成合同。不声称 Mac/Linux 跨平台 bitwise 一致。cost 是该进程的运行/推理耗时与全进程 peak RSS，不是模型独立内存测量或效率优势证据。

`40ddbb0` exact-head CI run `37366708154` 的 attempt 2 全部成功；attempt 1 的两个 job 因 hosted runner 未分配而取消，未执行测试。重试没有修改代码或删测试。上述独立 v1 verifier 要求 live source 等于历史 snapshot；后续源代码变化后，应使用新产物和新 verifier，不能将不匹配解释成历史产物失效或覆盖历史运行。

既有 build 通过；full CTest 在允许 loopback 的执行环境 **49/49** 通过，Reference verification 全部通过。首次受限环境的 7 个 socket 测试因 bind 权限失败，未计作代码 PASS。既有 CTest 的 ResearchDynamicsV1 intervention fixture 会重写历史 JSON；本次这些 tracked 内容逐字节未变，但不声称所有既有测试无写副作用。新合成测试不重算这些旧 fixtures。Repository health 退出 0，有 3 个警告：原有大 simulation.cpp / 重复原始材料，加新 train.py 52,810 bytes 的体量警告；不隐藏警告，也不在本阶段扩模块重构。

## 单独 DEVELOPMENT 执行准入（当前）

[fit_source.py](fit_source.py)只读固定路径的父代理准入记录，无授权、协议、数据或超参数 override。真实分支与合成分支共用训练/报告管线，但真实分支忽略调用者的 Example，必须从已验收的 projected/source 原字节重新构造输入；原协议、投影、code/test、cohort/split 和固定配置均核对后才创建独占输出。Reference / Demo / Runtime / Theory-S 参数未变。

父代理独立复核修掉：未定义的 run-root 变量、准入与任意调用者 Example 可拼接、真实报告误用 synthetic 名称、实际配置/准入标志歧义，以及真实运行缺少完整协议/code snapshots。最终本机重跑 **20 + 9 + 8 tests PASS**，新 8 项只用假记录/假数据，包含成功拟合与失败前置路径；CI 新增的是这 8 项测试，不读取本机真实 cohort。

当前版本合成产物 `outputs/light_source_ranking_v1_20261006/trainer_synthetic_parent_v3/` 经父代理独立 `parent_trainer_audit_v2.py` 核验：24 checkpoints、360 epoch records、216 predictions、loss/rank/metrics/paired intervals/provenance 全部相符。此前 `parent_v2` 保留为开发阶段产物，其 verifier 首次因要求当时未保存的新入口 snapshot 而拒绝，不记作已通过的最终验收。

实际执行记录（Git 忽略）为 `outputs/light_source_ranking_v1_20261006/execution_admission_v1/EXECUTION_ADMISSION.json`，SHA-256 `391b263d434c053f06738c99771246ed07abbb823398bcb0fe7ce9b1cc01b837`。依据是用户授权的 DEVELOPMENT 目标下的父代理实现审查，不是人类语义准入。其 `training_authorized=true` **仅限来源条件 DEVELOPMENT 排名**；actor_forecast / runtime_policy / formal_test / psychological_validity 全 false。原始 protocol/projected 的 false 原样保留，两者不是同一授权。

| 当前执行 pin | SHA-256 |
|---|---|
| train.py | `0a2afeaf824bf20ae6fa1067818306617d2e3cf752df1c1c91bf9aefe67eb0e3` |
| fit_source.py | `a9170d56d62779a9aeb7d2b52fa99c0ed3477d551b57a99f638044a46f58eee7` |
| test_execution_admission.py | `49cc8c1f372bfe70ad6a580479f1aa7b7959ad6d8d2153bee732663e2d529cf3` |
| 独立 parent_trainer_audit_v2.py | `ee81cb15c1b12907a9851adba30e37deab7316a0f3799eb8733e7c15271245d9` |
| parent_v3 synthetic provenance | `36123c114c4f51457bdcd672ae12957e5a221872d0a6ec99d07f3842677e894a` |

原始 13,463 行、9 条件、seeds 7/19/31、15 epochs 与冻结配置不变；bucket9 不训练、不评分。新输出必须是固定 `outputs/light_source_ranking_v1_20261006/trainer_runs/` 的未存在子目录；记录会连同输入/code 原字节保存，epoch 与阶段 checkpoint 实时 flush/fsync。没有覆盖或 resume 入口；中断产物不得冒充完整报告。

### 实际运行记录

已验收实现提交并推送为 `c8acd057c503788b79e7ff635f6c4a85fee8daf7`，远端 main 仍为 `e9ad2ebf329e8259b35f3ee0ef0492485d85c3ff`。本机真实运行根：`outputs/light_source_ranking_v1_20261006/trainer_runs/source_conditional_dev_c8acd05_20261006_v1/`（忽略，不上传源数据）。进程已实际完成 `context_only` 三个 seeds 的各 15 epochs，保存 checkpoint 与逐行预测；此观察不代表九条件对比已完成或任何模型胜出。

运行中以该目录 `progress.jsonl` 为实际进度 authority，而非本页的即时计数；本页不逐 epoch 更新。启动调用为 `fit_source.py --out outputs/light_source_ranking_v1_20261006/trainer_runs/source_conditional_dev_c8acd05_20261006_v1`，当前执行 session `9472` / 初始 PID `83166` 仅用于本机会话接续，不能替代产物证据。进程消失时先核验原目录是否有完整 report/provenance 或失败，不再启动同名/替代运行冒充原 run。InputReview snapshot 是运行前历史状态，不冒充当前 owner 状态。

## 当前下一动作与不变边界

唯一下一动作：监测已启动的固定 cohort / seeds DEVELOPMENT 运行，完成后独立读回 checkpoints、逐行预测及两项主比较；不重复启动、不调参、不逐通道增跑、不追逐正结果。`train.py` 默认入口仍拒绝真实拟合；只有独立 `fit_source.py` 核对记录后允许上述窄执行。该任务不把未证明的 source 信息偷称 actor-visible；完整演员观察契约仍需另行验证。方法来源与迁移边界见[近邻总表 §12 的 Cho 方法核验](../../01_文献/全量近邻精读总表_2026-10-06.md)及 README 的 Deep Sets 方法段。

本轮真实拟合已启动，尚未完成全套对比和独立产物验收；没有超参数搜索、Runtime/Demo/reference 内容修改或旧拟合结果重算。结果最多回答本协议的 DEVELOPMENT 条件排名问题；完整演员观察权限、动作 settlement、`A^O`、独立正式 test、具名心理 `S`、闭环 policy 和新颖性仍未由它证明。整个科研改造目标未完成。
