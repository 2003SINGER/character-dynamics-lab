# E0-1–E0-3 paired fixture 实际运行结果

运行日期：2026-09-05  
代码 revision：`576b28b`（本次 stdout 的实际 run commit）
命令：`character_dynamics_reference.exe --e0`  
构建：MinGW 16.1.0 / Debug / CMake（ASCII subst source path）  
固定：world seed `42`、procrastinating personality、初始 `S` 相同；`action_sampling=none`

## 汇总

| fixture | 干预 | support low / high | max_abs_delta_p | commitment low / high | 判定 |
|---|---|---|---:|---|---|
| E0-1 hidden wallet | wallet 20 vs 120，wallet hidden | O/X/S/support 全部相同 | 0.000000 | none / none | PASS：hidden-W non-interference（完整链路硬断言） |
| E0-2 visible wallet | wallet 20 vs 120，wallet visible | 12 / 13（`ShopOnPhone` 仅 high） | 0.085815 | none / none | PASS：visible-O channel connected |
| E0-3 completion visibility | 同一完成结算，completion visible vs hidden | 10 / 13（学习动作仅 hidden） | 0.131328 | none / active | PASS：`task_completed` X 标签、ΔS 方向与 policy 分叉均有硬断言 |

## E0-1 hidden wallet 逐动作概率

| action | p_low | p_high | delta |
|---|---:|---:|---:|
| use_phone | 0.138442 | 0.138442 | 0.000000 |
| shop_on_phone | 0.085815 | 0.085815 | 0.000000 |
| use_computer | 0.116080 | 0.116080 | 0.000000 |
| study_at_computer | 0.100573 | 0.100573 | 0.000000 |
| study_focused | 0.103952 | 0.103952 | 0.000000 |
| study_halfhearted | 0.110347 | 0.110347 | 0.000000 |
| rest_at_bed | 0.091161 | 0.091161 | 0.000000 |
| sleep_at_bed | 0.000000 | 0.000000 | 0.000000 |
| go_to_bathroom | 0.084666 | 0.084666 | 0.000000 |
| get_meal | 0.091987 | 0.091987 | 0.000000 |
| turn_light_on | 0.000000 | 0.000000 | 0.000000 |
| turn_light_off | 0.000000 | 0.000000 | 0.000000 |
| turn_off_alarm | 0.000000 | 0.000000 | 0.000000 |
| open_curtain | 0.000000 | 0.000000 | 0.000000 |
| close_curtain | 0.000000 | 0.000000 | 0.000000 |
| idle | 0.076976 | 0.076976 | 0.000000 |

## 原始 stdout

完整原文见 [2026-09-05_E0-1-3_stdout.txt](2026-09-05_E0-1-3_stdout.txt)。本轮 stdout 新增 `hidden_wallet_same_X/S/support`、`completion_X_assertion` 与 `completion_state_assertion`。

这些是当前确定性规则 fixture 的控制链结果，不证明 `S` 的现实预测价值，也不构成 held-out 行为实验。
