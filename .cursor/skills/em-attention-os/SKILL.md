---
name: em-attention-os
description: Generates and reviews an Engineering Manager's five-area attention budget. Use for "Attention brief", "EM attention budget", "attention review", or when deciding whether delivery, people, support, technical direction, and team future receive intentional focus.
---

# EM Attention Operating System

Use the local, deterministic `attention_os` module. Do not infer employee
performance or make autonomous people decisions.

## Daily brief

1. Gather today's calendar into a temporary JSON array with `title` and
   `duration_minutes`. Add `category` only to correct ambiguous titles.
2. Run:

```bash
python3 -m attention_os daily \
  --calendar-json /path/to/calendar.json \
  --context-dir /path/to/chief-of-staff \
  --output ~/.em-attention-os/daily/$(date +%F).md
```

3. Read the generated brief.
4. Ask the EM whether the recommended letter block fits what the team needs.
5. Help protect the block, but do not modify the calendar without approval.

## End-of-day capture

Ask for rough actual points across all five areas, energy from 1–5, one win,
and one adjustment. Execute:

```bash
python3 -m attention_os capture \
  --actual delivery=25,people=25,support=15,technical_direction=20,team_future=15 \
  --energy 3 --win "..." --adjustment "..."
```

Rough allocations are acceptable; the engine normalizes them to 100.

## Weekly review

After at least four captures:

```bash
python3 -m attention_os review --days 5
```

Discuss:

- Was the dominant area intentional?
- Which area stayed below 10 points?
- Did protected letter blocks change a decision, coaching conversation, or
  technical outcome?
- Which envelope task should be delegated or automated next?

## Guardrails

- Keep journals and generated reports private.
- Cite the source behind classifications when presenting them.
- Treat targets as reflection prompts, never performance scores.
- Never compare individual engineers using attention data.
- Prefer one useful adjustment over a long recommendation list.

See `docs/em-attention-os.md` for setup and pilot criteria.
