# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from duplicate_finder import utils as utils


def test_human_readable_size() -> None:
    assert utils.int_file_size_to_str(0) == "0 B"
    assert utils.int_file_size_to_str(1023) == "1023 B"
    assert utils.int_file_size_to_str(1024) == "1.0 KB"
    assert utils.int_file_size_to_str(1024**2) == "1.0 MB"
