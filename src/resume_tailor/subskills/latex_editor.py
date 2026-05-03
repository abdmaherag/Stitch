"""
LaTeX Editor — Step 3 of the resume-tailor pipeline.

edit(selection, company, output_dir) -> Path
  Pure Python — no Claude call.
  Reads template/template.tex.
  Makes targeted replacements in the five editable regions.
  Writes applications/{date}-{company}/Resume.tex.
  Returns the output path.
"""
import re
from pathlib import Path

from resume_tailor import config as _cfg

TEMPLATE = Path(__file__).parents[4] / "template" / "template.tex"

# ---------------------------------------------------------------------------
# Text processing helpers
# ---------------------------------------------------------------------------

def _latex_escape(text: str) -> str:
    """Escape plain-text special chars that appear in master.md bullets.
    Apply BEFORE _bold so the conversion sequences don't get double-escaped.
    """
    replacements = [
        ("°",  r"\textdegree{}"),
        ("→",  r"$\rightarrow$"),
        ("~",  r"\textasciitilde{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("$",  r"\$"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _bold(text: str) -> str:
    """Convert **phrase** markers (from Resume Selector) to \\textbf{phrase}."""
    return re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)


def _process_bullet(bullet: str) -> str:
    return _bold(_latex_escape(bullet))


def _make_items(bullets: list) -> str:
    """Render a list of bullets as indented \\item lines (no begin/end tags).
    Accepts either bare strings (legacy) or {"id", "text"} dicts (current schema)."""
    out = []
    for b in bullets:
        text = b["text"] if isinstance(b, dict) else b
        out.append(f"    \\item {_process_bullet(text)}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Template region replacement helpers
# ---------------------------------------------------------------------------

def _replace_summary(tex: str, summary: str) -> str:
    """Replace the Lorem Ipsum placeholder line after \\section*{Summary}."""
    # The summary block is a single line between \section*{Summary} \n and \n
    # Use the known placeholder as the anchor — template is locked so this is safe.
    old_marker = "% --- Summary --- %% EDIT HERE%%\n\\section*{Summary} \n"
    start = tex.find(old_marker)
    if start == -1:
        # Trailing space may have been stripped by an editor — try without it
        old_marker = "% --- Summary --- %% EDIT HERE%%\n\\section*{Summary}\n"
        start = tex.find(old_marker)
    if start == -1:
        raise ValueError(
            "Summary marker not found in template. "
            "Check that the \\section*{Summary} line in template.tex has not been modified."
        )
    content_start = start + len(old_marker)
    content_end = tex.find("\n", content_start)  # end of the summary line
    return tex[:content_start] + _process_bullet(summary) + tex[content_end:]


def _replace_itemize(tex: str, section_anchor: str, new_items: str) -> str:
    """Replace the content inside the first \\begin{itemize}...\\end{itemize}
    block found AFTER `section_anchor` in `tex`."""
    anchor_pos = tex.find(section_anchor)
    if anchor_pos == -1:
        raise ValueError(f"Section anchor not found in template: {section_anchor!r}")

    begin_tag = r"\begin{itemize}"
    end_tag = r"\end{itemize}"

    begin_pos = tex.find(begin_tag, anchor_pos)
    if begin_pos == -1:
        raise ValueError(f"\\begin{{itemize}} not found after anchor: {section_anchor!r}")

    end_pos = tex.find(end_tag, begin_pos)
    if end_pos == -1:
        raise ValueError(f"\\end{{itemize}} not found after anchor: {section_anchor!r}")

    before = tex[: begin_pos + len(begin_tag)]
    after = tex[end_pos:]
    return before + "\n" + new_items + "\n" + after


def _replace_techstack(tex: str, new_stack: str, github_anchor: str) -> str:
    """Replace the \\techstack{...} line directly below `github_anchor` in the template."""
    anchor_pos = tex.find(github_anchor)
    if anchor_pos == -1:
        raise ValueError(
            f"GitHub greylink anchor not found in template: {github_anchor!r}\n"
            "Check that github_anchor in stitch.yaml matches your template.tex exactly."
        )
    ts_start = tex.find(r"\techstack{", anchor_pos)
    ts_end = tex.find("}", ts_start) + 1  # closing brace
    return tex[:ts_start] + f"\\techstack{{{new_stack}}}" + tex[ts_end:]


def _replace_skills(tex: str, ai_ml: str, concepts_tools: str) -> str:
    """Replace the AI & ML and Concepts & Tools placeholder lines."""
    old_ai_ml      = r"\textbf{AI \& ML:} \\%EDIT HERE% EACH  MUST NOT EXCEED 200 CHARS"
    old_concepts   = r"\textbf{Concepts \& Tools:}%EDIT HERE% EACH  MUST NOT EXCEED 200 CHARS"

    new_ai_ml      = r"\textbf{AI \& ML:} " + ai_ml + r" \\"
    new_concepts   = r"\textbf{Concepts \& Tools:} " + concepts_tools

    if old_ai_ml not in tex:
        raise ValueError("AI & ML skills placeholder not found in template.")
    if old_concepts not in tex:
        raise ValueError("Concepts & Tools skills placeholder not found in template.")

    tex = tex.replace(old_ai_ml, new_ai_ml, 1)
    tex = tex.replace(old_concepts, new_concepts, 1)
    return tex


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def edit(selection: dict, output_dir: Path) -> Path:
    """
    Fill the locked template with tailored content from `selection`.
    Sections and anchors are driven by stitch.yaml — no hardcoded values.

    Args:
        selection:   Output dict from resume_selector.select().
        output_dir:  Destination directory (created if absent).

    Returns:
        Path to the written Resume.tex.
    """
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"template.tex not found at {TEMPLATE}")

    tex = TEMPLATE.read_text(encoding="utf-8")

    # 1. Summary
    tex = _replace_summary(tex, selection["summary"])

    # 2. Sections — driven by stitch.yaml
    for section in _cfg.get_sections():
        key     = section["key"]
        anchor  = section["template_anchor"]
        bullets = selection["bullets"].get(key, [])

        # Optional frozen techstack line (e.g. for a project section)
        if "github_anchor" in section:
            stack = section.get("frozen_techstack", "")
            tex = _replace_techstack(tex, stack, section["github_anchor"])

        tex = _replace_itemize(tex, anchor, _make_items(bullets))

    # 3. Technical Skills
    tex = _replace_skills(
        tex,
        selection["skills"]["ai_ml"],
        selection["skills"]["concepts_tools"],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "Resume.tex"
    out_path.write_text(tex, encoding="utf-8")
    print(f"[latex_editor] wrote -> {out_path}")
    return out_path
