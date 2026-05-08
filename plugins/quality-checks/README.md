# Quality Checks Plugin

The **final line of defense** before shipping. Eight gated phases that catch known and unknown issues across security, correctness, UI/UX craft, accessibility, performance, responsive behavior, streamlining, and final verification.

Designed to compose with three companion skills:

- [impeccable](https://github.com/getuslisted/impeccable) — brand/product UI craft and the absolute design bans
- [ui-ux-pro-max](https://github.com/getuslisted/ui-ux-pro-max-skill) — UX guidelines, palettes, font pairings, chart types
- [superpowers](https://github.com/getuslisted/superpowers) — verification iron law and parallel subagent patterns

## Why this exists

Most code-review tooling catches *known* issues (SQL injection, missing types). Most design-review tooling catches *aesthetic* issues (cluttered hierarchy, weak typography). Neither catches the gap *between*: a beautiful component that's inaccessible, a perfect-looking page that drops frames, a secure backend with an XSS sink in the markdown renderer.

This plugin runs both at once, with a final verification gate that refuses completion claims without evidence.

## Installation

From the parent claude-code repo:

```bash
claude --plugin ./plugins/quality-checks
```

Or add to `.claude/settings.json`:

```json
{
  "plugins": {
    "quality-checks": { "path": "./plugins/quality-checks" }
  }
}
```

## Commands

| Command | Use when |
|---|---|
| `/quality-checks` | Full 8-phase audit before shipping (commit, PR, deploy) |
| `/quality-quick` | Fast hot-pattern scan during development (~30 seconds) |

Both accept:

- `--scope=branch` (default) — audit `git diff main...HEAD`
- `--scope=staged` — audit `git diff --cached`
- `--scope=file=PATH` — audit a single file
- `--strict` — fail on P2 issues, not just P0/P1
- `--phases=2,4,5` — run only specific phases
- `--report=md|json` — output format

## The Eight Phases

Each phase is a **gate**. P0 failures stop the pipeline; P1 failures stop in `--strict` mode. Pipeline never claims success without evidence.

### Phase 0 — Preflight
Detect repo type, framework, package manager, design tokens, test/lint/build/typecheck commands. Confirm verification commands exist before claiming any "passes."

### Phase 1 — Security
Pattern scan for the 9 high-risk smells (XSS sinks, eval/exec, deserialization, command injection, GitHub Actions injection). Secret scan. Dependency vulnerability check.

### Phase 2 — Code correctness
Build, typecheck, lint, test must all exit 0. No silent failures (try/except: pass, swallowed promises, ignored returns). Imports resolve.

### Phase 3 — UI craft
The absolute bans (gradient text, side stripes, glassmorphism default, hero-metric template, identical card grids, modal-as-first-thought). AI-slop test. Color strategy declared.

### Phase 4 — Accessibility (WCAG AA)
Contrast 4.5:1 (3:1 large), accessible names on interactive elements, keyboard reachable, visible focus, semantic HTML, touch targets ≥44×44, `prefers-reduced-motion` respected.

### Phase 5 — Performance
No layout-property animation, bounded blur/filter, lazy images with fixed aspect ratios (no CLS), bundle size budget, no layout thrash, memoization where it matters.

### Phase 6 — Responsive display
All breakpoints (≥320, ≥768, ≥1024, ≥1440), no horizontal scroll, body ≥16px on mobile, all interactive states present, theme switching unbroken.

### Phase 7 — Streamlining (drop-in friendliness)
No hard-coded colors (tokens only), no nested cards, scoped CSS, relative units (rem/em), parent-aware sizing, optional `data-*` API for host overrides. **Goal:** the block drops into another website with minimal edits.

### Phase 8 — Verification
Fresh re-run of build/lint/typecheck/test. Print exit codes alongside the claim ("build=0, lint=0, typecheck=0, tests=42/42"). No completion language without evidence.

## How phases compose with the companion skills

| Phase | Plugin agent | Companion skill |
|---|---|---|
| 1 | `security-auditor` | claude-code `security-guidance` plugin (hook patterns) |
| 2 | `code-correctness-auditor` | superpowers `verification-before-completion` |
| 3 | `ui-craft-auditor` | impeccable shared design laws + absolute bans |
| 4 | `accessibility-auditor` | impeccable `audit.md`, ui-ux-pro-max 99 UX guidelines |
| 5 | `performance-auditor` | impeccable `optimize.md` |
| 6 | `responsive-display-auditor` | impeccable `adapt.md`, `responsive-design.md` |
| 7 | `streamlining-auditor` | impeccable `extract.md`, ui-ux-pro-max tokens |
| 8 | (orchestrator) | superpowers `verification-before-completion` |

If a companion skill is installed, the relevant agent loads its reference; otherwise it falls back to the criteria embedded in this plugin.

## Hook

The `PreToolUse` hook (`hooks/quality_block_hook.py`) intercepts `Edit|Write|MultiEdit` and **blocks** writes containing:

- The 6 absolute UI bans (gradient text, side stripes, glassmorphism default, hero-metric template, identical card grids, `<Modal>` as the only chosen affordance)
- High-risk security patterns (eval, `dangerouslySetInnerHTML` with user input, `innerHTML =`, `os.system`, `child_process.exec`, `pickle`, `new Function`)
- Hard-coded `#000` / `#fff` / `rgb(0,0,0)` / `rgb(255,255,255)` (use tinted neutrals)

Warnings are session-scoped; once shown, they don't repeat for the same file+rule.

Disable per-pattern in `.claude/quality-checks.json`:

```json
{ "disabledRules": ["side-stripe-border"] }
```

Disable entirely:

```bash
ENABLE_QUALITY_BLOCK=0
```

## License

Apache 2.0. Builds on Anthropic's `code-review`, `pr-review-toolkit`, and `security-guidance` plugin patterns; the design-craft criteria derive from the impeccable skill (also Apache 2.0). See NOTICE for attribution.
