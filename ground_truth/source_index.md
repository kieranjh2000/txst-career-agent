# Ground Truth Source Index

This directory serves as the **authoritative source of truth** for the NACE Career Competency Discovery Agent. The agent strictly grounds its definitions, observable behavior indicators, and evaluation rules in these verified materials.

---

## Approved Sources Registry

| Source Identifier | Document Name | Author / Organization | Provenance / Canonical Link | Scope of Use in Agent | Trust Justification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SRC-NACE-01** | *NACE Career Readiness Competencies (Updated Definitions & Sample Behaviors)* | National Association of Colleges and Employers (NACE) | [naceweb.org/career-readiness/competencies](https://www.naceweb.org/career-readiness/competencies/career-readiness-defined/) | Grounding definitions, terminology, and behavioral evidence indicators | **National Standard:** NACE is the premier national professional association connecting more than 16,000 college career services professionals and university recruiters. Its 8 competencies were established through extensive empirical nationwide research with major employers. |
| **SRC-TXST-02** | *TXST Career Services Career Readiness Framework* | Texas State University Career Services | [careerservices.txstate.edu](https://www.careerservices.txstate.edu/) | Contextualizing student experiences and university alignment | **Institutional Authority:** Texas State Career Services officially adopts and evaluates students against the 8 NACE Career Readiness Competencies across all academic colleges and departments. |
| **SRC-RULE-03** | *Agent Evaluation & Grounding Rules* | ISAN 5318 Project Specification / Graduate Course Charter | Texas State University MSDAIS Program | Defining behavioral rules: no hallucinated skills, evidence quoting, conflict resolution | **Pedagogical & Governance Alignment:** Formally governs the AI agent's decision logic, guaranteeing academic integrity, avoiding forced skill matches, and prioritizing student clarifications. |

---

## Files in this Directory

1. **[`source_index.md`](file:///c:/Users/kiera/OneDrive/Desktop/ISAN%205318%20Project/ground_truth/source_index.md)**:
   - This registry file. Identifies the provenance, authority, and trust rationale for all project knowledge assets.
2. **[`nace_competencies.json`](file:///c:/Users/kiera/OneDrive/Desktop/ISAN%205318%20Project/ground_truth/nace_competencies.json)**:
   - The canonical machine- and human-readable definitions and observable behavior indicators for all 8 NACE competencies.
3. **[`evaluation_rules.md`](file:///c:/Users/kiera/OneDrive/Desktop/ISAN%205318%20Project/ground_truth/evaluation_rules.md)**:
   - The operational constraints and evaluation guidelines that the agent must strictly enforce during student intake, completeness checking, and competency mapping.

---

## Texas State University Terminology Adaptation

Texas State University Career Services actively adopts the 8 NACE Career Readiness Competencies, tailored to Bobcat students' specific workplace needs:
- **`Advocacy & Compassion` (TXST Adaptation)**: In place of NACE's *Equity & Inclusion*, TXST defines this competency as: *"Demonstrate the awareness, attitude, knowledge, and skills required to compassionately engage people from different backgrounds. The ability to empathize with others, overcome challenges, and diffuse conflict."*
- **Observable Behaviors**: Grounded directly in Texas State Career Services' published indicators: soliciting feedback from multiple perspectives, keeping an open mind, adapting to diverse work environments, ensuring all voices are heard, and advocating professionally for oneself and others.
- **Other 7 Competencies**: Retain standard NACE names (*Career & Self-Development*, *Communication*, *Critical Thinking*, *Leadership*, *Professionalism*, *Teamwork*, *Technology*) with TXST's published behavior indicators.

---

## Why the Agent Can Trust These Files

1. **Traceable Lineage**: Every competency and definition in this folder is derived directly from published NACE research and official Texas State University Career Services guidance ([careerservices.txst.edu](https://www.careerservices.txst.edu/students-alumni/resources-services/competencies.html)), rather than generative LLM training memory.
2. **Deterministic Loading**: The agent loads these files directly into memory on execution. Any adjustments made to these files by human administrators immediately govern model behavior without vector database drift or retrieval hallucination.
3. **Auditability**: Career advisors and instructors can inspect this directory to verify the exact definitions and evaluation rules used to assess student experiences.
