---
name: option-prompt-tuning
description: Iterate and evaluate CoRoute's plan option-generation prompt. Use when changing the Claude synthesis prompt, the output schema, or debugging options that ignore constraints or repeat past outings. Runs the prompt against the demo fixture and checks every constraint is respected and recent outcomes are avoided.
---

# Option-prompt tuning

Iterate the prompt behind `POST /plans/{id}/options` and prove the output is good before
shipping. Source of truth for the prompt + schema: `docs/prompts/generate-options.md`.

## When to use
- Editing the synthesis system prompt or the `propose_options` output schema.
- Options come back that violate a hard constraint, ignore budget/diet, or repeat a recent
  venue.
- Tuning model choice or caching for the synthesis call.

## Before you start
- Read `docs/prompts/generate-options.md` (prompt + I/O contract + eval checklist) and the
  privacy rules in `docs/privacy.md` (inputs are pre-anonymized — never pass raw prefs).
- Consult the `claude-api` skill for current model IDs, tool-use (structured output), and
  prompt-caching details. Do not rely on memorized model info.

## Steps
1. **Load / build the demo fixture.** Use the anonymized input from the World Cup scenario
   (party of 4: vegetarian + 1 vegan, ≤$35/person, no loud bars, no car, step-free), with
   `recent_outcomes` including "The Anchor Sports Bar" so anti-repeat is testable. Reuse the
   fixture produced by the `seed-demo-data` skill if available.
2. **Run the prompt** with structured output (tool `propose_options`). Default model
   `claude-opus-4-8`; you may compare against `claude-sonnet-4-6` for cost.
3. **Score against the eval checklist** in `docs/prompts/generate-options.md`:
   - 3–5 concrete options; no hard-constraint or accessibility violations; each option's
     reasoning addresses every constraint group; nothing repeats `recent_outcomes`; **no
     constraint attributed to a named person**; output validates against the schema.
4. **Iterate** the prompt minimally; re-run; diff results. Prefer tightening instructions
   over adding examples.
5. **Persist** the final prompt back to `docs/prompts/generate-options.md` and note the
   model + caching settings used.

## Guardrails
- Never include member names or per-person constraint mappings in the prompt or in
  `ai_reasoning` — that breaks the privacy promise.
- Keep the system prompt stable enough to cache; vary only the per-plan input.
- Same input must yield same options (caching by input hash) — verify a re-run hits cache.
