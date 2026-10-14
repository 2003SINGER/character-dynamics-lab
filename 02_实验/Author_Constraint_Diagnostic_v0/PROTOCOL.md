# Author Constraint Diagnostic v0｜冻结诊断协议

2026-10-14（北京时间23:47开始）；基准 `416df310fda608a24bdb2f32e95cd1914276ac8b`。原始Luna请求、输出、旧FAIL及整套LLM_Admission/B0证据不改。本轮零模型调用，不开发新Planner/Director/AuthorBundle/Judge。

## 固定语义与预算

作者要求：最终在WESTBANK、持keys和lamp且lamp_on；原生bridge_created发生在首次实际抵达WESTBANK之前；整个已执行区间不能死亡。建桥是作者硬事件，同时可有当前计划的因果依赖，两种来源分别保存；不要求最终bridge持续存在。

- 离线诊断仅一次，直接读取旧原样输出，原四原子Goal无增删进入冻结UCS，10000扩展/10秒。FOUND才允许原生运行；预算耗尽不叫不可达。
- 最多一个新原版episode，冻结P1/B0 external_goal接口、seed20261014（startup后）、80任务输入、每次搜索10000扩展/10秒、搜索总120秒。原B0每输入会重求解，搜索调用数另记，不偷改成只执行离线预排路径，也不算新增诊断探针。
- native命令/原始字节、位置/库存/灯及建桥反馈分别核验，预测状态不进入监测器。旧E verifier完整结果保留；新诊断与原接纳FAIL分账，不宣称B2 Admission通过。
- 监测PASS/FAIL/UNKNOWN/PENDING；初始及每条输入回执完整、序号连续、最终fresh look→inventory、关闭seal才能以无死亡证据证明本执行区间ALWAYS。已确定的死亡可立即FAIL；未结束无死亡PENDING；缺日志UNKNOWN。
- 只做少量离线来源/时间反例。synthetic过桥后桥消失可新语义PASS而旧E verifier FAIL；它不是第二条真实游戏运行。
- 最小记录来源AUTHOR/PLANNER/GAME，强度MUST/PLAN_DEPENDENCY/SOFT，时间AT_END/EVENTUALLY/ALWAYS/BEFORE，证据/状态/plan ID/撤销条件。撤销只影响所属未执行PLANNER依赖，不能撤销作者要求、游戏规则或已提交历史。
- 本诊断明确将原no-death监测义务与重复residual映射到BOUND/PENDING；映射留证据，原文本不删除，不把所有hard residual通用放行。缺能力/缺monitor仍UNKNOWN且分类不同。

G1实际原四原子进UCS；G2搜索自主产生建桥/过桥及依赖；G3一条原版执行与预测比对；G4作者事件/顺序/终态/ALWAYS原生证据；G5来源/撤销/历史反例；G6所有冻结文件/旧FAIL/原生游戏不变。无论成功失败保存结果，完成后READY_FOR_INDEPENDENT_REVIEW，不自行CLOSED，不自动进入下一实验。
