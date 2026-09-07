# 复核｜Mechanism Sanity v1.1 修正要求

- 来源：`C:\Users\2003SINGER\.codex\attachments\ea4bc978-2fbf-4300-8c5e-905377dbbf38\pasted-text.txt`
- 来源修改时间：2026-09-07 20:56:50
- 归档副本：[原文](原文.txt)
- SHA-256：`C406A51C883FD848340AA3814EE78620A4F2CB79ED8CD28BEFD083169DA99FDB`

## 有效执行范围

这份复核接受 `514b98f` 的方向，但纠正其证据等级：当前只是 plumbing prototype。最终任务是完成 v1.1 的一刀修正，不启动 v1.2、Experiment B、formal test、新数据采集或新 Theory-S 字段。

## 五类必须修正的问题

1. 做真实的小型 Scene/Object/Action affordance ontology，接入 possessions、facts、description/type，并保留 provenance/rule id；缺事实就不生成，不能把 A* 塞回候选。
2. 对 `fatigue`、`engagement`、`tension` 做逐字段干预，预先写方向，报告 family mass、rank/top-action change、TV 和 PASS/FAIL/NOT_TESTABLE；联合翻转只作 stress test。
3. 增加 P/S 正交 sanity：P 改变稳定偏好，S 改变当前表达；两者都不能改 `A^O`。
4. 将 Theory-S 改称 candidate mechanism / engineering hypothesis；把 literature-constrained form、project-chosen fields、hand-set parameters 和未验证主张分开。
5. 将 LIGHT 结论降级为“当前 projection/字段/ontology 尚不足以支持 persistent-S identification；最终适用性未决”，并把 `ΔO→X→U→S` trajectory sanity 留到 v1.2/Gate 1。
