---
description: Run the 8-phase quality verification pipeline (security, code, UI craft, a11y, perf, responsive, streamlining, verification) - the final gate before shipping
argument-hint: "[--scope=branch|staged|file=PATH] [--strict] [--phases=1,2,3] [--report=md|json]"
allowed-tools:
  - Bash(git diff:*)
  - Bash(git status:*)
  - Bash(git log:*)
  - Bash(git ls-files:*)
  - Bash(git rev-parse:*)
  - Bash(git show:*)
  - Bash(npm:*)
  - Bash(pnpm:*)
  - Bash(bun:*)
  - Bash(yarn:*)
  - Bash(node:*)
  - Bash(npx:*)
  - Bash(pnpm dlx:*)
  - Bash(bunx:*)
  - Bash(rg:*)
  - Bash(grep:*)
  - Bash(find:*)
  - Bash(jq:*)
  - Bash(test:*)
  - Bash(cat:*)
  - Read
  - Glob
  - Grep
---

# /quality-checks — Final Line of Defense

Runs eight gated phases. **Each phase is a hard gate.** P0 failures stop the pipeline. No completion language without evidence.

## Agent contract (applies to every subagent below)

- **Evidence over assertions.** Every claim must cite a file path, line number, or command output. Never say "should" / "probably" / "looks correct."
- **Confidence threshold ≥ 80.** Flag only what you can defend with a quote from the diff or a command output. False positives erode trust.
- **No completion claims** until verification (Phase 8) re-runs the relevant commands.
- All tools are functional. Don't probe; don't run exploratory `--help` calls.

## Routing

Parse `$ARGUMENTS` for flags. Defaults:
- `--scope=branch` (the diff between current branch and the merge base with `main` or `master`, whichever exists)
- `--strict` not set (P0 + P1 fail; P2/P3 are reported but don't block)
- All phases enabled
- `--report=md`

If `--phases=` is provided, run only those (still in order). Phases 0 and 8 always run.

## Phase 0 — Preflight (gate)

Launch a Haiku subagent to detect:

1. **Repo identity**: framework (Next.js/Vite/Astro/SvelteKit/Remix/Expo/plain), language (TS/JS/Python/Go), package manager (npm/pnpm/bun/yarn).
2. **Verification commands** (must exist; record exact invocation):
   - Build: `package.json` `scripts.build` or framework default
   - Typecheck: `tsc --noEmit` if `tsconfig.json`
   - Lint: ESLint/Biome/Ruff/golangci-lint as applicable
   - Test: `scripts.test` or framework default
3. **Design tokens**: search for `tailwind.config.*`, `:root { --` in CSS, `tokens.*`, `design-tokens/*`, or a `DESIGN.md` (impeccable convention).
4. **Companion skills installed**: probe for `npx impeccable --version`, `npx uipro-cli --version`, and superpowers presence (`.claude/skills/verification-before-completion`). Note absence — don't fail.
5. **Scope resolution**: resolve `--scope` to a concrete file list. If empty, stop with status `no-changes`.

**Gate**: if no verification commands exist for the framework, warn loudly and continue — Phase 8 will say `verification=skipped:no-commands` rather than fabricate a pass.

Report preflight as a 5-line block, then continue.

## Phase 1 — Security (gate)

Launch the `security-auditor` agent (Opus). Pass it the resolved scope. It returns issues with confidence scores. P0 = exploitable today, P1 = exploitable under realistic conditions.

In parallel, run this fast pattern scan via Bash and merge results:

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

For any GitHub Actions YAML in the diff, also scan for unsafe `${{ github.event.* }}` interpolation in `run:` blocks (per github.blog injection guide).

**Gate**: any P0 → stop, write report, exit. Any P1 in `--strict` → stop. Otherwise continue.

## Phase 2 — Code correctness (gate)

Launch the `code-correctness-auditor` agent (Opus). It must:

1. Run typecheck (record exit code).
2. Run lint (record exit code, count of errors).
3. Run tests (record exit code, pass/fail counts).
4. Build (record exit code).
5. Search the diff for **silent failures**: bare `except:`, `except Exception: pass`, swallowed `Promise.catch(() => {})`, ignored returns from fallible APIs.
6. Verify all imports resolve (no unresolved references).

If the project lacks a command for any check, the agent reports `<check>=skipped:no-command` rather than fabricating a pass.

**Gate**: any non-zero exit code in build/typecheck/test → stop unless `--phases` explicitly excluded this phase. Lint failures in `--strict` → stop.

## Phase 3 — UI craft (gate, frontend-only)

If no frontend files in scope (no `.tsx`, `.jsx`, `.vue`, `.svelte`, `.astro`, `.html`, `.css`, `.scss`), skip with `phase-3=skipped:no-frontend`.

Launch the `ui-craft-auditor` agent (Opus). It checks:

- The six **absolute bans** from impeccable (gradient text, side stripes, glassmorphism default, hero-metric template, identical card grids, modal-as-first-thought)
- Tinted neutrals (no `#000`/`#fff`/`rgb(0,0,0)`/`rgb(255,255,255)` in committed CSS)
- Color strategy declared (Restrained / Committed / Full / Drenched)
- AI-slop test (first-order and second-order category-reflex check from impeccable)
- Em-dashes in copy strings

If impeccable is installed, also call `npx impeccable audit --json` on the changed files and merge findings.

## Phase 4 — Accessibility (WCAG AA, gate)

Launch the `accessibility-auditor` agent (Opus). It checks:

- Contrast ratios (parse Tailwind/CSS color usage; flag pairs below 4.5:1 for body text or 3:1 for large text and non-text)
- Accessible names on interactive elements (`button`, `a`, `input`, `[role]`)
- Keyboard reachability (no `tabindex="-1"` on visibly interactive elements; no removed focus indicators without replacement)
- Semantic HTML (heading order, no `div` masquerading as a button)
- Touch targets ≥ 44×44 CSS pixels
- `prefers-reduced-motion` respected on any animation in the diff
- Form inputs labeled, error states programmatically associated

If `axe-core` is installed and a dev server can be started safely, run a real axe scan; otherwise rely on static analysis.

**Gate**: WCAG A failures → P0 (stop). WCAG AA failures → P1.

## Phase 5 — Performance (gate)

Launch the `performance-auditor` agent (Opus). It checks:

- No CSS animation/transition on layout properties (`width`, `height`, `top`, `left`, `margin`, `padding`); only `transform`/`opacity`/`filter` (and only bounded `filter`).
- No unbounded `backdrop-filter` or `filter: blur()` on full-viewport elements.
- Images have explicit dimensions (or `aspect-ratio`) to prevent CLS.
- Off-screen images have `loading="lazy"` (when below the fold).
- No reads + writes to layout properties inside `for`/`while`/`requestAnimationFrame` callbacks (layout thrash).
- Bundle budget: warn if a new dependency adds >50 KB minified+gzipped to the initial bundle.
- React: components rendered ≥ 100 times per page check have `useMemo`/`React.memo` where appropriate.

## Phase 6 — Responsive display (gate)

Launch the `responsive-display-auditor` agent (Opus). It checks:

- Every page-level component renders without horizontal scroll at 320, 768, 1024, 1440 CSS px.
- Body text is ≥ 16 px on mobile (no `text-xs` on body copy at <768).
- All interactive elements have **all states**: default, hover, focus-visible, active, disabled, loading (where async), error (where validated).
- Theme switching (light/dark) doesn't break: no hard-coded colors that ignore the theme variable.
- `<input>`, `<button>`, `<a>` reach 44×44 with their padding included.
- Container queries (where used) have a fallback for older Safari.

## Phase 7 — Streamlining (drop-in friendliness)

Launch the `streamlining-auditor` agent (Sonnet). It checks each component or block in the diff for:

- **Token discipline**: every color, spacing, radius, font value comes from a token (CSS variable, Tailwind class, or design-token import) — not a literal.
- **No nested cards** (a card inside a card).
- **CSS scoping**: scoped via CSS Modules, `:scope`, `@scope`, `data-*` attribute selector, or namespaced class. No naked global rules introduced by a component.
- **Relative units**: `rem`/`em`/`%`/`ch` for typography and most spacing; `px` only for borders, fine-tuning, and `1px`-precision elements.
- **Parent-aware**: respects parent `font-size`, `color`, `direction` (RTL) where reasonable.
- **Optional override surface**: a component intended as a reusable block exposes a `data-*` or CSS-variable override surface, not just hard-wired props.

This is the phase that makes the block **drop into another website with minimal edits** — the user's stated goal.

## Phase 8 — Final verification (always runs)

This phase **must run fresh**, even if Phase 2 ran earlier. The verification iron law from superpowers `verification-before-completion`:

> Evidence before claims, always. If you haven't run the verification command in this message, you cannot claim it passes.

Re-run, in order, capturing exit codes:

1. Typecheck
2. Lint
3. Build
4. Tests

For each, print one of:
- `<check>=ok (exit 0)`
- `<check>=fail (exit N)` with the first 20 lines of error output
- `<check>=skipped:<reason>`

**Never** print `<check>=ok` without having run it in this invocation.

## Final report

Emit the report in `--report` format. Default Markdown structure:

```
# Quality Checks Report

## Verdict
[BLOCK | PASS-WITH-WARNINGS | PASS]

## Phase summary
| # | Phase | Status | P0 | P1 | P2 | P3 | Notes |
|---|---|---|---|---|---|---|---|
| 0 | Preflight | ok | - | - | - | - | next.js, pnpm |
| 1 | Security  | ok | 0 | 0 | 1 | 0 |  |
| 2 | Code      | ok | 0 | 0 | 0 | 0 | tsc=0 lint=0 test=42/42 build=0 |
| ... |

## Findings (P0 → P3, grouped by phase)
For each: [P?] phase / file:line / category / impact / fix

## Verification evidence (from Phase 8)
- typecheck=ok (exit 0)
- lint=ok (exit 0)
- build=ok (exit 0)
- tests=42/42 (exit 0)
```

## Verdict rules

- **BLOCK** if any P0 found, or if `--strict` and any P1, or if Phase 8 has any non-skipped non-zero exit.
- **PASS-WITH-WARNINGS** if P1/P2 issues exist and not in `--strict`.
- **PASS** only if zero P0/P1 and Phase 8 is all green.

Never output **PASS** without a fresh Phase 8 evidence block.

## What this command never does

- Auto-fix code. (Pair with `/code-review`, impeccable `polish`, or a separate apply step.)
- Post GitHub comments. (Pair with `/code-review --comment` if you want that.)
- Run on files outside `--scope`.
- Claim a check passed when the command was skipped.

Create a TODO list before starting Phase 1 so the user can track progress in real time.
