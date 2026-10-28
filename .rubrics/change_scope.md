---
dimension: change_scope
version: 1
levels: [contained, incidental, expansive]
rule:
  expansive:  { severity: blocking,   disposition: annotated }
  incidental: { severity: should-fix, disposition: advisory-implementer }
  contained:  { severity: none,       disposition: none }
---

# Change Scope

Judge whether every change in the diff belongs to the task. Compare each changed
hunk with the task text. Changes the task asks for, including refactors it
names, belong to it.

## contained

Every change traces back to a requirement of the task.
Evidence: none needed beyond naming the files checked.

## incidental

The diff contains changes the task does not ask for, but they do not change
behaviour: drive-by refactors, renames, formatting noise, edits to unrelated
docs or backlog files.
Evidence: list each such hunk as `file:line` with a short quote.

## expansive

The diff changes behaviour outside the task: a public CLI option or function
signature, a shared module the task does not name, configuration, dependencies.
Evidence: list each such hunk as `file:line` with a short quote.

## Output

```json
{"dimension": "change_scope", "version": 1, "level": "...", "evidence": "..."}
```
