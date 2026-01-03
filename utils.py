from typing import Tuple

MAX_UPLOAD_SIZE_MB = 200

def validate_file_size(file_obj, max_mb=MAX_UPLOAD_SIZE_MB) -> Tuple[bool, str]:
    """
    Checks if the file size is within limits.
    Returns (True, "") if valid.
    Returns (False, error_message) if invalid.
    """
    # Streamlit UploadedFile has a .size attribute (in bytes)
    if hasattr(file_obj, "size"):
        if file_obj.size > max_mb * 1024 * 1024:
            return False, f"❌ {file_obj.name} exceeds {max_mb}MB limit"
    return True, ""
