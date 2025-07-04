# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from duplicate_finder import utils as utils


def test_human_readable_size():
    assert utils.humanize_size(0) == "0 B"
    assert utils.humanize_size(1023) == "1023 B"
    assert utils.humanize_size(1024) == "1.0 KB"
    assert utils.humanize_size(1024**2) == "1.0 MB"
