# Author Constraint Diagnostic v0｜原四原子驱动原版，作者时间义务通过

**DEVELOPMENT / READY_FOR_INDEPENDENT_REVIEW；本轮停止，未 CLOSED。**基准 `webgpt-sync@416df310fda608a24bdb2f32e95cd1914276ac8b`。10月14日23:47（北京时间）读取新任务，唯一原版运行在10月15日00:01开始（原账本UTC `20261014T160155Z`）。未再次调用Luna或任何LLM。

本轮把旧原样四原子Goal直接送入冻结UCS；搜索自行产生建桥/过桥，随后唯一原版episode满足明确后的作者语义。**旧LLM_Admission原接纳FAIL仍为FAIL，未覆盖或改判。**这不是新B2准入，不是重新提示模型取得的新回答。

逐项当前证据自审见[completion audit](completion_audit.json)，原版完整命令/字节的可读读回见[native readback](native_readback.txt)；读回不是第二次replay运行。

可读读回只规范化CRLF及行末空白，原始字节仍完整保留在events.jsonl的base64回执中，不将派生文本冒充字节级原件。

## G1–G6证据

| Gate | 结果 | 直接证据及范围 |
|---|---|---|
| G1 原四原子真实进UCS | PASS | [input](execution/input.json)、[search](execution/search.json)记录未经补全的完整Goal与原回答SHA；原生全部15次搜索也使用同一四原子hash，与人工五原子E不同 |
| G2 搜索自主补过程 | PASS | 真实离线UCS一次FOUND，15步；zero-based第13步建桥、第14步依赖bridge过岸；完整操作/前后预测状态见search，非walkthrough或预排执行 |
| G3 原版执行 | PASS | [native结果](execution/native.json)、[原始events](runs/oa-b0-E-clean-75d7229602-20261014T160155Z-f33049/events.jsonl)、[B0 trace](runs/oa-b0-E-clean-75d7229602-20261014T160155Z-f33049/b0_trace.jsonl)。15动作的实际输入与离线路径相同，15次原生反馈reconciliation、0 model_mismatch |
| G4 作者时间语义 | PASS | [独立temporal](execution/temporal.json)：建桥seq16 < 首次西岸seq17；最终look18/inventory19；keys、lamp、lamp_on及完整已执行区间无死亡均通过，不需要bridge成为终态Goal原子 |
| G5 来源/撤销/历史 | PASS（限定机制） | [声明](execution/constraints.json)、[原生计划沿革](execution/native_plan_lifecycle.json)及[12项离线测试](parent_tests_final.log)。AUTHOR/GAME不随计划撤销；已执行witness保留；未执行PLANNER依赖可撤销；非玩家扰动比较或新在线任务管理算法 |
| G6 冻结保留 | PASS | 80个受保护文件[before](execution/protected_before.json)/[after](execution/protected_after.json)字节hash相同；旧输出未变、旧FAIL未改。原版tracked source与binary关闭检查均true；不改E0/C++/Evennia/P5/main或既有RESULTS |

## 输入、搜索与接缝

原回答仍在[旧raw文件](../LLM_Admission_v0/calls/e/response.raw.txt)，所有原字段保留，包括重复hard residual；本轮只在隔离路径提取其有效终态Goal，不改其任何字节。

```text
at(player,WESTBANK), carrying(keys), carrying(lamp), lamp_on
```

没有追加bridge或rod，也没有按GOALS["E"]选择人工目标。四原子hash `0f64a442084f48b277550714a422b88e99f8ab8760d0a54f94bf31b541440d45`，人工五原子E hash `0ec1145d9862ac9329e2890a37a012628605d6beaf864bcf69cf5bc645081105`；实际B0 15条search均前者。控制器接收外部Goal的源分支及原生记录hash共同支持这一接缝；mock契约另验证无bridge补全，mock不算实际搜索。

一次真实离线UCS：**3951扩展、48177 generated、0.384秒、15步**（单次观测，不是效率优势结论）。10000扩展/10秒预算不改。预测轨迹明确初始unbridged，在第14个规划动作 `wave rod` 后bridge成立，下一动作 `over` 消费bridge前提；该前提只是当前路线的计划依赖。用户同时明确“建桥过”是本题作者硬事件，二者指向同一证据，但来源/撤销权不同。

原版episode：**17任务输入（15动作+最终look/inventory），另2条启动n/seed；15次原B0逐输入重搜索，总39404扩展、3.836秒搜索时间**。它们是原控制器在线机制，不是15个另选条件的诊断。未改变seed时机、80输入预算、每次10000/10秒和总120秒；不查看NPC隐藏位置/随机游标或读取旧成功回放来决策。原始计划与实际输入如下，bootstrap和最终审计不混称动作：

```text
enter → take keys → take lamp → out → depre → on lamp → unlock grate
→ enter → debri → take rod → pit → d → forwa → wave rod → over
```

## 实际事件与监测

- seq16 `wave rod` 的原生成功反馈确认晶桥新建立；不是look里已有桥的描述，也不是预测bridge=true。
- seq17 `over` 的完整原生地点反馈确认西岸，严格晚于建桥。
- seq18 fresh look确认最终西岸；seq19 inventory确认keys/lamp（rod也在，但不是新增作者硬要求）。seq8原生亮灯反馈后没有关灯/耗尽反证。
- 初始及seq1–19回执完整、连续，发送/意图字节匹配；完整区间无注册死亡/复活反证，close seal完整。结论仅是这个已执行区间，不是保证未来不死或忽略日志缺口。
- 7项作者义务均PASS；最终bridge在这次实际运行中碰巧仍存在，因此**冻结旧E native verifier也PASS**。旧semantic Admission依然FAIL，两种判定不是同一个gate。

检查器只读原生账本，复用冻结独立verifier的字节/地点/库存/死亡提取工具，不读规划预测、不用最终bridge作作者判据。规则范围是这个固定原版区域与已注册输出标记，不声称一般自然语言语义验证、任意游戏的全事件认证或防篡改密码学。

## 归属、残留与反例

[constraints](execution/constraints.json)分别保留AUTHOR/MUST/AT_END、建桥EVENTUALLY及BEFORE、no-death ALWAYS、带plan_id和撤销条件的PLANNER/PLAN_DEPENDENCY，以及原版fissure crossing的GAME规则来源。来源不等于强度，也不等于时间。

AUTHOR与PLANNER的最终状态/witness见native_plan_lifecycle；[GAME规则当前观察评定](execution/game_rule_evaluated.json)以本次seq17原生合法过桥为依据，作用域仅此consumer，不将永久世界规则误解成“最终必须有桥”的作者目标。

原生trace的14次后续计划替换中，回顾性账本保留35个已执行consumer的依赖witness，撤销291个尚未执行的旧计划依赖；作者7项身份不变，事件seq16/17不删除。**这是从真实trace读出的来源生命周期记录，不是新在线Director或玩家扰动后的能力评估。**PLANNER依赖PASS只说明其消费动作经冻结B0原生反馈核验，不能据此宣称每项抽象前提都是独立观测的游戏真值。

已绑定但待运行验证：BOUND/PENDING；游戏有机制但缺monitor：BOUND_BUT_UNVERIFIABLE/UNKNOWN；游戏缺能力：UNSUPPORTED_CAPABILITY/UNKNOWN。三者不再在本诊断中一律当“无法实现”。此分类是本题的明确映射，**没有删除原no-death residual或通用放行所有hard residual**。

少量确定性测试覆盖：撤销只影响所属未执行Planner依赖；换路线不能撤销作者建桥；真实过去witness不消失；已死亡即FAIL；未结束无死亡PENDING；缺失/损坏/未seal日志UNKNOWN；先到岸后建桥FAIL；look描述有桥不等于创建事件；缺能力与待验证不同。**桥过岸后消失**用明确标为synthetic的离线回执验证：新时间监测PASS，旧E verifier FAIL。未在真实episode追加消桥动作，不冒称第二条原版实验。

最终离线回归 **48/48（12本轮 + 原36）**；[原始日志](parent_tests_final.log)。[6条已保存合成反例](offline_examples/results.json)及相应synthetic.jsonl可独立读回，原生episode数均0。CI增加的也是离线契约，无真实搜索、游戏下载/运行或模型调用。

实现提交`81d5faa4de314f1337fdb08676f5f870ec58060f`的[exact-head CI 38599507367](https://github.com/2003SINGER/character-dynamics-lab/actions/runs/38599507367)为6/7 jobs成功，本轮诊断+B0/P1专项通过；唯一失败为旧E0。限定[job结果](implementation_ci.json)与[失败原文](implementation_ci_failed.log)保存，不修改E0规则/预算/预期以刷绿。后续证据文档提交的CI另以对应HEAD的Actions为准，不把此run冒充新的提交结果。

## 实施中的失败与范围

首次启动在保护文件检查阶段遇到Git默认Unicode路径转义，尚未调用UCS或启动游戏；[原始错误日志](run_once.log)保留。修正为Git `-z`，新增确定性路径测试后才进行上述唯一实际诊断。[唯一实际运行日志](run_once_final.log)与[结果](execution/outcome.json)另存；没有因搜索/游戏失败而重试、换seed或预算刷PASS。

运行后针对“无法判断建桥”的明确要求做独立重读，补齐未注册wave反馈/未知最终地点必须UNKNOWN而非FAIL的保守检查。[当次运行所用代码副本](source_at_native/monitor.py)在改动前保留（复制时点在运行后，不伪称预运行签名）；原temporal.json不改。[新检查器只重读同一账本](post_review_temporal.json)仍PASS，没有第二次搜索或原版运行。

所有原回执/请求/输出/失败历史和冻结代码不变。仅新增本实验局部检查与必要CI/入口指针；原native B0配置沿用了 `external_validated_candidate` 标签，[attempt上下文](execution/native_attempt_claim.json)明确它描述接口来源，不意味着旧semantic Admission通过。上游程序/资源/二进制不公开，许可证与归属沿用[原NOTICE](../OpenAdventure_Native_v0/THIRD_PARTY_NOTICE.md)。新对话完整私有归档，原附件已移入可恢复废纸篓。

## 能推出什么、不能推出什么

**本例旧四原子目标确实可经冻结因果搜索和原版执行满足本轮明确的作者时间语义。**因此，旧拒绝不能可靠证明“缺最终bridge就不能满足建桥要求”；在这个明确单例上，阻断主要来自静态目标精确匹配及残留/待验证分类的接纳设计，而非已观察到的搜索或执行缺陷。

不回改旧FAIL，也不把此次诊断放行说成原协议B2成功。模型此前把生存义务重复列在residual中的格式/契约问题仍存在；此单例跑通不证明一般语义绑定正确、Luna优势、新时序算法、完整Character Dynamics、任意世界在线规划或玩家活人感。继承旧Luna-in-Codex的环境混杂限制。

作者事件义务在本轮是由人按明确任务固定、由监测器另行检验，**没有编译进UCS或参与在线路线选择**。成功依赖当前有限域过岸动作本身必须有桥；在有其他通路的游戏中，仅四原子终态不能保证作者建桥事件。来源撤销机制测试与回顾性记录也不能冒充已完成的通用在线作者义务修复。

本轮停止在READY_FOR_INDEPENDENT_REVIEW。下一步只建议先独立审阅本次证据与作者/计划义务分离是否成立；不自动启动新模型比较、原生状态规划、第二游戏或通用平台。
