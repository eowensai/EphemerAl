
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock streamlit module
if "streamlit" not in sys.modules:
    mock_st = MagicMock()
    mock_st.session_state = {}
    sys.modules["streamlit"] = mock_st
else:
    mock_st = sys.modules["streamlit"]

# Now we can import the utils module which imports streamlit
from utils import get_cached_exports, get_conversation_signature

class TestExportCaching(unittest.TestCase):
    def setUp(self):
        # Reset session state for each test
        mock_st.session_state = {}
        # Clear the module-level mock if needed (though we rely on the same mock object)
        mock_st.session_state["_export_cache"] = {}

    def test_signature(self):
        messages = [{"id": "1", "content": "Hello"}]
        sig = get_conversation_signature(messages)
        self.assertEqual(sig, (1, "1", 5))

        messages.append({"id": "2", "content": "Hi"})
        sig = get_conversation_signature(messages)
        self.assertEqual(sig, (2, "2", 2))

    @patch("utils.build_conversation_markdown")
    @patch("utils.build_conversation_html")
    def test_caching_behavior(self, mock_html_gen, mock_md_gen):
        mock_md_gen.return_value = "Markdown"
        mock_html_gen.return_value = "HTML"

        messages = [{"id": "1", "role": "user", "content": "hello"}]

        # First call - should generate
        md, html = get_cached_exports(messages)

        self.assertEqual(md, "Markdown")
        self.assertEqual(html, "HTML")
        mock_md_gen.assert_called_once()
        mock_html_gen.assert_called_once()

        # Second call with same messages - should return cached
        mock_md_gen.reset_mock()
        mock_html_gen.reset_mock()

        md2, html2 = get_cached_exports(messages)

        self.assertEqual(md2, "Markdown")
        self.assertEqual(html2, "HTML")
        mock_md_gen.assert_not_called()
        mock_html_gen.assert_not_called()

        # Update content of last message
        messages[-1]["content"] = "hello world"

        md3, html3 = get_cached_exports(messages)

        mock_md_gen.assert_called_once()
        mock_html_gen.assert_called_once()
        self.assertEqual(mock_st.session_state["_export_cache"]["signature"], (1, "1", 11))

if __name__ == "__main__":
    unittest.main()
