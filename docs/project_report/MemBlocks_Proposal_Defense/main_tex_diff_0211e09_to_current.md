# `main.tex` Change Report

Baseline commit: `0211e09eb7f030ff8b2c42f2e1505bb91e391ca8`  
Baseline commit date: `Thu Mar 19 19:50:04 2026 +0545`  
Baseline commit message: `proposal and recommended format added`

Compared file:
- `docs/project_report/MemBlocks_Proposal_Defense/main.tex`

Diff summary:
- `1 file changed, 176 insertions(+), 30 deletions(-)`

---

## Quick Navigation

| ID | Area | Type | Jump |
|---|---|---|---|
| C01 | Abstract memory model | Modified | [Go](#c01) |
| C02 | Abstract architecture stance | Modified | [Go](#c02) |
| C03 | Objective #2 section definition | Modified | [Go](#c03) |
| C04 | Methodology framing | Modified | [Go](#c04) |
| C05 | Feasibility (technology stack framing) | Modified | [Go](#c05) |
| C06 | Feasibility (status and scope completion) | Modified | [Go](#c06) |
| C07 | Functional requirement: sectioned structure | Modified | [Go](#c07) |
| C08 | Functional requirement: storage label | Modified | [Go](#c08) |
| C09 | System architecture opening | Modified | [Go](#c09) |
| C10 | Container section composition | Modified | [Go](#c10) |
| C11 | Retrieval layer section references | Modified | [Go](#c11) |
| C12 | Async orchestrator ownership | Modified | [Go](#c12) |
| C13 | Section count statement | Modified | [Go](#c13) |
| C14 | Resources subsection treatment | Replaced with scope note | [Go](#c14) |
| C15 | Section title rename | Modified | [Go](#c15) |
| C16 | Semantic section intro paragraph | Modified | [Go](#c16) |
| C17 | Semantic workflow heading | Modified | [Go](#c17) |
| C18 | Candidate filtering wording | Modified | [Go](#c18) |
| C19 | Product naming consistency | Modified | [Go](#c19) |
| C20 | Prompt-engineering section naming | Modified | [Go](#c20) |
| C21 | Prompt P_s3 memory reference | Modified | [Go](#c21) |
| C22 | Retrieval strategy naming | Modified | [Go](#c22) |
| C23 | Retrieval subsection rename | Modified | [Go](#c23) |
| C24 | Resources retrieval paragraph | Removed | [Go](#c24) |
| C25 | Context assembly wording | Modified | [Go](#c25) |
| C26 | Figure caption branding | Modified | [Go](#c26) |
| C27 | New section: Results | Added | [Go](#c27) |
| C28 | New section: Discussion | Added | [Go](#c28) |
| C29 | New section: Testing/Evaluation/Validation | Added | [Go](#c29) |
| C30 | Conclusion section expansion | Added/Expanded | [Go](#c30) |
| C31 | New section: Limitations and Future Enhancement | Added | [Go](#c31) |
| C32 | New section: Appendix and artifacts | Added | [Go](#c32) |
| C33 | EOF newline normalization | Modified | [Go](#c33) |

---

## Granular Change Log

| ID | Baseline (0211e09) | Current | Impact | Current line |
|---|---|---|---|---|
| <a id="c01"></a>C01 | Abstract says block includes `event and factual memory, immutable resources, and recursive summaries`. | Abstract now says block includes `semantic memory, and recursive summaries`. | Removes resource section from implemented-core claim; consolidates memory terminology under semantic memory. | ~70 |
| <a id="c02"></a>C02 | Abstract highlights dynamic switching, user control, privacy-preserving collaboration, and concrete stack incl. LangChain. | Abstract now highlights `library-first` implementation with `MemBlocksClient`, optional backend/frontend layers, and MCP as lightweight interface. | Moves report tone from feature promise to implementation architecture and integration surface. | ~72 |
| <a id="c03"></a>C03 | Objective #2 includes `recursive summary, and resources (documents)`. | Objective #2 now includes `semantic memory` and `recursive summary (conversation compression and continuity)`. | Narrows objective to shipped sections and strengthens wording on summary purpose. | ~155 |
| <a id="c04"></a>C04 | Methodology intro framed as comprehensive design/proposal of Memory Blocks system. | Methodology intro reframed as documented implemented system with executed architecture and library-first center. | Shifts chapter from proposed design language to implementation-evidence language. | ~279 |
| <a id="c05"></a>C05 | Feasibility cites `agent orchestration frameworks` and `LangChain`. | Feasibility cites `practical integration tooling`, `MemBlocksClient`, optional MCP integration. | Repositions technology narrative from orchestration framework emphasis to client-library integration emphasis. | ~283 |
| <a id="c06"></a>C06 | Feasibility paragraph is future/proposed oriented (`can be implemented`). | Feasibility paragraph is completion oriented (`remained feasible`, `was evaluated`, `was completed`). | Changes tense from plan to delivered outcome. | ~285 |
| <a id="c07"></a>C07 | Functional requirement row defines sections as core + event/factual + resources + recursive summaries. | Row now defines sections as core + semantic + recursive summary. | Aligns requirements table to current implemented section model. | ~303 |
| <a id="c08"></a>C08 | Requirement row label is `Event & Factual Memory Storage`. | Requirement row label is `Semantic Memory Storage`. | Standardizes terminology across document. | ~307 |
| <a id="c09"></a>C09 | System Architecture opens with 3-layer architecture description (Memory Space / Processing / User Interaction). | System Architecture opens with library-first architecture and `MemBlocksClient` as primary integration surface. | Re-centers architecture around reusable core library and optional interfaces. | ~355 |
| <a id="c10"></a>C10 | Container paragraph lists sections including `Resources` and `Event and Factual Memory`. | Container paragraph lists `Core`, `Semantic`, and `Recursive Summary` as three implemented sections. | Removes resources as active implemented section in architecture narrative. | ~357 |
| <a id="c11"></a>C11 | Retrieval paragraph references core + event/factual + resources + recursive summaries. | Retrieval paragraph references core + semantic + recursive summary. | Keeps retrieval scope consistent with section-model changes. | ~360 |
| <a id="c12"></a>C12 | Async orchestrator described as `The Agent (async)` with event/factual additions and summary evolution. | Async orchestrator described as `MemBlocksClient (async)` with semantic additions and summary updates. | Assigns orchestration responsibility to explicit client component. | ~364 |
| <a id="c13"></a>C13 | Section implementation intro says container has `four specialized sections`. | Intro now says `three implemented sections`. | Explicitly marks implemented subset and avoids over-claiming. | ~389 |
| <a id="c14"></a>C14 | Full `Resources Section` subsection present (immutable docs/transcripts, hybrid retrieval). | Resources subsection removed and replaced by one scope sentence: reserved for future implementation. | Major scope correction from implemented feature narrative to planned/future feature. | ~391 |
| <a id="c15"></a>C15 | Subsection title `Event and Factual Memory Section`. | Subsection title `Semantic Memory Section`. | Terminology consolidation. | ~403 |
| <a id="c16"></a>C16 | Intro distinguishes event vs factual memories explicitly. | Intro simplifies to semantic memory storing events/facts/opinions with metadata. | Reduces conceptual split while retaining metadata model. | ~405 |
| <a id="c17"></a>C17 | Workflow heading: `Memory Addition Workflow For Event and Factual Memory`. | Workflow heading: `Memory Addition Workflow For Semantic Memory`. | Consistent procedure naming. | ~429 |
| <a id="c18"></a>C18 | Candidate filtering step says search in `Event and Factual section`. | Candidate filtering step says search in `Semantic section`. | Terminology and retrieval-target consistency. | ~436 |
| <a id="c19"></a>C19 | Paragraph says `Memory Blocks' integration ...`. | Paragraph says `MemBlocks' integration ...`. | Product naming consistency update. | ~443 |
| <a id="c20"></a>C20 | Prompt engineering intro says `Memory Blocks system`. | Prompt engineering intro says `MemBlocks system`. | Product naming consistency update. | ~465 |
| <a id="c21"></a>C21 | Prompt `P_s3` constraint says do not duplicate from `Core or Event/Factual memory`. | Constraint now says do not duplicate from `Core or Semantic memory`. | Aligns summarization guardrails with renamed section model. | ~477 |
| <a id="c22"></a>C22 | Retrieval strategy intro says `Memory Blocks retrieval strategy`. | Retrieval strategy intro says `MemBlocks retrieval strategy`. | Product naming consistency update. | ~481 |
| <a id="c23"></a>C23 | Subsection label is `Event and Factual Memory Retrieval`. | Subsection label is `Semantic Memory Retrieval`. | Retrieval section naming aligned with rest of paper. | ~489 |
| <a id="c24"></a>C24 | Dedicated `Resources Retrieval` paragraph exists (conditional activation). | Paragraph removed. | Removes non-shipped retrieval path from active methodology text. | between ~489 and ~491 |
| <a id="c25"></a>C25 | Context assembly refers to `Retrieved Event and Factual memories`. | Context assembly refers to `Retrieved semantic memories`. | End-to-end retrieval pipeline naming consistency. | ~496 |
| <a id="c26"></a>C26 | Figure caption: `Memory Blocks System Architecture Overview`. | Figure caption: `MemBlocks System Architecture Overview`. | Branding consistency in figure labels and references. | ~503 |
| <a id="c27"></a>C27 | No `Results` section in baseline at this location. | New `\section{Results}` added with implementation outcomes and interface-level observations. | Adds explicit outcomes narrative to complement methodology. | ~523 |
| <a id="c28"></a>C28 | No `Discussion` section in baseline at this location. | New `\section{Discussion}` added (objectives alignment + architecture significance). | Introduces interpretive analysis layer beyond pure description. | ~533 |
| <a id="c29"></a>C29 | No `Testing/Evaluation/Validation` section in baseline at this location. | New validation section added, references evidence matrix and confidence framing. | Adds traceability/evidence posture to report body. | ~543 |
| <a id="c30"></a>C30 | Conclusion content was shorter/less implementation-evidence heavy before later sections. | Conclusion now expanded with stronger evidence-grounded outcomes and architectural coherence framing. | Improves closure and ties objectives to delivered implementation. | ~553 |
| <a id="c31"></a>C31 | No dedicated `Limitations and Future Enhancement` section in baseline. | New limitations/future-enhancement section added with paired limitation-path statements. | Adds boundary clarity and forward roadmap language. | ~561 |
| <a id="c32"></a>C32 | No appendix block with prompt/model/API extracts and packaging placeholders. | New `Appendix` section added with prompt extracts, data model extracts, API request model extracts, and pending artifact placeholders. | Adds supporting technical artifact snapshots and documentation traceability. | ~578 |
| <a id="c33"></a>C33 | File ended without newline at EOF. | File now ends with newline. | Minor formatting normalization. | EOF |

---

## Change Pattern Summary

| Pattern | Observation |
|---|---|
| Section model simplification | Repeated shift from `event/factual + resources` to `semantic` plus note that resources are future scope. |
| Architecture recentering | Multiple paragraphs now center `MemBlocksClient` and library-first implementation. |
| Proposal-to-implementation tense shift | Methodology and feasibility wording changed from prospective language to delivered/executed language. |
| Evaluation maturity | Entire new sections (`Results`, `Discussion`, `Testing/Evaluation/Validation`, expanded `Conclusion`) added to strengthen evidence narrative. |
| Naming consistency | `Memory Blocks` normalized to `MemBlocks` across technical sections and captions. |
