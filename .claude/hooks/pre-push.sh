#!/usr/bin/env bash
# Claude Code PreToolUse hook: run the pipeline up to PyTest before Claude pushes.
# Reads the tool call JSON from stdin. Exit 2 blocks the call and shows stderr to Claude.

# ponytail: regex on the raw JSON, a push hidden in a script or alias slips through
grep -Eq '\bgit( -C [^ ]+)? push\b' || exit 0

out=$(cd "$CLAUDE_PROJECT_DIR" && pypeline run 2>&1) && exit 0

# Claude Code reads exit 2 with empty stdout and "No such file" on stderr as a hook error, not a block.
echo "pypeline failed, push blocked"
echo "Push blocked: 'pypeline run' failed. Fix the failures, then push again." >&2
echo "$out" | tail -n 40 >&2
exit 2
