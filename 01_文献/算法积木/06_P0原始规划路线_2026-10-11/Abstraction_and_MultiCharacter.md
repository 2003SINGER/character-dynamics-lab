# P0 mechanism check: Fisher & Ware abstraction and the 2023 system pointer

Checked 2026-10-11. Scope: full AIIDE 2024 paper, version/hash, publicly discoverable implementation pointer, and the identity of the repository's “2023 complete multi-character system” reference. This is a bounded mechanism check, not a new gap or novelty claim.

## Source and version

- **Paper evidence** — Mira Fisher and Stephen Ware, “A Model for Automating the Abstraction of Planning Problems in a Narrative Context,” *Proceedings of the Twentieth AAAI Conference on Artificial Intelligence and Interactive Digital Entertainment (AIIDE 2024)*, 20(1), 35–45, DOI [10.1609/aiide.v20i1.31864](https://doi.org/10.1609/aiide.v20i1.31864). The publisher record gives publication date 2024-11-15. Full paper: [AAAI proceedings PDF](https://ojs.aaai.org/index.php/AIIDE/article/download/31864/34031/35933); author-hosted full paper: [University of Kentucky PDF](https://www.cs.uky.edu/~sgware/reading/papers/fisher2024model.pdf).
- **Local原件** — [`FisherWare2024_AIIDE_Abstraction.pdf`](../../../90_原始材料/_private/2026-10-11_Planner_P0/FisherWare2024_AIIDE_Abstraction.pdf) is an ignored/private local copy saved from the author-hosted URL above; it is not part of the public repository. SHA-256 `8b92bccd11c45bc4c7892887a0fd7137fd429c1dc517ee6276dd35e07ddbcfeb`; 11 PDF pages; metadata title and authors match the paper. The extraction reports a metadata subject string “accepted and presented at AIIDE-2022,” which conflicts with the publisher citation and is treated as stale metadata, not publication year evidence.
- **Coverage attribution** — Luna performed the full-text reading and Figure 3 visual inspection; the present audit card consolidates that coverage. The main agent's current-turn check focused on the mechanism and interface boundaries and is not represented as an independent complete reread. Figure 3 (PDF p. 6 / proceedings p. 40) shows situation graphs for X, Y, and X∪Y, with local/global edges and regions induced by external interactions. The paper has no appendix.
- **Public implementation** — the paper and publisher record expose the article/PDF, but no code/artifact link is given there. Exact-title, author, and “Grid Grandma” repository searches did not surface an attributable public implementation. Thus no public code version/commit can be identified from the sources checked; implementation availability remains unverified, not proven nonexistent. Do not substitute a planner cited as background for this algorithm's implementation.

## Mechanism in executable terms

**Paper evidence.** The input is a classical SAS+-like planning problem Π = ⟨V,O,s₀,s⋆⟩. Operators have pre-, post-, and prevail-conditions. The method first partitions facts into subproblem sets Fᵢ. Operators whose changes stay within one set are local; operators changing facts across sets are global. For each subproblem it generates a situation space while checking only local facts. Edges retain the ignored prevail conditions, and global edges also retain their nonlocal pre/post side effects. This relaxed enumeration can include locally possible situations that are globally unreachable.

For each subproblem, the method groups its situations by the transitions they make available to operators elsewhere in the decomposition network. A situation makes an external operator/transition available only when assuming its facts does not conflict with the situations that operator describes. Goal-satisfying situations enable a special END transition. Situations with the same externally available transition set fall into the same region.

The abstract state variables correspond to subproblems, and each variable's values are those subproblem regions. The low-to-high mapping is explicit:

`α(s) = {(vᵢ, ρ(s ∩ Fᵢ)) for each subproblem i}`

That is, intersect a complete low-level state with each subproblem's facts, look up the resulting situation's region ρ, and assign that region as the high-level value. Partial situations can map to a set of possible abstract facts. Initial and goal states are lifted the same way. For each original operator, abstract operators are generated from the possible abstract pre-, post-, and prevail-situations, keeping only cases whose abstract pre and post differ. Thus operators are aggregated by their abstract reformulation; low-level details that do not alter the region are hidden.

**What the abstraction preserves.** It preserves the external transition affordances relevant to the rest of the network, including required prevail conditions and cross-subproblem side effects. It also preserves the mapped initial/goal situation and an END transition where a subproblem meets the goal. Internal distinctions that do not change those interactions are candidates to merge. Combining mutually observed variables can move dependencies inside a subproblem and reduce exposed observations. In Grid Grandma, X∪Y compresses Tom's row/column to “adjacent to Grandma,” “adjacent to Merchant,” or “elsewhere.”

**What it does not specify.** The paper does not give an abstract-plan refinement search, a low-level execution validator, or a feedback/replanning loop. The constructed operators are induced from original operators through the mapping; the authors state abstract plans can be directly translated to low-level plans and illustrate one matched story (Figure 4). That is not an algorithm for resolving a spurious abstract path or proving every abstract plan refines. The method therefore should not be described as a complete hierarchy with verified refinement. Its edge labels and regional equivalence are the protection against losing externally relevant preconditions, not a general post-search validation procedure.

## Evaluation and limits

**Paper evidence.** The test domain is an authored low-level “Grid Grandma” variant: five characters are present, but Tom is the player/acting planner and NPCs only attack him; they do not have independently planned goals or action policies. The paper compares successive hand-selected fact groupings, not an automated optimizer for selecting the best partition. For the full domain, the raw reachable graph is 2,242,343 states / 9,390,133 edges. The final GG-Coins abstract graph has 40,440 states / 10,504 edges (Table 2). The paper also reports reductions in reachable abstract state-space size as partitions are successively grouped; grouping choice can reduce region count while increasing each subproblem's situation count.

Six selected story plans are compared by length: examples range from 18–71 primitive actions versus 3–18 abstract events; Figure 4 shows one low-level/abstract correspondence. This supports compression and the representability of those selected stories in this domain. It is not a runtime benchmark, a completeness/soundness proof for arbitrary abstract plans, a comparison on external game domains, or a human study. The authors explicitly describe the work as early development and leave broader domains and human perception evaluation for future work.

**Inference from paper.** The “abstraction” output is a new finite planning problem intended for narrative-level search, while the low-level domain supplies its symbols/operators. The empirical results establish state-space and plan-length reduction in one constructed domain, but do not establish that a planner can safely execute every abstract plan in an arbitrary underlying world.

## 2023 system identity: identified; mechanism not audited here

**SOURCE_IDENTIFIED; AUTHOR_PAGE_ABSTRACT_CHECKED; full-text mechanism check pending.** The user identified the intended source as de Lima, Feijó, and Furtado, “Managing the Plot Structure of Character-based Interactive Narratives in Games,” *Entertainment Computing* 47 (2023), article 100590, DOI [10.1016/j.entcom.2023.100590](https://doi.org/10.1016/j.entcom.2023.100590), with the author page at [edirlei.com](https://edirlei.com/component/content/article/entertainment-computing-journal-2023-managing-the-plot-structure-of-character-based-interactive-narratives-in-games?catid=8). The title/metadata and author-page abstract were checked by the main agent, which describes multi-agent planning, narrative-structure-based drama management, and a graphical authoring tool with evaluation. The DOI full text was not available in that check. Detailed planner allocation, POPF, feedback/control, code, and evaluation procedures remain unverified; the abstract is not treated as full-method evidence.

## Project boundary

This check only identifies a reusable abstraction primitive: group low-level facts, derive per-subproblem reachable situations and external interaction signatures, then lift states/operators over equivalence regions. It does not establish a new research gap, novelty, or a complete cross-layer mechanism. No reproduction was run. The bounded next action is to try this original mechanism on the user's common executable game instance; do not invent a separate refinement layer before testing the paper's actual input/output contract.

## Sources

- [AAAI publisher record](https://ojs.aaai.org/index.php/AIIDE/article/view/31864)
- [AAAI full-text PDF](https://ojs.aaai.org/index.php/AIIDE/article/download/31864/34031/35933)
- [Author-hosted full-text PDF](https://www.cs.uky.edu/~sgware/reading/papers/fisher2024model.pdf)
- Local related-work index: [`01_文献/README.md`](../../README.md), [`全量近邻精读总表_2026-10-06.md`](../../全量近邻精读总表_2026-10-06.md), and [`05_游戏世界规划近邻审计_2026-10-11/Dramamancer_FormalDomain.md`](../05_游戏世界规划近邻审计_2026-10-11/Dramamancer_FormalDomain.md).
