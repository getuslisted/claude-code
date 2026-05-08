# NOTICE

The quality-checks plugin builds on prior art:

- Plugin scaffolding patterns from Anthropic's `claude-code` plugins (`code-review`, `pr-review-toolkit`, `security-guidance`, `frontend-design`).
- The `quality_block_hook.py` design (per-session state file, exit-2 blocking, JSON config) closely follows `plugins/security-guidance/hooks/security_reminder_hook.py` by David Dworken.
- The UI craft criteria — absolute bans, AI-slop test, color strategy, tinted neutrals — derive from the [impeccable](https://github.com/getuslisted/impeccable) skill (Apache 2.0; based on Anthropic's frontend-design skill).
- The verification iron law — "evidence before claims, always" — derives from the [superpowers](https://github.com/getuslisted/superpowers) `verification-before-completion` skill.
- The accessibility / responsive / streamlining checklists draw from the [ui-ux-pro-max](https://github.com/getuslisted/ui-ux-pro-max-skill) skill's UX guideline catalog.

This plugin: Apache 2.0.
