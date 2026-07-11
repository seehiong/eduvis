# EduVis: Core Engines and Algorithms Reference

This document provides documentation on the mathematical formulas, algorithms, and logical structures underlying the core engines of EduVis: **Spaced Repetition (SM-2)**, **Study Plan Generator**, **Adaptive Remediation**, and the **Assessment Blueprint Engine**.

---

## 1. Spaced Repetition (SM-2 Algorithm)

The spaced repetition scheduler resides in `spaced_repetition.py`. It implements a stateless variant of the SuperMemo-2 (SM-2) algorithm to update retention intervals and review schedules for elements based on student feedback scores.

### Formula and Step Updates:
For each review event, the student supplies a quality score $q$ from $0$ (complete blackout) to $5$ (perfect response). The database tracks ease factor ($EF$), repetition count ($n$), and interval ($I$ in days):

1.  **Ease Factor ($EF$) Update**:
    $$EF_{new} = EF_{old} + (0.1 - (5 - q) \times (0.08 + (5 - q) \times 0.02))$$
    *   The ease factor is bounded: $EF \ge 1.30$.
2.  **Repetitions ($n$) and Interval ($I$) Update**:
    *   If response is incorrect ($q < 3$):
        *   Repetition count is reset to $n = 0$.
        *   Interval is set to $I = 1$ day.
    *   If response is correct ($q \ge 3$):
        *   If $n = 0$ (first review): $I = 1$ day.
        *   If $n = 1$ (second review): $I = 6$ days.
        *   If $n > 1$: $I_{new} = I_{old} \times EF_{old}$.
        *   Increment repetition count: $n_{new} = n_{old} + 1$.

---

## 2. Study Plan Generator & Revision Engine

The revision scheduler in `revision_engine.py` generates study plans by prioritizing topics for revision based on knowledge retention gap and exam importance.

### Concept Priority Score:
Each concept node $c$ in the curriculum is ranked using a priority score $P$:
$$P(c) = E(c) \times (1.0 - M(c))$$
where:
*   $E(c)$ is the curriculum-defined `exam_weight` representing the topic's relative value on tests.
*   $M(c)$ is the learner's dynamic `mastery_score` (between $0.0$ and $1.0$).

### Selection Algorithm:
1.  **Filter & Rank**: Filters out fully mastered concepts ($M(c) \ge 0.80$) and ranks remaining concepts in descending order of priority score $P(c)$.
2.  **Allocate Time Budget**: Allocates estimated study times dynamically (e.g. 25–35 minutes per concept based on complexity) until the total hours budget is filled.
3.  **Order Topics**:
    *   `lesson` mode: Orders prerequisite concepts first so the learner builds foundations sequentially.
    *   `exam_prep` mode: Sorts strictly by priority score $P(c)$ to focus on high-yield exam gaps first.
    *   `crash_course` mode: Ranks by graph centrality to focus on concepts that unlock the maximum number of downstream dependents.

---

## 3. Adaptive Remediation Engine

The adaptive tutoring engine in `remediation_engine.py` resolves concept deficiencies dynamically during lesson playback.

### Tracing Prerequisite Failure Cause:
If a student fails a concept $C$, the remediation engine traces prerequisite failures backwards along the dependency path:
1.  Traverses $C$'s prerequisites recursively.
2.  Finds the deepest parent node in the dependency hierarchy where the learner's mastery is below threshold.
3.  Returns this root concept as the immediate target for corrective study.

### MCQ Misconception Detection & Boost:
When selecting the next practice item:
*   **Misconception Mapping**: MCQs define mapping keys matching incorrect options to specific misconceptions (e.g., `digit_size_magnitude_error`).
*   **Target Selection Boost**: If the telemetry trace shows an active misconception, the engine applies a selection boost to practice items that explicitly list `remediation_for` relationships targeting that misconception, prioritizing targeted remediation over general practice.

---

## 4. Assessment Blueprint & Assembly Engine

The assessment compiler in `blueprint_engine.py` constructs test papers satisfying conceptual and cognitive requirements.

### Blended Concept Weights:
To distribute marks proportionally, the importance of each concept node $c$ is calculated by blending its test representation and its connectivity:
$$\text{Importance}(c) = 0.70 \times E(c) + 0.30 \times C(c)$$
where:
*   $E(c)$ is the `exam_weight`.
*   $C(c)$ is the normalized graph centrality weight representing prerequisite dependency connections.
*   Concept targets are normalized so they sum to $1.0$.

### Greedy Paper Assembler:
Given a blueprint of concept targets and cognitive targets (e.g. 30% conceptual, 50% procedural, 10% application, 10% reasoning), the engine:
1.  Scores a pool of available question elements.
2.  Selecting questions that contribute marks toward outstanding concept and cognitive gaps.
3.  Assembles a validated paper divided cleanly into sections by assessment objective.
