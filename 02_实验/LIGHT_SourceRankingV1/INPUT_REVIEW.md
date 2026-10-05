# SourceRankingV1 输入投影验收

日期：2026-10-06。状态：**INPUT_IMPLEMENTED / PARENT_AUDIT_PASS / READY_FOR_INDEPENDENT_REVIEW**；不是 `CLOSED`。`training_authorized=false`；**TRAINER_NOT_IMPLEMENTED**。

本页只维护投影实现、验收与当前下一动作。[README](README.md)冻结任务、通道和拟训练规格；[LIGHT 来源审计](../../01_文献/精读_LIGHT与本地预测任务准入_2026-10-06.md)拥有 source/observation 的未准入结论。输入投影通过不等于演员可见观察契约、Paper-0 或训练通过。

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

## 当前下一动作与不变边界

唯一下一动作：按冻结规格实现 source-conditional ranking 训练器及合成功能合同，再由主代理独立核对实际 tensors、特征权限、训练/validation 隔离、pool/GRU 公平条件与输出证据；通过前不拟合真实数据。方法来源与迁移边界见[近邻总表 §12 的 Cho 方法核验](../../01_文献/全量近邻精读总表_2026-10-06.md)及 README 的 Deep Sets 方法段。

本轮没有拟合、超参数搜索、Runtime/Demo/reference 修改或旧结果重算。后续结果最多回答本协议的 DEVELOPMENT 条件排名问题；完整演员观察权限、动作 settlement、`A^O`、独立正式 test、具名心理 `S`、闭环 policy 和新颖性仍未由它证明。整个科研改造目标未完成。
