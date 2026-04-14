# Agent Preferences for savestack

## Project Directory
/home/ojogu/projects/savestack

## Backend Location
/home/ojogu/projects/savestack/backend

---

## Commit Style

### Conventional Format
```
<type>(<scope>): <short description>
```
- Types: feat, fix, refactor, test, docs, chore, style, ci, perf
- Title: Max 72 characters
- Use present tense

### Body (non-trivial changes)
- 2-3 bullet points max
- Explain "Why" and side effects
- One sentence, max 15 words per bullet

### Breaking Changes
- Append `!` to type: `feat!(auth): description`

---

## Commit Message Generation

### Inputs
- Changed files with semantic summaries, signals, raw diff
- Aggregate metadata (files changed, insertions, deletions)
- Heuristic hints (suggested type, scope, breaking change signal, confidence)

### Key Rules
- **Raw Diff is source of truth** — hints are weak signals, treat as suggestions
- If confidence is "low", analyze diff to determine true intent
- Validate hints against diff: if hint says 'feat' but diff shows bug fix, use 'fix'

### Focus
- Identify the "Why" — why were these changes made?
- Summarize intent, not line-by-line description
- Use surrounding code context to understand scope

### Output
- Present tense
- Specific and direct
- Output ONLY the commit message (no explanations)

---

## Dynamic Context Guidance

| Condition | Action |
|-----------|--------|
| >5 files changed | Identify single dominant architectural intent |
| Breaking signal detected | Verify if public APIs/interfaces altered |
| Confidence "low" | Analyze diff logic to determine true intent |
| Suggested type "test" | If only tests affected, use 'test' type |
| Suggested type "refactor" | Confirm no functional changes before using |

---

## Preferred Commands
- lint: ruff check
- test: pytest
- typecheck: mypy
