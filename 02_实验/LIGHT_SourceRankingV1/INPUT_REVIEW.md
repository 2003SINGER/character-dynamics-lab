# SourceRankingV1 实现验收与下一动作

日期：2026-10-06。状态：**DEVELOPMENT_TRAINED / PARENT_ARTIFACT_AUDIT_PASS / READY_FOR_INDEPENDENT_REVIEW**；不是 `CLOSED`。冻结投影仍为 `training_authorized=false`；单独的 `SOURCE_CONDITIONAL_DEVELOPMENT` 执行记录已准入并完成本次固定拟合。这不升级 actor-visible / Runtime policy / formal test / 心理有效性。

本页唯一维护投影/训练器实现验收、真实 DEVELOPMENT 结果与当前下一动作。[README](README.md)冻结任务、通道和拟训练规格，保留冻结时的未准入状态，不随实现进度改写；[LIGHT 来源审计](../../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)拥有 source/observation 的未准入结论。投影、合成合同和真实来源条件排名结果是不同层次的证据，均不等于演员可见观察契约或 Paper-0 通过。

## 修订与执行证据

主代理发现并要求修正两处会破坏比较的问题：初稿 `context_only` 去掉 persona，混淆历史增益；初版 feature entry 接受 upstream schema 而不是 projected schema。最终对照静态条件相同（只有命名消融例外）；[project_inputs.py](project_inputs.py)的唯一模型入口 `features(projected_row)`读明确允许字段，不读标签、provenance、admission。核心 partner command 污染或私有 extra feature key 会拒绝，不依赖“调用者不会传错”。

- [9 个合成测试](test_project_inputs.py)与 `py_compile` 通过。覆盖真实 projected schema、metadata 毒访问、gold mutation noninterference、core/diagnostic 隔离与空 turn 保留、正控、非法 schema/role/type/ref/split、支持集重数和内部空格保持、重复 source key、固定 hash、existing/overlap/symlink/outside-root 路径拒绝。
- 真实 CLI 成功生成全量输出；再次调用同一默认路径返回 **1 / refusing existing output**，产物 hash 不变。该预期拒绝不是一个新的成功生成。
- 主代理独立逐行构造预期投影，不调用 projector；全量比对输出字段、history views、provenance、split 与源行。两种 view × 有/无 context 的 feature entry 均做 metadata 毒访问检查，合法 prior dialogue 改动为正控。重新计算 manifest 的全部 split/episode/actor/group/depth/role-channel/eligibility 计数及 cohort/source-key digest；全部相符。
- 全部 13,463 行保留。train / validation / excluded bucket9 = **9,530 / 2,717 / 1,216**；episode 各 **3,490 / 986 / 468**，不跨 split。唯一支持标签各 **9,488 / 2,707 / 1,211**，歧义各 **42 / 10 / 5**，缺席与坏支持均 0。这里只是监督 eligibility 计数；没有训练或评分 bucket9，也没有删掉歧义记录。
- 在 **9,397** 个 target prefixes 中存在 prior partner raw command：core 全部置 null，diagnostic 原样保持。group 总数仍 **116,961**，不是 unique events。保留结构/role 仍可能带来源信息，不声称合法 `H^obs` 或完全去除未验证信息。

## 本机可复核产物

路径：`outputs/light_source_ranking_v1_20261006/contract_v1/`。manifest 和协议/code/test 的原字节 snapshots 已纳入[公开审阅清单](../PUBLIC_REVIEW_INDEX_2026-10-07.md)；projected JSONL 属于数据集输入，仍仅本地保存。不改旧 source、旧 fits 或 cohort。

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

产物：`outputs/light_source_ranking_v1_20261006/trainer_synthetic_parent_v1/`；独立核验脚本 `outputs/light_source_ranking_v1_20261006/parent_trainer_audit_v1.py`。可公开的合成结果/代码快照现已按原路径跟踪，详见[公开审阅清单](../PUBLIC_REVIEW_INDEX_2026-10-07.md)。

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

实际执行记录为 `outputs/light_source_ranking_v1_20261006/execution_admission_v1/EXECUTION_ADMISSION.json`（现已公开），SHA-256 `391b263d434c053f06738c99771246ed07abbb823398bcb0fe7ce9b1cc01b837`。依据是用户授权的 DEVELOPMENT 目标下的父代理实现审查，不是人类语义准入。其 `training_authorized=true` **仅限来源条件 DEVELOPMENT 排名**；actor_forecast / runtime_policy / formal_test / psychological_validity 全 false。原始 protocol/projected 的 false 原样保留，两者不是同一授权。

| 当前执行 pin | SHA-256 |
|---|---|
| train.py | `0a2afeaf824bf20ae6fa1067818306617d2e3cf752df1c1c91bf9aefe67eb0e3` |
| fit_source.py | `a9170d56d62779a9aeb7d2b52fa99c0ed3477d551b57a99f638044a46f58eee7` |
| test_execution_admission.py | `49cc8c1f372bfe70ad6a580479f1aa7b7959ad6d8d2153bee732663e2d529cf3` |
| 独立 parent_trainer_audit_v2.py | `ee81cb15c1b12907a9851adba30e37deab7316a0f3799eb8733e7c15271245d9` |
| parent_v3 synthetic provenance | `36123c114c4f51457bdcd672ae12957e5a221872d0a6ec99d07f3842677e894a` |

原始 13,463 行、9 条件、seeds 7/19/31、15 epochs 与冻结配置不变；bucket9 不训练、不评分。新输出必须是固定 `outputs/light_source_ranking_v1_20261006/trainer_runs/` 的未存在子目录；记录会连同输入/code 原字节保存，epoch 与阶段 checkpoint 实时 flush/fsync。没有覆盖或 resume 入口；中断产物不得冒充完整报告。

### 实际运行与全量产物验收

已验收实现提交并推送为 `c8acd057c503788b79e7ff635f6c4a85fee8daf7`，远端 main 仍为 `e9ad2ebf329e8259b35f3ee0ef0492485d85c3ff`。本机真实运行根：`outputs/light_source_ranking_v1_20261006/trainer_runs/source_conditional_dev_c8acd05_20261006_v1/`（忽略，不上传源数据）。实际运行退出 **0**，九条件 × 三 seeds 全部完成：24 个学习 checkpoints、360 条学习 epoch records、329,265 条 train/validation predictions。uniform 无参数，也按固定三 seeds 记录；bucket9 没有拟合或评分。

启动调用为 `fit_source.py --out outputs/light_source_ranking_v1_20261006/trainer_runs/source_conditional_dev_c8acd05_20261006_v1`。历史 session `9472` / PID `83166` 已完成，不是待继续运行。`progress.jsonl` 终点为 `analysis_complete`，完整 report/provenance 已存在；不得重启来冒充原 run。InputReview snapshot 是运行前历史状态，不冒充当前 owner 状态。

父代理先用 `parent_partial_fit_audit_v1.py` 独立核对 context 三 seeds 的实际参数更新、45 epochs 和 36,585 predictions。再用独立 `parent_trainer_audit_v3.py` 核对完整文件清单/hash、源字节/准入/cohort、全部 24 个学习模型相对同 seed 初始化确有参数变化、earliest-min checkpoint、329,265 条原位概率/rank/NLL、指标及两项主比较/六个 strata 的 seed-average 与 episode bootstrap，退出 **0 / PASS**。它不调用训练、指标或 bootstrap helpers；仍复用模型类加载网络，不声称第二套完全独立神经网络实现。首次全量 verifier 因遗留合成断言将全部行数当作可评分行数而拒绝；修为独立重建 eligibility 后先通过合成回归，再通过本次全量核验。没有重跑训练或放宽 eligibility。

可评分 train = **9,488 rows / 3,479 episodes**；validation = **2,707 rows / 985 episodes**。这与原始 train 9,530 / 3,490、validation 2,717 / 986 的总行/episode 数是不同分母；歧义标签保留但不训练/评分。产物共 337,839,453 bytes；本次报告阶段 wall time 为 1,176.54 s（约 19.6 min，起点在特征构造后，不是完整预处理耗时），全进程 peak RSS 为 3,332,800,512 bytes（约 3.10 GiB）。不据此声称某模型独立内存或效率优势。

| 全量证据 | SHA-256 |
|---|---|
| report.json | `3777b8a72f76702cde78cb4002e2df88eea32db9b0cd5e30b156989496ecff26` |
| provenance.json | `87431a40e99b34f1be40258ecbb55a385c4138555bf1fcaeb232f4491b5bf583` |
| parent_trainer_audit_v3.py | `ea031b234fc0f7594e9cf28e29251b80965fc72d6f788addbdde3106aa478fdb` |
| parent_partial_fit_audit_v1.py | `ce96c4074171d5c9e2d6c695cf13f241f72996258e26082615e9b8dc39f205ea` |

实现提交 `c8acd05` 的 exact-head CI `37396816807`、运行进度提交 `53cd632` 的 exact-head CI `37397125302` 全部 success；它们验证代码/合成合同/既有回归，**不执行上述本地真实数据拟合或全量验收**。

## 本次 DEVELOPMENT 结果

下表是固定 validation 的三 seeds 均值；NLL 越小越好。top1 / MRR 按冻结的 source-order tie rule；uniform 的 top1 是等分时选原列表第一项，不是随机抽样准确率。此比较共享输入/训练规则，但不是总参数容量匹配。

| 条件 | NLL | top1 | MRR | 可训练参数 |
|---|---:|---:|---:|---:|
| uniform | 2.333493 | 0.114518 | 0.302832 | 0 |
| context_only | 2.288309 | 0.177072 | 0.373151 | 25,153 |
| last2_core | 2.281749 | 0.186061 | 0.382453 | 39,665 |
| pooled_core | 2.261169 | 0.201576 | 0.396584 | 41,281 |
| gru_core | 2.277577 | 0.192095 | 0.389107 | 47,761 |
| gru_no_context | 2.280667 | 0.188154 | 0.384960 | 47,761 |
| gru_no_dialogue | 2.257462 | 0.205393 | 0.398856 | 47,761 |
| gru_no_persona | 2.279979 | 0.191356 | 0.387189 | 47,761 |
| gru_plus_partner_raw_commands（unverified diagnostic） | 2.255712 | 0.208718 | 0.404783 | 47,761 |

两个预先固定主比较的 ΔNLL 均为 **GRU − 对照**；先平均每行三 seeds，再以 episode 做 row-weighted paired cluster bootstrap（2,000 draws，seed 104729）。以下是同一 validation 选 checkpoint 后的 **DEVELOPMENT 描述区间**，不是 untouched test/generalization CI，也没有预定实用收益阈值。

| 主比较 | 平均 ΔNLL | 95% development 区间 | seed 7 / 19 / 31 |
|---|---:|---|---|
| GRU − context | −0.010732 | [−0.020397, −0.001838] | −0.014389 / −0.006798 / −0.011010 |
| GRU − pooled | +0.016407 | [+0.003805, +0.029517] | +0.008954 / +0.022833 / +0.017434 |

本规格下，core history 相对 context 有小的条件排名增益；**GRU 三个 seeds 都差于该 pooled baseline，不支持本 GRU 相对本 pool 的优势或有序状态编码必要性**。不能据此泛化成“顺序无用”：架构、容量、优化与表示均有边界。no-dialogue 的描述分数更好，没有新增事后比较或借此筛样本；它不证明自然对话普遍无用。partner raw command diagnostic 分数较好也不赋予该通道 actor-visible 权限。

固定 validation 深度 strata：1–4 为 305 rows / 234 episodes，5–8 为 909 / 572，≥9 为 1,493 / 798。GRU−context 各为 +0.025349、−0.005124、−0.021517，前两个区间包含 0，≥9 为 [−0.032863, −0.009174]；GRU−pooled 三个 strata 区间均包含 0。完整 train/validation、每 seed、availability 与区间只保存在本次 report/raw predictions；不作长时程人物行为结论或独立 strata 贡献主张。

## 当前下一动作与不变边界

唯一下一动作：独立复核本次固定 DEVELOPMENT 对比及其证据边界，再确定下一项真正可识别的研究问题。保留 pooled 作为本任务的已学习对照，不为挽救 GRU 假设重调系数/编码器或扩大拟合。`train.py` 默认入口仍拒绝真实拟合；单独准入只覆盖本冻结协议。完整演员观察契约、心理 S 与 Runtime policy 仍需各自的数据/监督/验证，不由这次来源排名替代。方法来源与迁移边界见[近邻总表 §12 的 Cho 方法核验](../../01_文献/全量近邻精读总表_2026-10-06.md)及 README 的 Deep Sets 方法段。

本轮真实拟合与父代理全量产物验收完成；没有超参数搜索、Runtime/Demo/reference 内容修改或旧拟合结果重算。结果最多回答本协议的 DEVELOPMENT 条件排名问题；完整演员观察权限、动作 settlement、`A^O`、独立正式 test、具名心理 `S`、闭环 policy 和新颖性仍未由它证明。整个科研改造目标未完成。
