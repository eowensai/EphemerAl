import re
from html import escape as html_escape
from typing import List, Tuple, Union

from ephemeral.config import CONTEXT_PREFIX


def build_message_text(messages: List[dict]) -> str:
    """Flatten message content into text for token estimation."""
    chunks: List[str] = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for part in content:
                if part.get("type") == "text":
                    text = part.get("text")
                    if text:
                        chunks.append(text)
        else:
            if content:
                chunks.append(str(content))
    return "\n".join(chunks)


def _extract_export_info(content: Union[str, list]) -> Tuple[List[str], List[str], str]:
    """
    Extract (doc_lines, img_lines, message_text) from message content.

    Notes:
    - We do NOT export the full extracted document text from Context:, only filenames and counts.
    - Synthetic context parts (marked with _synthetic flag) are parsed for metadata only.
    """
    doc_lines: List[str] = []
    img_lines: List[str] = []
    text_chunks: List[str] = []

    if not isinstance(content, list):
        return doc_lines, img_lines, "" if content is None else str(content)

    doc_seen = set()
    img_seen = set()
    img_marker_names: List[str] = []

    for part in content:
        ptype = part.get("type")

        if ptype == "text":
            text = part.get("text", "")

            if part.get("_synthetic"):
                ctx = text[len(CONTEXT_PREFIX) :] if text.startswith(CONTEXT_PREFIX) else text
                blocks = re.split(r"(?m)^---\s*(.+?)\s*---\s*$", ctx)
                for i in range(1, len(blocks), 2):
                    fname = (blocks[i] or "").strip()
                    extracted = blocks[i + 1] if i + 1 < len(blocks) else ""
                    char_count = len((extracted or "").strip())
                    if fname and fname not in doc_seen:
                        doc_seen.add(fname)
                        doc_lines.append(f"- 📄 {fname} ({char_count:,} characters extracted)")

            elif text.startswith("📄 *") and text.endswith("*"):
                fname = text[len("📄 *") : -1].strip()
                if fname and fname not in doc_seen:
                    doc_seen.add(fname)
                    doc_lines.append(f"- 📄 {fname}")

            elif text.startswith("📷 *") and text.endswith("*"):
                fname = text[len("📷 *") : -1].strip()
                if fname:
                    img_marker_names.append(fname)

            else:
                if text and text.strip():
                    text_chunks.append(text.strip())

        elif ptype == "image":
            fname = (part.get("filename") or "image").strip()
            if fname and fname not in img_seen:
                img_seen.add(fname)
                img_lines.append(f"- 📷 {fname}")

        elif ptype == "image_url":
            fname = (part.get("filename") or "image").strip()
            if fname and fname not in img_seen:
                img_seen.add(fname)
                img_lines.append(f"- 📷 {fname}")

    for fname in img_marker_names:
        if fname not in img_seen:
            img_seen.add(fname)
            img_lines.append(f"- 📷 {fname}")

    message_text = "\n\n".join(text_chunks).strip()
    return doc_lines, img_lines, message_text


def build_conversation_markdown(messages: List[dict]) -> str:
    """Build a Markdown transcript used as plain-text clipboard fallback."""
    lines: List[str] = ["# EphemerAl Conversation", ""]

    for msg in messages:
        lines.extend(_build_message_markdown_lines(msg))
        lines.append("---")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _inline_md_to_html(text: str) -> str:
    """Minimal inline Markdown -> HTML for clipboard friendliness."""
    t = html_escape(text)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", t)
    return t


def _md_block_to_html(md_block: str) -> str:
    """Minimal block Markdown -> HTML for clipboard friendliness."""
    md_block = (md_block or "").replace("\r\n", "\n")
    lines = md_block.split("\n")

    out: List[str] = []
    para: List[str] = []
    in_ul = False
    in_ol = False

    def flush_para() -> None:
        nonlocal para
        if para:
            out.append("<p>" + "<br>".join(para) + "</p>")
            para = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    for raw in lines:
        stripped = (raw or "").strip()

        if stripped == "":
            flush_para()
            continue

        if stripped in {"---", "***", "___"}:
            flush_para()
            close_lists()
            out.append("<hr>")
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            close_lists()
            level = len(m.group(1))
            out.append(f"<h{level}>" + _inline_md_to_html(m.group(2)) + f"</h{level}>")
            continue

        m = re.match(r"^[-*•]\s+(.*)$", stripped)
        if m:
            flush_para()
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append("<li>" + _inline_md_to_html(m.group(1)) + "</li>")
            continue

        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            flush_para()
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append("<li>" + _inline_md_to_html(m.group(1)) + "</li>")
            continue

        close_lists()
        para.append(_inline_md_to_html(stripped))

    flush_para()
    close_lists()
    return "\n".join(out)


def _md_to_html_basic(md: str) -> str:
    """Minimal Markdown -> HTML converter for copy/paste purposes."""
    md = (md or "").replace("\r\n", "\n")
    parts = md.split("```")
    out: List[str] = []

    for i, part in enumerate(parts):
        if i % 2 == 1:
            code = html_escape(part.strip("\n"))
            out.append("<pre><code>" + code + "</code></pre>")
        else:
            block_html = _md_block_to_html(part)
            if block_html.strip():
                out.append(block_html)

    return "\n".join(out).strip()


def build_conversation_html(messages: List[dict]) -> str:
    """Rich transcript as HTML for clipboard copy."""
    chunks: List[str] = ["<div>", "<p><strong>EphemerAl Conversation</strong></p>"]

    for msg in messages:
        chunks.append(build_message_html(msg))
        chunks.append("<hr>")

    chunks.append("</div>")
    return "\n".join(chunks).strip()


def _build_message_markdown_lines(message: dict) -> List[str]:
    """Build Markdown lines for a single message export."""
    role = message.get("role", "assistant")
    role_title = "User" if role == "user" else "Assistant"
    lines: List[str] = [f"**{role_title}**"]

    doc_lines, img_lines, message_text = _extract_export_info(message.get("content", ""))

    if doc_lines or img_lines:
        lines.append("")
        lines.append("Attachments:")
        lines.extend(doc_lines)
        lines.extend(img_lines)

    if message_text:
        lines.append("")
        lines.append(message_text)

    lines.append("")
    return lines


def build_message_markdown(message: dict) -> str:
    """Build clipboard-friendly Markdown for one message turn."""
    return "\n".join(_build_message_markdown_lines(message)).strip() + "\n"


def build_message_html(message: dict) -> str:
    """Build clipboard-friendly HTML for one message turn."""
    chunks: List[str] = []
    role = message.get("role", "assistant")
    role_title = "User" if role == "user" else "Assistant"
    chunks.append(f"<p><strong>{html_escape(role_title)}</strong></p>")

    doc_lines, img_lines, message_text = _extract_export_info(message.get("content", ""))

    if doc_lines or img_lines:
        chunks.append("<p><strong>Attachments:</strong></p>")
        chunks.append("<ul>")
        for line in (doc_lines + img_lines):
            item = line.lstrip("- ").strip()
            chunks.append("<li>" + _inline_md_to_html(item) + "</li>")
        chunks.append("</ul>")

    if message_text:
        chunks.append(_md_to_html_basic(message_text))

    return "\n".join(chunks).strip()
