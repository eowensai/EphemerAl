from ephemeral.export import (
    _extract_export_info,
    _md_to_html_basic,
    build_conversation_html,
    build_conversation_markdown,
    build_message_html,
    build_message_markdown,
)


def test_extract_export_info_plain_and_none():
    assert _extract_export_info("hello") == ([], [], "hello")
    assert _extract_export_info(None) == ([], [], "")


def test_extract_export_info_multipart_with_images_docs_and_synthetic_context():
    content = [
        {
            "type": "text",
            "text": "Context:\n--- alpha.pdf ---\nabc\n\n--- beta.docx ---\n12345\n",
            "_synthetic": True,
        },
        {"type": "text", "text": "📄 *manual.txt*"},
        {"type": "text", "text": "📄 *manual.txt*"},
        {"type": "text", "text": "📷 *photo.png*"},
        {"type": "image", "filename": "photo.png"},
        {"type": "image_url", "filename": "scan.jpg"},
        {"type": "text", "text": "  user note  "},
        {"type": "text", "text": ""},
    ]

    docs, imgs, text = _extract_export_info(content)
    assert "- 📄 alpha.pdf (3 characters extracted)" in docs
    assert "- 📄 beta.docx (5 characters extracted)" in docs
    assert "- 📄 manual.txt" in docs
    assert imgs == ["- 📷 photo.png", "- 📷 scan.jpg"]
    assert text == "user note"


def test_markdown_and_html_build_and_escape():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "📄 *doc1.pdf*"},
                {"type": "text", "text": "hello **world**"},
            ],
        },
        {
            "role": "assistant",
            "content": "<script>alert(1)</script>\n\n<div>content</div>",
        },
    ]

    md = build_conversation_markdown(messages)
    assert "# EphemerAl Conversation" in md
    assert "**User**" in md
    assert "Attachments:" in md
    assert "- 📄 doc1.pdf" in md

    html = build_conversation_html(messages)
    assert "<strong>User</strong>" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;div&gt;content&lt;/div&gt;" in html
    assert "<script>" not in html


def test_single_message_builders_match_turn_expectations():
    message = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "📄 *doc1.pdf*"},
            {"type": "text", "text": "hello **world**"},
        ],
    }

    md = build_message_markdown(message)
    assert "**Assistant**" in md
    assert "Attachments:" in md
    assert "- 📄 doc1.pdf" in md
    assert "hello **world**" in md

    html = build_message_html(message)
    assert "<strong>Assistant</strong>" in html
    assert "<strong>Attachments:</strong>" in html
    assert "<li>📄 doc1.pdf</li>" in html
    assert "<p>hello <strong>world</strong></p>" in html


def test_md_to_html_basic_formats():
    md = """# Heading

Paragraph with **bold**, *italic*, and `code` plus & entity.

- item 1
- item 2

1. first
2. second

---

```python
print('x')
```
"""
    html = _md_to_html_basic(md)
    assert "<h1>Heading</h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html
    assert "<code>code</code>" in html
    assert "&amp; entity" in html
    assert "<ul>" in html and "<ol>" in html
    assert "<hr>" in html
    assert "<pre><code>python\nprint(&#x27;x&#x27;)</code></pre>" in html
