---
description: Fast hot-pattern scan during development - runs only Phase 1 (security smells) and Phase 3 (absolute UI bans) plus a typecheck. Aim ~30s
argument-hint: "[--scope=branch|staged|file=PATH]"
allowed-tools:
  - Bash(git diff:*)
  - Bash(git status:*)
  - Bash(git ls-files:*)
  - Bash(git rev-parse:*)
  - Bash(rg:*)
  - Bash(grep:*)
  - Bash(find:*)
  - Bash(npx tsc:*)
  - Bash(pnpm tsc:*)
  - Bash(bun tsc:*)
  - Bash(npm exec tsc:*)
  - Read
  - Glob
  - Grep
---

# /quality-quick — Fast hot-pattern scan

For in-progress work, not pre-shipping. ~30 seconds. Three checks only:

## Check 1 — Security smells

```bash
rg -nP --hidden -g'!**/node_modules/**' -g'!**/dist/**' -g'!**/build/**' \
   -e 'eval\(' \
   -e 'new Function\(' \
   -e 'dangerouslySetInnerHTML' \
   -e '\.innerHTML\s*=' \
   -e 'document\.write\(' \
   -e 'child_process\.exec\(' \
   -e 'os\.system\(' \
   -e 'pickle\.loads?\(' \
   -e 'YAML\.load\(' \
   -e 'subprocess\..*shell=True'
```

Report hits. Any hit = block.

## Check 2 — Absolute UI bans

```bash
rg -nP --hidden -g'!**/node_modules/**' -g'!**/dist/**' \
   -e 'background-clip:\s*text' \
   -e '-webkit-background-clip:\s*text' \
   -e 'border-left:\s*[2-9]px' \
   -e 'border-right:\s*[2-9]px' \
   -e 'border-l-[248]\s' \
   -e 'border-r-[248]\s' \
   -e 'backdrop-filter:\s*blur' \
   -e 'backdrop-blur'
```

Manually inspect the hits — these patterns are sometimes legitimate. Flag glassmorphism only if it's used as the default chrome (multiple hits across components), gradient text only if combined with `background:.*gradient`, side stripes only if used as a colored accent (not a 1px hairline border).

Also scan for hard-coded `#000` / `#fff` (use tinted neutrals).

## Check 3 — Typecheck

Run `tsc --noEmit` if `tsconfig.json` exists. Report exit code and first 20 lines of error if non-zero.

## Output

Three-line summary at the end:

```
security: <count> hits
ui-bans:  <count> hits (<count> after manual review)
typecheck: ok (exit 0)
```

Don't run a full audit — that's `/quality-checks`. This command is for tight feedback during a coding session.
