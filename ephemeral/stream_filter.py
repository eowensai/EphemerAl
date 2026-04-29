import re
from typing import List, Tuple


class ThinkStreamFilter:
    """Stateful filter for stripping streamed think/thought-channel blocks across chunks."""

    def __init__(self) -> None:
        self.in_think_block = False
        self.current_think_close_tag = ""
        self.stream_parse_buffer = ""
        self.think_tag_pairs: List[Tuple[str, str]] = [
            ("<|channel>thought\n", "<channel|>"),
            ("<think>", "</think>"),
        ]
        self.open_tag_tail_len = max(len(open_tag) for open_tag, _ in self.think_tag_pairs) - 1
        self.close_tag_tail_lens = {
            close_tag: len(close_tag) - 1 for _, close_tag in self.think_tag_pairs
        }

    def process_chunk(self, delta: str) -> str:
        if not delta:
            return ""

        output = ""
        self.stream_parse_buffer += delta

        while self.stream_parse_buffer:
            if self.in_think_block:
                close_idx = self.stream_parse_buffer.find(self.current_think_close_tag)
                if close_idx == -1:
                    close_tag_tail_len = self.close_tag_tail_lens[self.current_think_close_tag]
                    if len(self.stream_parse_buffer) > close_tag_tail_len:
                        self.stream_parse_buffer = self.stream_parse_buffer[-close_tag_tail_len:]
                    break

                self.stream_parse_buffer = self.stream_parse_buffer[
                    close_idx + len(self.current_think_close_tag) :
                ]
                self.in_think_block = False
                self.current_think_close_tag = ""
                continue

            nearest_open = None
            for open_tag, close_tag in self.think_tag_pairs:
                open_idx = self.stream_parse_buffer.find(open_tag)
                if open_idx == -1:
                    continue
                if nearest_open is None or open_idx < nearest_open[0]:
                    nearest_open = (open_idx, open_tag, close_tag)

            if nearest_open is None:
                if len(self.stream_parse_buffer) > self.open_tag_tail_len:
                    output += self.stream_parse_buffer[:-self.open_tag_tail_len]
                    self.stream_parse_buffer = self.stream_parse_buffer[-self.open_tag_tail_len:]
                break

            open_idx, open_tag, close_tag = nearest_open
            output += self.stream_parse_buffer[:open_idx]
            self.stream_parse_buffer = self.stream_parse_buffer[open_idx + len(open_tag) :]
            self.in_think_block = True
            self.current_think_close_tag = close_tag

        return output

    def finalize(self) -> str:
        if self.stream_parse_buffer and not self.in_think_block:
            tail = self.stream_parse_buffer
            self.stream_parse_buffer = ""
            return tail
        self.stream_parse_buffer = ""
        return ""


def strip_think_blocks(text: str) -> str:
    text = re.sub(r"<\|channel>thought\n.*?<channel\|>\s*", "", text, flags=re.DOTALL)
    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
    return text
