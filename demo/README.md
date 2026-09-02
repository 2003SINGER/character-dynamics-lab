# 小房间 W→O 演示

这是机制骨架的**可视化实验底座**，不是心理机制、LLM 策略或论文实验的实现。

它先演示一个用户确认的关键接口：场所是 `W → O` 的观察过滤器。角色在某个场所时，该场所的可观察字段作为一个整体进入 `O`；离开后，旧场所视图保留，并随时间变为 `stale` 或 `unknown`。

## 运行

在项目根目录执行：

```powershell
python -m http.server 8000 -d demo
```

随后打开 `http://localhost:8000`。

## 当前明确展示的内容

- W：房间、走廊、对象、位置与动作结算；
- O：按场所维护的局部世界视图，带 `fresh / stale / unknown`；
- S/P：现阶段只显示数据结构与一个明确标注为**占位**的 StateDelta；
- Action：候选、演示排序、选择后由 W 校验和结算；
- provenance：事件、场所观察、StateDelta、动作与世界变化的顺序日志。

`core.js` 的 `semanticStateOperator` 和 `rankActions` 都是可替换接口，不能被误读为已确定的 LLM 或心理学机制。
