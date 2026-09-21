# Demo Living V1

`COUPLING_SPEC.md` 是本版本唯一机制设计入口。当前实现属于 Demo/application engineering，不是研究证据或心理学验证。

实现已将主要状态从无条件线性 drift / coefficient 组合迁移到显式 zone、smooth response、跨状态 interaction 和 contextual action effects：

- hunger / bathroom 各自只有一个 continuous accumulation owner；
- pressure motivation 与 anxiety facilitation/impairment 分离，overload 只由高压与高焦虑/疲劳交互产生；
- Rest/Sleep 提供暂态恢复出口；screen strain 与 purchase urge 由 exposure/cue 驱动；
- action completion impulses 读取当前状态区间，不再一律使用固定心理增量。

`character_dynamics_living_dynamics_v1_coupling_smoke` 覆盖核心非单调关系、低/高区 response、overload interaction、无条件 satisfaction drift 防回归和 purchase urge cooldown。冻结前审计见 [V1 implementation audit](V1_IMPLEMENTATION_AUDIT.md)，第一轮可解释校准见 [calibration log](CALIBRATION_LOG.md)。原始同 seed 128×48h V1 诊断保留在 `batch_48h_v1/`；新的 [calibrated batch](batch_48h_v1_calibrated/) 不覆盖它。`../living_dynamics_v0/batch_48h_v0/` 也保留为不可覆盖的历史 baseline；所有结果均明确标注为 Demo-only。

当前状态见 [baseline-freeze status](BASELINE_FREEZE_STATUS.md)：授权的 [mechanism repair audit](MECHANISM_REPAIR_AUDIT.md) 已完成同 seed 128×48h 产物，当前为 `READY_FOR_INDEPENDENT_REVIEW`，而非 CLOSED。本次没有接入 Laya。
