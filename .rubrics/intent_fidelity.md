---
dimension: intent_fidelity
version: 1
levels: [full, partial, divergent, unassessable]
rule:
  divergent:    { severity: blocking, disposition: advisory-planner }
  partial:      { severity: blocking, disposition: advisory-implementer }
  unassessable: { severity: nit,      disposition: annotated }
  full:         { severity: none,     disposition: none }
---

# Intent Fidelity

Judge only the task text, its acceptance criteria and the diff. You have no
access to the implementer's notes and must not ask for them.

Before you read the diff, write down the behaviour each acceptance criterion of
the task requires. Then read the diff and pick exactly one level.

## full

Every acceptance criterion of the task is addressed in the diff.
Evidence: name each criterion and the code and test that meet it.

## partial

The core behaviour is there, but at least one named criterion is open.
Evidence: quote the open criterion and say what is missing.

## divergent

The change solves a different problem than the task describes.
Evidence: quote the task and the code that does something else.

## unassessable

The task names no criterion that can be checked against the diff.
Evidence: quote the task text that is too vague to check.

## Output

```json
{"dimension": "intent_fidelity", "version": 1, "level": "...", "evidence": "..."}
```
