# 1) Rubric v1.1 (drop-in)

Use this wording (short, machine-checkable). It fits your existing fields:

* `dimension ∈ {accuracy, completeness, addition, name_consistency, dialogue_style, flow, other}`
* `severity ∈ {"1","2","3"}`
* `reason` (≤ 30 words)
* `corrected_korean_sentence` (0–2 sentences max; include only if materially different)
* `tags` (choose from: `terminology`, `formality`, `punctuation`, `numbers`, `honorifics`, `style`, `fluency`, `consistency`)

**Severity (impact-based)**

* **1 minor** – Meaning intact. Local grammar/wording/tone issues; publishable after touch-up.
* **2 major** – Partial meaning loss, wrong nuance, or terminology error; needs correction before publish.
* **3 critical** – Core meaning wrong, invented details, or safety-critical error; must block publish.

**Dimension tests (one-liners)**

* **accuracy**: Korean meaning ≠ source meaning (incl. false friends/term misuse).
* **completeness**: Required info missing.
* **addition**: Content invented/not present in source.
* **name\_consistency**: Names/terms inconsistent with prior or glossary.
* **dialogue\_style**: Speech level/formality/honorific misuse.
* **flow**: Unnatural phrasing harming readability without changing meaning.
* **other**: Real issues not above; avoid overuse.

**Conciseness rules**

* Put the **evidence** inside `reason` as micro-quotes only (since we aren’t adding fields):
  `reason` format: `source:"<≤15 chars>" -> target:"<≤15 chars>" + 1-sentence justification`.
* `corrected_korean_sentence`: **1–2 sentences max**. If a tiny fix is enough, write just the corrected clause/sentence—no paraphrase.

# 2) Prompt skeleton (schema-compatible, JSON-only)

Drop this under your *structured\_quick* template:

```
You are a translation validator. Return JSON ONLY matching this shape:
{"cases":[
  {
    "current_korean_sentence": string,
    "problematic_source_sentence": string,
    "reason": string,          // ≤ 30 words; include micro-quotes: source:"..." -> target:"..."
    "dimension": "accuracy|completeness|addition|name_consistency|dialogue_style|flow|other",
    "severity": "1"|"2"|"3",
    "corrected_korean_sentence": string?, // 0–2 sentences max, only if materially different
    "tags": string[]?         // choose only from: terminology, formality, punctuation, numbers, honorifics, style, fluency, consistency
  }
]}
RULES
- Use the rubric below exactly.
- Merge duplicates/overlaps; prefer highest severity.
- If no issues: return {"cases": []}.
- No markdown, no prose, no comments, no trailing text.

RUBRIC
[Insert the Rubric v1.1 text from section 1 verbatim]
```

> **Why this helps:** we keep your schema unchanged but force evidence via tiny quotes **inside `reason`**, and we hard-cap verbosity.

# 3) Handling \~30,000-char segments reliably (no new fields)

**A. Two-pass, windowed validation (deterministic)**

1. **Sentence index & shard (preprocess):**

   * Split source and target into numbered sentences (`S1..Sn`, `T1..Tm`) using a deterministic splitter.
   * Build fixed windows, e.g., 6–8 sentences per side with 2-sentence overlap.
   * Deterministically select windows:

     * **Glossary-first:** include any window containing a glossary hit.
     * **Uniform fill:** add evenly spaced windows until a cap (e.g., 10–15 windows).
2. **Pass 1 (scout):** Ask for **dimensions only** per window (no reasons/corrections). Temperature 0, top-p 0.1.
3. **Pass 2 (judge):** For windows flagged in Pass 1, re-validate the same text with the **full prompt** above to produce final `cases`.

   * This improves recall without blowing context, and produces more stable outputs.

**B. Sentence-number anchoring inside existing fields**

* Prepend each window with a numbered list of sentences:

  ```
  Source (S#):
  [S12] ...
  [S13] ...
  Target (T#):
  [T12] ...
  [T13] ...
  ```
* Instruct: “When writing `reason`, reference sentence numbers (e.g., `S13->T13`) plus micro-quotes.”
  This gives you anchorability **without** adding span fields.

**C. Deterministic sampling for partial docs**

* When `sample_rate < 1`, choose segments by a content hash (e.g., `sha1(segment) % 100`) to avoid drift across runs.

# 4) Consistency & reliability knobs (no schema change)

**Prompt/decoding**

* `temperature=0`, `top_p=0.1–0.2`, `max_tokens` safely above worst-case.
* Add a **stop sequence** after the closing `]}` to prevent spillover.
* Ask for **max N cases** per segment (e.g., `Report up to 5 highest-impact cases`). This reduces variance.

**Self-check micro-loop (cheap)**

* After the model returns JSON, run a tiny **validator prompt** that takes the JSON and answers **one boolean**:
  “Does every case obey the rubric (dimension valid, severity in {1,2,3}, reason ≤30 words, corrected ≤2 sentences, tags subset)?”
* If “no”, re-ask with: “Fix the JSON to satisfy constraints; do not change meanings.”

**Post-processing invariants (deterministic)**

* **Word-count clamp**: truncate `reason` to 30 words server-side if the model exceeds it.
* **Tag normalizer**: map synonyms to your canonical tag set.
* **Dup merge**: if two cases have identical `dimension` and highly similar `current_korean_sentence`, keep the higher severity.
* **Severity floor**: if `dimension ∈ {accuracy, completeness, addition}` and `reason` contains keywords like “wrong meaning / omitted / invented”, auto-raise `severity` to at least `"2"`.

**N-of-K agreement (optional)**

* Run the **judge pass** twice with different nucleus caps (top-p 0.1 and 0.2).
* Keep only cases that appear in both (string-similar `reason` + same `dimension`), **or** require at least one run to label severity ≥"2".
* This improves precision without large token cost.

# 5) Few-shot (schema-compatible, tiny)

Add 2–3 **micro-examples** that obey your current schema and the 1–2 sentence limit. Example:

```json
// EX1 accuracy (polysemy)
{
  "input": {
    "source": "[S5] She sat by the bank and watched the water.",
    "ko": "[T5] 그녀는 은행에 앉아 물을 바라봤다.",
    "glossary": {"Bank":"강둑"}
  },
  "output": {"cases":[{
    "current_korean_sentence":"그녀는 은행에 앉아 물을 바라봤다.",
    "problematic_source_sentence":"She sat by the bank and watched the water.",
    "reason":"S5->T5 source:\"bank\" -> target:\"은행\"; context implies riverside, not financial.",
    "dimension":"accuracy",
    "severity":"2",
    "corrected_korean_sentence":"그녀는 강둑에 앉아 물을 바라봤다.",
    "tags":["terminology"]
  }]}
}
```

```json
// EX2 completeness (omission)
{
  "input": {"source":"[S2] He opened the window and waved to us.","ko":"[T2] 그는 손을 흔들었다."},
  "output": {"cases":[{
    "current_korean_sentence":"그는 손을 흔들었다.",
    "problematic_source_sentence":"He opened the window and waved to us.",
    "reason":"S2->T2 source:\"opened the window\" omitted; action missing.",
    "dimension":"completeness",
    "severity":"2",
    "corrected_korean_sentence":"그는 창문을 열고 우리에게 손을 흔들었다.",
    "tags":["fluency"]
  }]}
}
```

These keep structure tight and reinforce short `reason` + 1-sentence corrections.

# 6) Operational safeguards (quick wins)

* **Keep `extra=forbid`** in Pydantic for production stability; soften to `ignore` only in controlled testing.
* **Log rubric drift**: track `dimension` distribution by week; if `other` > 10%, review examples/rubric.
* **Golden set**: maintain \~30 frozen segments; fail CI if outputs deviate in dimension/severity beyond a small tolerance.
* **Glossary discipline**: pre-highlight matched terms in the prompt (e.g., `[[Term → Expected]]`) so the model reliably tags `terminology`.

---

### TL;DR rollout

1. Paste **Rubric v1.1** and the **prompt skeleton** (no schema change).
2. Switch to **two-pass windowing** for 30k-char segments (scout → judge).
3. Add **2–3 micro-shots** like EX1/EX2.
4. Enforce **reason ≤30 words** and **correction ≤2 sentences** via prompt + post-checks.
5. Turn on **dup-merge + tag normalization + deterministic sampling**.

This keeps your schema untouched, but materially boosts **consistency, anchorability (via quotes + S#/T#), and precision**, especially on long segments.
