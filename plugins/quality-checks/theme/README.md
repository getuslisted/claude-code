# Marrow Theme

A drop-in theme + 8 component blocks. Designed to be the easiest way to update an existing project's theme: change one CSS variable to re-skin, or copy individual blocks without dragging in opinionated globals.

- **No build step.** Two CSS files, one HTML demo. Open `index.html` in a browser.
- **One re-skin lever.** Change `--hue` in `theme.css` to retune the entire palette.
- **OKLCH colors.** Perceptually-uniform palette derived from the brand hue. No hex literals, no pure black or pure white.
- **Scoped blocks.** Every block uses `qc-<name>` class prefixes. Drops into a host site without colliding with existing styles.
- **Accessible by default.** WCAG 2.2 AA contrast on every text/background pair, visible focus indicators, 44×44 touch targets, semantic HTML, `prefers-reduced-motion` respected.
- **Dark mode** via `prefers-color-scheme`. No toggle code needed (add one if you want).

Verified clean against the [quality-checks](../) eight-gate pipeline: zero findings on Gate 1 (security), Gate 3 (UI craft), Gate 5 (perf), Gate 7 (streamlining).

## Files

```
theme/
├── theme.css       Design tokens, reset, global utilities, buttons.
├── blocks.css      Per-block styles (nav, hero, features, testimonial,
│                   pricing, FAQ, CTA, footer).
├── index.html      Live demo page composing all 8 blocks.
└── README.md       This file.
```

## Quick start

### Use the whole demo

Clone or copy the `theme/` folder. Open `index.html` in a browser. That's it. Edit copy and rearrange blocks to match your product.

### Use only some blocks

1. Copy `theme.css` to your project.
2. Copy the block sections you need from `blocks.css` (each block is delimited by a comment header like `/* NAV ... */`).
3. Copy the matching `<section>` from `index.html`.

The blocks are **scoped** via the `qc-<block>` class prefix, so they will not interfere with your existing styles. To re-style, override CSS variables on a parent element, or add a higher-specificity rule.

### Re-skin in one variable

Open `theme.css`. Find:

```css
:root {
  --hue: 30;  /* warm terra */
}
```

Try other values: `250` (cobalt), `145` (sage), `190` (teal), `320` (aubergine), `0` (red), `60` (mustard). The whole palette derives from this one hue; tinted neutrals shift, the accent shifts, dark mode shifts.

If you need a fully bespoke palette, override the individual `--color-*` tokens.

### Use a different font

Both fonts are loaded from Google Fonts. To swap:

1. Update the `<link>` in `index.html` to load your fonts.
2. Update `--font-display` and `--font-body` in `theme.css`.

The type scale uses `rem`, so user-level font-size scaling continues to work.

## What's in the theme

### Design tokens (`theme.css`)

- **Color**: 12 semantic tokens (bg, surface, surface-2, line, line-2, text, text-soft, text-muted, accent, accent-soft, accent-fg, accent-hover) plus success/danger/warning/focus. All OKLCH; all derive from `--hue`.
- **Type**: scale from `--text-xs` (13px) to `--text-4xl` (clamped 40px–67px), perfect-fourth (1.333) ratio.
- **Spacing**: 11-step scale `--space-1` through `--space-11`, base 4px.
- **Radius**: sm / md / lg / xl / pill.
- **Shadow**: 1 / 2 / 3 (subtle, layered, hue-tinted).
- **Motion**: ease-out-quart and ease-out-expo curves; `--duration-1/2/3/4` from 120ms to 560ms. No bounce, no elastic.
- **Layout**: `--container`, `--container-narrow`, `--measure` (65ch), `--gutter`, `--section-pad`.

### Blocks (`blocks.css` + `index.html`)

| Block | What it is | Notes |
|---|---|---|
| `qc-nav` | Sticky top navigation | Solid surface (no glassmorphism default), 44px min-height, mobile-collapses links |
| `qc-hero` | Asymmetric hero | Italic-stressed title, lede, two CTAs, optional aside panel |
| `qc-features` | Mosaic feature section | One lead feature + two supporting; deliberately not a 3-up identical grid |
| `qc-testimonial` | Single feature quote | Display-serif quote, attribution row; no 3-up headshot grid |
| `qc-pricing` | Two-tier pricing | Free + Studio; tiers visually different (not identical cards) |
| `qc-faq` | Native disclosure FAQ | `<details>/<summary>`; no modal-as-first-thought |
| `qc-cta` | Committed-color CTA section | The single drenched moment per page |
| `qc-footer` | Minimal footer | Brand + 3 link columns + small print |

### Global utilities

- `.skip-link` — keyboard skip-to-content link, animates with `transform` (not `top`)
- `.container`, `.container--narrow` — content-width wrappers
- `.visually-hidden` — visually-hidden but screen-reader-readable
- `.btn`, `.btn--primary`, `.btn--secondary`, `.btn--ghost`, `.btn--lg`, `.btn--sm`
- `.eyebrow` — small uppercase label
- `.lede` — opening paragraph treatment

## How the theme avoids common pitfalls

The Marrow theme is the reference implementation that the [quality-checks](../) plugin uses to demonstrate "what good looks like." Specifically:

| Pitfall | What we do instead |
|---|---|
| Pure `#000` / `#fff` everywhere | OKLCH neutrals tinted toward `--hue` (chroma 0.008–0.020) |
| Gradient text (`background-clip: text`) | Single-color emphasis via `<em>` + accent color |
| Glassmorphism as default chrome | Solid sticky nav with hairline divider |
| Hero-metric template (big number + small label, repeated) | Hero aside is a 4-row mock UI; content varies |
| Identical card grid (3 features, same shape) | Mosaic: 1 lead + 2 supporting, with different sizes and treatments |
| Side-stripe borders > 1px | Full borders or backgrounds; 1px hairline only |
| Modal as first thought | `<details>/<summary>` for FAQ |
| Em-dashes in copy | Periods, colons, commas |
| Animating `width` / `top` / `left` | Animating `transform` and `opacity` only |
| `<img>` without dimensions causing CLS | (No images in the demo; if added, set `width`/`height` or `aspect-ratio`) |
| Hard-coded literal colors | Every color references a `--color-*` token |
| Global selector pollution | All block CSS prefixed with `qc-` |
| `tabindex="-1"` on visible interactives | (None in the demo) |
| Removed focus indicators | `:focus-visible` ring on all interactives |
| Touch targets < 44px | `min-height: 44px` on `.btn`, `.qc-faq__summary`, etc. |

## Running the gate scan

If you have the `quality-checks` plugin installed:

```bash
# from the claude-code repo root
node plugins/quality-checks/../impeccable/skill/scripts/quality-gates.mjs \
  --gate=all \
  --scope=plugins/quality-checks/theme/theme.css,plugins/quality-checks/theme/blocks.css,plugins/quality-checks/theme/index.html
```

Expected output:

```json
{
  "gate": "all",
  "filesScanned": 3,
  "findings": [],
  "summary": { "total": 0, "byGate": {}, "bySeverity": {} }
}
```

Zero findings is the verification that the theme passes its own gates.

## Browser support

- Modern Chrome, Firefox, Safari, Edge.
- OKLCH: requires Chrome 111+, Firefox 113+, Safari 15.4+. Fallbacks not provided in this minimal theme; if you need legacy support, run the OKLCH values through a converter at build time and emit hex fallbacks.
- `<details>/<summary>` and CSS custom properties: supported everywhere relevant.
- `clamp()`, `min()`, `:focus-visible`, `prefers-color-scheme`, `prefers-reduced-motion`: supported everywhere relevant.

## License

Apache 2.0. Reuse freely. Attribution appreciated but not required.

## Credits

- Color discipline (OKLCH, tinted neutrals, color strategy) from [impeccable](https://github.com/getuslisted/impeccable).
- Type pairing (Fraunces + Inter) inspired by editorial-typographic conventions.
- Block scoping pattern (`qc-` prefix, no global selectors) follows the streamlining gate from this plugin.
- Reset borrows shape from Andy Bell's "A more modern CSS reset" and Josh Comeau's CSS reset, simplified.
