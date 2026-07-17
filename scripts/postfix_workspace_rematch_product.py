from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "main_review/offline_investigation.py"
text = PRODUCT.read_text(encoding="utf-8")

old_replace = '''        for match in re.finditer(r"(?:os\\.)?replace\\s*\\(\\s*([^,\\n]+)\\s*,", body):
            replacements.append((match.start(), match.group(1).strip()))
'''
new_replace = '''        for match in re.finditer(
            r"(?:\\bos\\.replace|(?<![.\\w])replace)\\s*\\(\\s*([^,\\n]+)\\s*,",
            body,
        ):
            replacements.append((match.start(), match.group(1).strip()))
'''
if old_replace not in text:
    raise SystemExit("Generated standalone replace detector was not found")
text = text.replace(old_replace, new_replace, 1)

anchor = '''        for match in re.finditer(
            r"(?m)^\\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*"
            r"[A-Za-z_][A-Za-z0-9_]*\\.__class__\\s*\\(\\s*(?P<source>[^)\\n]+)\\s*\\)",
            body,
        ):
            path_objects[match.group("name")] = match.group("source").strip()
'''
addition = anchor + '''        for match in re.finditer(
            r"(?m)^\\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\\s*=\\s*"
            r"(?P<source>[A-Za-z_][A-Za-z0-9_]*\\.(?:with_suffix|with_name|resolve|absolute)\\s*\\([^\\n]*\\))",
            body,
        ):
            path_objects[match.group("name")] = match.group("source").strip()
'''
if anchor not in text:
    raise SystemExit("Generated Path-object detector was not found")
text = text.replace(anchor, addition, 1)
PRODUCT.write_text(text, encoding="utf-8")

for relative in (
    "scripts/postfix_workspace_rematch_product.py",
    "scripts/fix_workspace_rematch_patch.py",
    "scripts/sitecustomize.py",
):
    (ROOT / relative).unlink(missing_ok=True)
