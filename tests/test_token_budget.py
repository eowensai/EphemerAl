from ephemeral.token_budget import _heuristic_token_estimate


def test_heuristic_token_estimate_ranges():
    assert _heuristic_token_estimate("") == 0
    assert _heuristic_token_estimate("a") >= 1
    assert _heuristic_token_estimate("hello world") >= 1
    short = _heuristic_token_estimate("x" * 20)
    long = _heuristic_token_estimate("x" * 2000)
    assert long > short
