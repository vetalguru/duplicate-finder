# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import hashlib
from pathlib import Path

import duplicate_finder.utils as utils
import pytest


# calc_file_sha256
def test_sha256_known_content(tmp_path: str) -> None:
    content = b"hello world"
    file_path = Path(tmp_path) / "test.txt"
    file_path.write_bytes(content)

    expected_hash = hashlib.sha256(content).hexdigest()

    assert utils.calc_file_sha256(str(file_path)) == expected_hash


def test_sha256_empty_file(tmp_path: str) -> None:
    file_path = Path(tmp_path) / "empty.txt"
    file_path.write_bytes(b"")

    expected_hash = hashlib.sha256(b"").hexdigest()

    assert utils.calc_file_sha256(str(file_path)) == expected_hash


def test_sha256_large_file(tmp_path: str) -> None:
    large_content = b"a" * (65536 * 3 + 123)  # more than 3 block sizes
    file_path = Path(tmp_path) / "large.bin"
    file_path.write_bytes(large_content)

    expected_hash = hashlib.sha256(large_content).hexdigest()

    assert utils.calc_file_sha256(str(file_path),
                                  block_size=65536) == expected_hash


# str_file_size_to_int
@pytest.mark.parametrize(
    "size_str, expected",
    [
        ("1B", 1),
        ("1K", 1000),
        ("1KB", 1000),
        ("1M", 1000**2),
        ("1MB", 1000**2),
        ("1G", 1000**3),
        ("1GB", 1000**3),
        ("1T", 1000**4),
        ("1TB", 1000**4),
        ("1Ki", 1024),
        ("1KiB", 1024),
        ("1Mi", 1024**2),
        ("1MiB", 1024**2),
        ("1Gi", 1024**3),
        ("1GiB", 1024**3),
        ("1Ti", 1024**4),
        ("1TiB", 1024**4),
        ("123", 123),
        ("  2.5 MB ", int(2.5 * 1000**2)),
        ("10mb", 10 * 1000**2),
    ],
)
def test_str_file_size_to_int_valid(size_str: str, expected: int) -> None:
    assert utils.str_file_size_to_int(size_str) == expected


@pytest.mark.parametrize(
    "invalid_str",
    [
        "abc",
        "10XB",     # unknown unit
        "1.2.3GB",  # multiple dots
        "MB",       # no number
        ".",        # just a dot
        "",         # empty string
    ],
)
def test_str_file_size_to_int_invalid(invalid_str: str) -> None:
    with pytest.raises(ValueError):
        utils.str_file_size_to_int(invalid_str)


# int_file_size_to_str
@pytest.mark.parametrize(
    "size_bytes, expected",
    [
        (0, "0 B"),
        (1, "1 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1024**2, "1.0 MB"),
        (1.5 * 1024**2, "1.5 MB"),
        (1024**3, "1.0 GB"),
        (1024**4, "1.0 TB"),
        (1024**5, "1.0 PB"),
    ],
)
def test_int_file_size_to_str_valid(size_bytes: int, expected: str) -> None:
    assert utils.int_file_size_to_str(size_bytes) == expected


@pytest.mark.parametrize(
    "invalid_input",
    [
        None,
        -1,
        "100",
        [1024],
        {"bytes": 1024},
    ],
)
def test_int_file_size_to_str_invalid(invalid_input: int) -> None:
    assert utils.int_file_size_to_str(invalid_input) == "Invalid size"


# files_are_identical
def create_temp_file(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def test_identical_files(tmp_path: str) -> None:
    file1 = create_temp_file(Path(tmp_path) / "file1.txt", b"hello world")
    file2 = create_temp_file(Path(tmp_path) / "file2.txt", b"hello world")
    assert utils.files_are_identical(
        str(file1),
        str(file2)
    )


def test_different_size_files(tmp_path: str) -> None:
    file1 = create_temp_file(Path(tmp_path) / "file1.txt", b"short")
    file2 = create_temp_file(Path(tmp_path) / "file2.txt", b"longer content")
    assert not utils.files_are_identical(
        str(file1),
        str(file2)
    )


def test_same_size_different_content(tmp_path: str) -> None:
    file1 = create_temp_file(Path(tmp_path) / "file1.txt", b"abc123")
    file2 = create_temp_file(Path(tmp_path) / "file2.txt", b"abc124")
    assert not utils.files_are_identical(
        str(file1),
        str(file2)
    )


def test_empty_files(tmp_path: str) -> None:
    file1 = create_temp_file(Path(tmp_path) / "file1.txt", b"")
    file2 = create_temp_file(Path(tmp_path) / "file2.txt", b"")
    assert utils.files_are_identical(
        str(file1),
        str(file2)
    )


def test_small_chunk_size(tmp_path: str) -> None:
    content = b"abcdefghij" * 100  # 1KB
    file1 = create_temp_file(Path(tmp_path) / "file1.txt", content)
    file2 = create_temp_file(Path(tmp_path) / "file2.txt", content)
    assert utils.files_are_identical(
        str(file1),
        str(file2),
        chunk_size=10
    )
