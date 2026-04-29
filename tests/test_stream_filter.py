from ephemeral.stream_filter import ThinkStreamFilter, strip_think_blocks


def _run_chunks(chunks):
    f = ThinkStreamFilter()
    out = ""
    for c in chunks:
        out += f.process_chunk(c)
    out += f.finalize()
    return out, f


def test_complete_think_block_stripped():
    out, _ = _run_chunks(["hello <think>secret</think> world"])
    assert out == "hello  world"


def test_complete_channel_thought_block_stripped():
    out, _ = _run_chunks(["a<|channel>thought\nsecret<channel|>b"])
    assert out == "ab"


def test_split_chunks_tag_boundaries():
    out, _ = _run_chunks(["hello <thi", "nk>secret</th", "ink> world"])
    assert out == "hello  world"


def test_unclosed_think_block_end_of_stream():
    out, f = _run_chunks(["safe <think>secret forever"])
    assert out == "safe "
    assert f.in_think_block is True


def test_content_outside_blocks_unchanged_and_multiple_blocks():
    out, _ = _run_chunks([
        "A<think>x</think>B<|channel>thought\ny<channel|>C<think>z</think>D"
    ])
    assert out == "ABCD"


def test_post_strip_defense_in_depth():
    assert strip_think_blocks("a<think>b</think>c") == "ac"
    assert strip_think_blocks("a<|channel>thought\nb<channel|>c") == "ac"
