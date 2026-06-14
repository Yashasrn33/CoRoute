# Prompt spec — generate plan options

The synthesis prompt behind `POST /plans/{id}/options`. See the endpoint contract in
[../../CLAUDE.md](../../CLAUDE.md) and the privacy rules in [../privacy.md](../privacy.md).

**Hard rule:** inputs are already **anonymized** before they reach the model. The prompt
receives a group-level constraint summary and history — **never** per-user rows, never
names. Do not undo this by passing raw prefs.

Use **structured output via tool use** so the result validates against the schema below —
do not parse free text. Cache by a hash of the assembled input (same inputs ⇒ same options;
keeps cost flat and demos deterministic).

---

## Inputs (assembled server-side by the privileged reader)

```jsonc
{
  "plan": {
    "type": "watch_party",          // dinner | watch_party | trip | activity | ...
    "title": "World Cup final",
    "scheduled_for": "2026-06-21T19:00:00Z",
    "location_hint": "downtown",     // optional organizer note
    "party_size": 4                  // count of yes + maybe attendees
  },
  "constraints": {                   // AGGREGATED, no names, no per-person mapping
    "diet": ["vegetarian-friendly", "1 vegan"],
    "budget_per_person_max": 35,
    "vibe_dislikes": ["loud bars", "long waits"],
    "transportation": ["reachable without a car"],
    "hard_nos": ["no smoking sections"],
    "accessibility": ["step-free entry"]
  },
  "recent_outcomes": [               // last 5, newest first — for anti-repeat / memory
    { "summary": "Watched at The Anchor Sports Bar", "happened_at": "2026-05-17" },
    { "summary": "Dinner at Otto's", "happened_at": "2026-05-03" }
  ]
}
```

---

## System prompt (stable; cache this part)

```
You are CoRoute's planning engine. You generate concrete, real-world options for a group
outing that satisfy ALL of the group's constraints at once.

Rules:
- Honor every hard_no and accessibility need as a strict filter. An option that violates
  any hard constraint is invalid — do not include it.
- Treat budget_per_person_max, diet, vibe_dislikes, and transportation as requirements to
  satisfy, not preferences to trade off, unless satisfying all simultaneously is
  impossible — in which case say so explicitly in the option's reasoning.
- AVOID anything similar to recent_outcomes (same venue, or same category/vibe if it would
  feel repetitive). Variety is a feature: the group's complaint is "we always end up at the
  same places."
- Return 3 to 5 options, concrete and specific (a named place or a clearly-scoped plan),
  ordered best-first.
- For each option, explain how it satisfies each constraint group. NEVER attribute a
  constraint to a person — you do not know who has which constraint, and must not guess.
- Keep it realistic for the party_size, scheduled_for, and location_hint.
```

---

## Output schema (tool: `propose_options`)

```jsonc
{
  "options": [
    {
      "title": "string",                  // e.g. "Mesa Verde — back patio"
      "location": "string",               // address or area
      "description": "string",            // 1-2 sentences, what the outing is
      "rank": 1,                          // 1 = best
      "ai_reasoning": {
        "satisfies": {                    // per constraint-group, how it fits — NO names
          "diet": "Full vegetarian menu; 3 vegan mains.",
          "budget": "Mains $14-22, under the $35/person cap.",
          "vibe": "Patio seating, quiet; no bar-volume music.",
          "transportation": "On the M line, 4-min walk; no car needed.",
          "accessibility": "Step-free patio entrance."
        },
        "avoids_repeat": "Different venue and vibe from The Anchor (last month).",
        "tradeoffs": "string | null"      // honest note if any constraint is tight
      }
    }
    // ... 3-5 total
  ]
}
```

Persist each entry as an `options` row with its `ai_reasoning` jsonb. `ai_reasoning` is
surfaced in the UI so the group can see *why* each option fits — this is the visible payoff
of the private-constraints feature.

---

## Eval checklist (used by the `option-prompt-tuning` skill)

Run against the World Cup demo fixture and confirm:
- [ ] 3–5 options returned, each concrete and specific.
- [ ] No option violates any `hard_nos` or accessibility need.
- [ ] Every option's reasoning visibly addresses each constraint group present.
- [ ] No option repeats or closely echoes anything in `recent_outcomes`.
- [ ] No reasoning text attributes a constraint to a named person.
- [ ] Output validates against the `propose_options` schema (structured output).
