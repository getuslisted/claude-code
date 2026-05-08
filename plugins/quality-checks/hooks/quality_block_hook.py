#!/usr/bin/env python3
"""Quality block hook for Claude Code.

Intercepts Edit / Write / MultiEdit and blocks (or warns once per session) on:
  - The absolute UI bans from impeccable (gradient text, side stripes, etc.)
  - High-risk security smells from claude-code's security-guidance plugin
  - Hard-coded #000 / #fff / rgb(0,0,0) / rgb(255,255,255)

Design mirrors plugins/security-guidance/hooks/security_reminder_hook.py:
  - Per-session, per-(file, rule) state so warnings don't repeat
  - Exit 2 to block (PreToolUse), exit 0 to allow
  - Disable per-rule via .claude/quality-checks.json: {\"disabledRules\": [...]}
  - Disable entirely: ENABLE_QUALITY_BLOCK=0
"""

import json
import os
import random
import re
import sys
from datetime import datetime

DEBUG_LOG_FILE = "/tmp/quality-checks-log.txt"


def debug_log(message):
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(DEBUG_LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


# Patterns. Each entry has:
#   ruleName (str): stable id used for state tracking and disabling
#   regex (compiled re): pattern to match against the new content
#   action ('block'|'warn'): block exits 2; warn writes to stderr but exits 0
#   reminder (str): the message shown to the user
#   appliesTo (callable taking path -> bool): which files this rule covers
SOURCE_FILE_RE = re.compile(
    r"\.(tsx?|jsx?|vue|svelte|astro|css|scss|sass|less|html|htm|mdx)$",
    re.IGNORECASE,
)

PYTHON_FILE_RE = re.compile(r"\.py$", re.IGNORECASE)
YAML_FILE_RE = re.compile(r"\.(ya?ml)$", re.IGNORECASE)


def is_frontend(path: str) -> bool:
    return bool(SOURCE_FILE_RE.search(path))


def is_python(path: str) -> bool:
    return bool(PYTHON_FILE_RE.search(path))


def is_actions_workflow(path: str) -> bool:
    return ".github/workflows/" in path and bool(YAML_FILE_RE.search(path))


def any_file(_path: str) -> bool:
    return True


QUALITY_PATTERNS = [
    # --- Absolute UI bans (impeccable) ---
    {
        "ruleName": "gradient-text",
        "regex": re.compile(
            r"(?:-webkit-)?background-clip:\s*text", re.IGNORECASE
        ),
        "action": "warn",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check: gradient text detected (`background-clip: text`).\n"
            "This is one of the impeccable absolute bans — it's decorative, never meaningful.\n"
            "Use a single solid color; emphasis via weight or size.\n"
            "Disable this rule: add 'gradient-text' to disabledRules in .claude/quality-checks.json."
        ),
    },
    {
        "ruleName": "side-stripe-border",
        "regex": re.compile(
            r"(?:border-(?:left|right):\s*[2-9]\d*px|\bborder-[lr]-[248](?:\s|$|[\"'`]))",
            re.IGNORECASE,
        ),
        "action": "warn",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check: side-stripe border detected (border-left/right > 1px).\n"
            "This is an impeccable absolute ban when used as a colored accent on cards / list items / callouts / alerts.\n"
            "Rewrite with a full border, a background tint, a leading icon/number, or nothing.\n"
            "If this is a hairline `1px` divider, this warning is a false positive — you can disable the rule."
        ),
    },
    {
        "ruleName": "glassmorphism-default",
        "regex": re.compile(
            r"(?:backdrop-filter:\s*[^;]*blur|\bbackdrop-blur(?:-[a-z0-9]+)?\b)",
            re.IGNORECASE,
        ),
        "action": "warn",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check: glassmorphism (backdrop-blur) detected.\n"
            "Glassmorphism as default chrome is an impeccable absolute ban; rare and purposeful, or nothing.\n"
            "If this is a single intentional surface (one nav, one modal), this warning is a false positive.\n"
            "If you're applying it across multiple surfaces, rewrite with solid surfaces or subtle elevation."
        ),
    },
    {
        "ruleName": "hardcoded-pure-black",
        "regex": re.compile(
            r"(#000(?![0-9a-fA-F])|#000000\b|rgb\(\s*0\s*,\s*0\s*,\s*0\s*\))"
        ),
        "action": "warn",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check: pure black (#000 / #000000 / rgb(0,0,0)) detected.\n"
            "impeccable rule: tint every neutral toward the brand hue (chroma 0.005–0.01).\n"
            "Use the project's `--color-fg` / `--color-text` token, or oklch(20% 0.01 <hue>) etc."
        ),
    },
    {
        "ruleName": "hardcoded-pure-white",
        "regex": re.compile(
            r"(#fff(?![0-9a-fA-F])|#ffffff\b|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))",
            re.IGNORECASE,
        ),
        "action": "warn",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check: pure white (#fff / #ffffff / rgb(255,255,255)) detected.\n"
            "impeccable rule: tint every neutral toward the brand hue.\n"
            "Use the project's `--color-bg` / `--color-surface` token."
        ),
    },
    # --- Security: high-risk smells (these BLOCK; user can disable) ---
    {
        "ruleName": "eval-injection",
        "regex": re.compile(r"\beval\s*\("),
        "action": "block",
        "appliesTo": any_file,
        "reminder": (
            "Quality check (security): eval() usage.\n"
            "Blocked. eval executes arbitrary code and is a major security risk.\n"
            "Use JSON.parse for data, or a real interpreter library if you need expression evaluation.\n"
            "If this is genuinely necessary, disable rule 'eval-injection' in .claude/quality-checks.json."
        ),
    },
    {
        "ruleName": "new-function-injection",
        "regex": re.compile(r"\bnew\s+Function\s*\("),
        "action": "block",
        "appliesTo": any_file,
        "reminder": (
            "Quality check (security): new Function() with dynamic input.\n"
            "Blocked. Equivalent to eval and equally dangerous.\n"
            "Disable rule 'new-function-injection' in .claude/quality-checks.json if intentional."
        ),
    },
    {
        "ruleName": "react-dangerous-html",
        "regex": re.compile(r"dangerouslySetInnerHTML"),
        "action": "warn",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check (security): dangerouslySetInnerHTML.\n"
            "This is XSS-prone if the input isn't sanitized.\n"
            "Pass through DOMPurify (or an equivalent typed sanitizer); validate on the server too.\n"
            "For trusted constants, this warning is a false positive — disable rule 'react-dangerous-html'."
        ),
    },
    {
        "ruleName": "innerHTML-assignment",
        "regex": re.compile(r"\.innerHTML\s*="),
        "action": "warn",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check (security): direct .innerHTML assignment.\n"
            "XSS-prone. Use textContent for plain text, createElement+appendChild for structure, or DOMPurify for HTML."
        ),
    },
    {
        "ruleName": "document-write",
        "regex": re.compile(r"\bdocument\.write\s*\("),
        "action": "block",
        "appliesTo": is_frontend,
        "reminder": (
            "Quality check (security): document.write().\n"
            "Blocked. XSS-prone and bad for performance. Use DOM APIs instead."
        ),
    },
    {
        "ruleName": "child-process-exec",
        "regex": re.compile(
            r"\b(?:child_process\.exec|exec|execSync)\s*\(\s*[`'\"]"
        ),
        "action": "warn",
        "appliesTo": any_file,
        "reminder": (
            "Quality check (security): child_process.exec / execSync with a string command.\n"
            "Command-injection prone. Prefer execFile / execFileSync with an args array, or a known-safe wrapper."
        ),
    },
    {
        "ruleName": "os-system",
        "regex": re.compile(
            r"\b(?:os\.system|os\.popen|subprocess\.[a-zA-Z_]+\([^)]*shell\s*=\s*True)"
        ),
        "action": "warn",
        "appliesTo": is_python,
        "reminder": (
            "Quality check (security): os.system / shell=True.\n"
            "Command-injection prone with any non-static input. Use subprocess.run with a list and shell=False."
        ),
    },
    {
        "ruleName": "pickle-deserialization",
        "regex": re.compile(r"\bpickle\.loads?\s*\("),
        "action": "warn",
        "appliesTo": is_python,
        "reminder": (
            "Quality check (security): pickle.load on bytes.\n"
            "Pickle on untrusted input → arbitrary code execution. Use JSON, MessagePack, or Protobuf."
        ),
    },
    {
        "ruleName": "yaml-unsafe-load",
        "regex": re.compile(r"\byaml\.load\s*\((?!.*Loader\s*=\s*[a-zA-Z_]*Safe)"),
        "action": "warn",
        "appliesTo": is_python,
        "reminder": (
            "Quality check (security): yaml.load without SafeLoader.\n"
            "Use yaml.safe_load() (or yaml.load(..., Loader=SafeLoader))."
        ),
    },
    {
        "ruleName": "github-actions-injection",
        "regex": re.compile(
            r"\$\{\{\s*github\.event\.(?:issue|pull_request|comment|review|review_comment|head_commit)\."
            r"(?:title|body|message|name)",
            re.IGNORECASE,
        ),
        "action": "warn",
        "appliesTo": is_actions_workflow,
        "reminder": (
            "Quality check (security): GitHub Actions interpolation of attacker-controllable input.\n"
            "Inputs like issue/PR/comment titles & bodies can carry shell metacharacters.\n"
            "Pass via env: and quote: env: { TITLE: ${{ github.event.issue.title }} }; run: 'echo \"$TITLE\"'\n"
            "https://github.blog/security/vulnerability-research/how-to-catch-github-actions-workflow-injections-before-attackers-do/"
        ),
    },
]


def get_state_file(session_id):
    return os.path.expanduser(
        f"~/.claude/quality_checks_state_{session_id}.json"
    )


def cleanup_old_state_files():
    try:
        state_dir = os.path.expanduser("~/.claude")
        if not os.path.exists(state_dir):
            return
        current = datetime.now().timestamp()
        cutoff = current - (30 * 24 * 60 * 60)
        for filename in os.listdir(state_dir):
            if filename.startswith("quality_checks_state_") and filename.endswith(
                ".json"
            ):
                fpath = os.path.join(state_dir, filename)
                try:
                    if os.path.getmtime(fpath) < cutoff:
                        os.remove(fpath)
                except OSError:
                    pass
    except Exception:
        pass


def load_state(session_id):
    sf = get_state_file(session_id)
    if os.path.exists(sf):
        try:
            with open(sf, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, IOError):
            return set()
    return set()


def save_state(session_id, shown):
    sf = get_state_file(session_id)
    try:
        os.makedirs(os.path.dirname(sf), exist_ok=True)
        with open(sf, "w") as f:
            json.dump(list(shown), f)
    except IOError as e:
        debug_log(f"Failed to save state: {e}")


def load_disabled_rules(cwd):
    """Read .claude/quality-checks.json from cwd for disabled rules."""
    config_path = os.path.join(cwd, ".claude", "quality-checks.json")
    if not os.path.exists(config_path):
        return set()
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        return set(data.get("disabledRules", []))
    except (json.JSONDecodeError, IOError):
        return set()


def extract_content_from_input(tool_name, tool_input):
    if tool_name == "Write":
        return tool_input.get("content", "")
    if tool_name == "Edit":
        return tool_input.get("new_string", "")
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits", []) or []
        return "\n".join(e.get("new_string", "") for e in edits)
    return ""


def check(file_path, content, disabled):
    """Return list of (rule, action, reminder) hits."""
    if not content:
        return []
    hits = []
    for pat in QUALITY_PATTERNS:
        if pat["ruleName"] in disabled:
            continue
        if not pat["appliesTo"](file_path):
            continue
        if pat["regex"].search(content):
            hits.append((pat["ruleName"], pat["action"], pat["reminder"]))
    return hits


def main():
    if os.environ.get("ENABLE_QUALITY_BLOCK", "1") == "0":
        sys.exit(0)

    if random.random() < 0.1:
        cleanup_old_state_files()

    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        debug_log(f"JSON decode error: {e}")
        sys.exit(0)

    session_id = data.get("session_id", "default")
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {}) or {}

    if tool_name not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        sys.exit(0)

    content = extract_content_from_input(tool_name, tool_input)
    disabled = load_disabled_rules(os.getcwd())
    hits = check(file_path, content, disabled)

    if not hits:
        sys.exit(0)

    shown = load_state(session_id)
    blocking = False
    messages = []
    for rule, action, reminder in hits:
        key = f"{file_path}::{rule}"
        if key in shown:
            continue
        shown.add(key)
        messages.append(reminder)
        if action == "block":
            blocking = True

    save_state(session_id, shown)

    if not messages:
        sys.exit(0)

    print("\n\n---\n\n".join(messages), file=sys.stderr)
    sys.exit(2 if blocking else 0)


if __name__ == "__main__":
    main()
