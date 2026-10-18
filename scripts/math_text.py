#!/usr/bin/env python3
"""One math representation path for the whole Paper Reader (Issue #48).

The Reader used to emit mathematics three different ways: display equations as
`\\[ ... \\]` (rendered by Kami), term glossaries wrapped in `<code>` (never
rendered, because `<code>`/`<pre>` are explicitly ignored by the MathJax
pipeline), and prose with bare LaTeX. A reader therefore saw literal
`\\mathbf{D}\\mathbf{A}` in the middle of an otherwise clean page.

This module fixes the representation, not the science:

* `protect_math` turns a source string into escaped HTML in which real
  mathematics is wrapped in `\\( ... \\)` (inline) or `\\[ ... \\]` (display),
  and genuine code spans stay `<code>`.
* `unrendered_math_errors` is the deterministic gate: after rendering, a Reader
  must contain zero surviving TeX control sequences outside rendered SVG.

It deliberately does not judge whether a formula is *correct* - that is the
independent source review's job (Issue #46). It only guarantees that a formula
that the model wrote reaches the page as mathematics instead of as punctuation.
"""
from __future__ import annotations

import html
import re

# Commands that are unambiguously mathematics when they appear in prose.
_MATH_COMMANDS = (
    r"\\[a-zA-Z]+",
)
_TEX_COMMAND_RE = re.compile(r"\\[a-zA-Z]{2,}")

# Genuine inline code the author meant as code, not mathematics.
_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")

# Text that is already display math in the manuscript.
_DISPLAY_RE = re.compile(r"\\\[(.+?)\\\]", re.S)
_INLINE_RE = re.compile(r"\\\((.+?)\\\)", re.S)

# Deliberately no `$...$` support: manuscripts use \( \) and \[ \], and treating
# dollars as delimiters turns currency like "$5 and $6" into bogus formulas.

# A bare TeX run begins at a control sequence. It continues through adjacent
# ASCII math characters and across spaces only when another control sequence
# follows, so `\Delta \text{Acc}` stays one formula but `\varepsilon 很小` stops.
_CJK_RE = re.compile(r"[\u2e80-\u9fff\uf900-\ufaff\uff00-\uffef]")
_MATH_CHARS = set("\\{}^_=+-*/<>()[]|!:'\"0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.")
_LEFT_EXTEND = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_^{}")
_TRAILING_PUNCT = ".,;:"

# Wrapping in these tags makes MathJax skip the content, so never emit math there.
_CODE_LIKE_TAGS = ("code", "pre", "samp", "kbd", "tt")


def _looks_like_math(text: str) -> bool:
    """True when a bare string is mathematics the reader must see as math."""
    if not text or len(text) > 2000:
        return False
    return bool(_TEX_COMMAND_RE.search(text))


def math_inline(tex: str) -> str:
    """Wrap TeX as an inline math span for the Kami/MathJax pipeline."""
    return f"\\( {tex.strip()} \\)"


def math_display(tex: str) -> str:
    """Wrap TeX as a display equation for the Kami/MathJax pipeline."""
    return f"\\[ {tex.strip()} \\]"


def render_math_source(raw: str) -> str:
    """Render a source string, converting delimited and bare TeX to math spans.

    The returned string is HTML-escaped text plus `\\(...\\)` / `\\[...\\]`
    markers, which Kami's `render_latex_in_html` then converts to SVG.
    """
    if not raw:
        return ""
    text = html.escape(str(raw))

    # Already-delimited math survives escaping unchanged in structure.
    text = _DISPLAY_RE.sub(lambda m: math_display(html.unescape(m.group(1))), text)
    text = _INLINE_RE.sub(lambda m: math_inline(html.unescape(m.group(1))), text)

    # A term glossary stores raw TeX without delimiters; that is the exact case
    # that produced literal \mathbf{D}\mathbf{A} inside <code>.
    if _looks_like_math(html.unescape(text)) and not re.search(r"\\[\[(]", text):
        return math_inline(html.unescape(text))

    return text


def term_html(term: str) -> str:
    """Render one glossary term as mathematics, never as a code span."""
    return math_inline(term) if _looks_like_math(term) else html.escape(str(term or ""))


def protect_math(text: str) -> str:
    """Escape prose while marking every mathematical fragment as math.

    Bare TeX in prose becomes inline math; genuine ``backtick`` spans stay code.
    """
    if not text:
        return ""
    pieces: list[str] = []
    cursor = 0
    for match in _CODE_SPAN_RE.finditer(text):
        pieces.append(_protect_plain(text[cursor:match.start()]))
        pieces.append(f"<code>{html.escape(match.group(1))}</code>")
        cursor = match.end()
    pieces.append(_protect_plain(text[cursor:]))
    return "".join(pieces)


def _protect_plain(segment: str) -> str:
    """Escape a plain segment, turning delimited and bare TeX into math spans."""
    if not segment:
        return ""
    sentinels: list[str] = []

    def _stash(value: str) -> str:
        sentinels.append(value)
        return f"\x00{len(sentinels) - 1}\x00"

    # Delimited math first, so bare-TeX scanning cannot touch its interior.
    segment = _DISPLAY_RE.sub(lambda m: _stash(math_display(m.group(1))), segment)
    segment = _INLINE_RE.sub(lambda m: _stash(math_inline(m.group(1))), segment)
    segment = _wrap_bare_tex(segment, _stash)

    escaped = html.escape(segment)
    for idx, value in enumerate(sentinels):
        escaped = escaped.replace(f"\x00{idx}\x00", value)
    return escaped


def _bare_tex_runs(text: str) -> list[tuple[int, int]]:
    """Locate bare TeX runs in plain text as (start, end) spans."""
    runs: list[tuple[int, int]] = []
    i, n = 0, len(text)
    while i < n:
        if text[i] != "\\" or i + 2 >= n or not text[i + 1].isalpha() or not text[i + 2].isalpha():
            i += 1
            continue
        start = i
        # Include an immediately preceding operand such as the D in D\alpha.
        while start > 0 and text[start - 1] in _LEFT_EXTEND:
            start -= 1
        j = i
        depth = 0
        while j < n:
            ch = text[j]
            if ch == "{":
                depth += 1
                j += 1
                continue
            if ch == "}":
                depth = max(0, depth - 1)
                j += 1
                continue
            if ch in _MATH_CHARS:
                j += 1
                continue
            if ch.isspace():
                # Inside a group, spaces are part of the formula (\Delta \text{Acc}).
                if depth > 0:
                    j += 1
                    continue
                # Otherwise only join across a gap when math clearly continues.
                k = j
                while k < n and text[k].isspace():
                    k += 1
                if k >= n:
                    break
                nxt = text[k]
                is_control = (
                    nxt == "\\" and k + 2 < n and text[k + 1].isalpha() and text[k + 2].isalpha()
                )
                # `\alpha > 0` must stay one formula: after an operator the next
                # operand belongs to the same expression.
                after_operator = j > 0 and text[j - 1] in "+-*/=<>|"
                if is_control or nxt in "+-*/=<>|" or (after_operator and nxt in _MATH_CHARS):
                    j = k
                    continue
            break
        end = j
        # Hand trailing sentence punctuation back to the prose.
        while end > start and text[end - 1] in _TRAILING_PUNCT:
            end -= 1
        # A run that opens a group or \left( but does not close it would be
        # handed to MathJax as broken TeX. Extend forward until balanced, but
        # never across CJK prose.
        end = _extend_to_balanced(text, start, end)
        if end > start:
            runs.append((start, end))
            i = end
        else:
            i = j
    return runs


def _extend_to_balanced(text: str, start: int, end: int) -> int:
    """Grow a candidate run until braces and \\left/\\right pairs balance."""
    def _unbalanced(chunk: str) -> bool:
        depth = 0
        for ch in chunk:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
        lefts = len(re.findall(r"\\left\b", chunk))
        rights = len(re.findall(r"\\right\b", chunk))
        return depth != 0 or lefts != rights

    if not _unbalanced(text[start:end]):
        return end
    cursor = end
    n = len(text)
    while cursor < n:
        ch = text[cursor]
        if _CJK_RE.match(ch):
            break
        cursor += 1
        if ch in ("}", "\\)") and not _unbalanced(text[start:cursor]):
            break
    return cursor if not _unbalanced(text[start:cursor]) else end


def _wrap_bare_tex(segment: str, _stash) -> str:
    """Replace each bare TeX run with an inline-math sentinel."""
    runs = _bare_tex_runs(segment)
    if not runs:
        return segment
    out: list[str] = []
    cursor = 0
    for start, end in runs:
        out.append(segment[cursor:start])
        out.append(_stash(math_inline(segment[start:end])))
        cursor = end
    out.append(segment[cursor:])
    return "".join(out)


def strip_rendered_math(html_text: str) -> str:
    """Remove rendered math and code spans, leaving only visible prose."""
    text = re.sub(r"<mjx-container.*?</mjx-container>", " ", html_text, flags=re.S)
    text = re.sub(r"<svg.*?</svg>", " ", text, flags=re.S)
    text = re.sub(r"<span class=['\"]math-(?:source|display)['\"].*?</span>", " ", text, flags=re.S)
    for tag in _CODE_LIKE_TAGS:
        text = re.sub(rf"<{tag}\b.*?</{tag}>", " ", text, flags=re.S)
    return text


def unrendered_math_errors(html_text: str, *, limit: int = 5) -> list[str]:
    """Return one error per surviving TeX control sequence in visible output."""
    if not html_text:
        return ["Reader HTML is empty; mathematics cannot have been rendered"]
    visible = strip_rendered_math(html_text)
    offenders: list[str] = []
    for match in _TEX_COMMAND_RE.finditer(visible):
        snippet = visible[max(0, match.start() - 40): match.end() + 40]
        snippet = re.sub(r"\s+", " ", html.escape(snippet.strip()))
        offenders.append(f"unrendered TeX command {match.group(0)!r} near: {snippet}")
        if len(offenders) >= limit:
            break
    return offenders


def rendered_math_count(html_text: str) -> int:
    """Count distinct rendered formula containers."""
    return len(re.findall(r"<mjx-container", html_text or ""))


if __name__ == "__main__":  # pragma: no cover - manual probe
    sample = "核心项 \\mathbf{D}\\mathbf{A} 表示字典与稀疏系数之积"
    print(protect_math(sample))
