# EM Attention Operating System

The Attention OS makes an Engineering Manager's attention allocation visible
without automating managerial judgment.

It uses Anton Zaides' five-area attention budget:

1. Delivery
2. People
3. Support
4. Technical direction
5. Team future

The daily brief converts calendar and Chief-of-Staff context into 100 planned
attention points, compares them with an adaptive target, and recommends one
60–90 minute "letter block": coaching, judgment, strategy, or technical
synthesis that should not be replaced by status administration.

## Privacy model

- Analysis is deterministic and local; it does not call an LLM.
- Inputs and generated reports remain local.
- The default journal is `~/.em-attention-os/journal.jsonl`.
- Do not commit real calendars, reports, or journals.
- The tool supports reflection. It must not be used for employee scoring,
  performance ratings, or automated people decisions.

## Quick start

The module has no third-party dependencies and requires Python 3.11+.

```bash
git clone https://github.com/sebflorent/agents-council.git
cd agents-council

python3 -m attention_os daily \
  --calendar-json examples/attention-os/calendar.example.json
```

To combine the brief with an existing Chief-of-Staff workspace:

```bash
python3 -m attention_os daily \
  --context-dir /path/to/chief-of-staff \
  --calendar-json /path/to/todays-calendar.json \
  --output ~/.em-attention-os/daily/$(date +%F).md \
  --json-output ~/.em-attention-os/daily/$(date +%F).json
```

The context directory may contain:

- `weekly-focus.md`, with the table used by the existing EM Chief-of-Staff skill
- `open-loops.md`, with ID, Description, Due, Added, and Status columns

Calendar JSON is intentionally portable:

```json
[
  {
    "title": "1:1 with Alice",
    "duration_minutes": 30
  },
  {
    "title": "Architecture quality review",
    "duration_minutes": 60,
    "category": "technical_direction"
  }
]
```

The optional category override is one of:
`delivery`, `people`, `support`, `technical_direction`, `team_future`.

## Five-day pilot

### Morning (3 minutes)

Generate the brief and protect the recommended letter block:

```bash
python3 -m attention_os daily \
  --context-dir /path/to/chief-of-staff \
  --calendar-json /path/to/todays-calendar.json \
  --output ~/.em-attention-os/daily/$(date +%F).md
```

On macOS, install a private weekday brief at 07:15:

```bash
./scripts/install-em-attention-macos.sh /path/to/chief-of-staff
```

The installer creates a user LaunchAgent. Reports and logs stay under
`~/.em-attention-os/`. Remove the pilot with:

```bash
launchctl bootout "gui/$(id -u)/com.agents-council.em-attention"
rm ~/Library/LaunchAgents/com.agents-council.em-attention.plist
```

### End of day (2 minutes)

Estimate actual allocation. Values are normalized to 100, so rough numbers are
good enough:

```bash
python3 -m attention_os capture \
  --actual delivery=35,people=25,support=20,technical_direction=10,team_future=10 \
  --energy 3 \
  --win "Protected the difficult feedback conversation" \
  --adjustment "Delegate the staff status collection"
```

### Day five (10 minutes)

```bash
python3 -m attention_os review \
  --days 5 \
  --output ~/.em-attention-os/review-week-1.md
```

Continue the pilot if:

- at least four of five daily captures are completed;
- at least two letter blocks were protected;
- the brief changed one real decision during the week;
- daily use stays below five minutes.

Stop or redesign if:

- classification corrections exceed 20%;
- the output creates guilt rather than clarity;
- sensitive data is copied into shared outputs;
- it becomes another status-reporting obligation.

## Custom targets

The default target is 25/25/15/20/15. Active open loops and weekly priorities
adapt it slightly. Override it when the team's context requires a deliberate
shift:

```bash
python3 -m attention_os daily \
  --target delivery=20,people=30,support=10,technical_direction=20,team_future=20
```

Targets are guidance, not a performance score. The useful question is:
"Is the current allocation intentional for what the team needs now?"

## Test

```bash
python3 -m unittest discover -s tests -v
python3 -m attention_os daily \
  --calendar-json examples/attention-os/calendar.example.json
```

## Integration path

The initial version is intentionally standalone. It can later be connected to:

- the EM Chief-of-Staff daily briefing;
- Calendar via a read-only MCP connector or API exporter;
- the Manager Command Center dashboard;
- a weekday Cursor Automation;
- a Friday reflection prompt.

Keep connectors at the boundary. The scoring engine should remain deterministic,
testable, and independent from any one company's tools.
