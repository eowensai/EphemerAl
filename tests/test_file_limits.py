import unittest
from unittest.mock import Mock
from utils import validate_file_size, MAX_UPLOAD_SIZE_MB

class TestFileLimits(unittest.TestCase):
    def test_small_file(self):
        f = Mock()
        f.name = "small.txt"
        f.size = 100 * 1024  # 100KB
        valid, msg = validate_file_size(f)
        self.assertTrue(valid)
        self.assertEqual(msg, "")

    def test_large_file(self):
        f = Mock()
        f.name = "huge.zip"
        # 1 byte over the limit
        f.size = (MAX_UPLOAD_SIZE_MB * 1024 * 1024) + 1
        valid, msg = validate_file_size(f)
        self.assertFalse(valid)
        self.assertIn(f"exceeds {MAX_UPLOAD_SIZE_MB}MB limit", msg)

    def test_exact_limit(self):
        f = Mock()
        f.name = "limit.txt"
        f.size = MAX_UPLOAD_SIZE_MB * 1024 * 1024
        valid, msg = validate_file_size(f)
        self.assertTrue(valid)

if __name__ == '__main__':
    unittest.main()
