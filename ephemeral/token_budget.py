from ephemeral.config import TOKEN_HEURISTIC_CHARS_PER_TOKEN


def _heuristic_token_estimate(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / TOKEN_HEURISTIC_CHARS_PER_TOKEN))
