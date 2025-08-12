# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from duplicate_finder.duplicate_finder_config import DuplicateFinderConfig


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_normalize_dir_path_valid(temp_dir: str) -> None:
    cfg = DuplicateFinderConfig(scan_folder_path=temp_dir)
    assert Path(cfg.scan_folder_path) == Path(temp_dir).resolve()


def test_normalize_dir_path_invalid() -> None:
    with pytest.raises(ValueError):
        DuplicateFinderConfig(scan_folder_path="/non/existent/path")


def test_normalize_pattern() -> None:
    cfg = DuplicateFinderConfig(scan_folder_path=".",
                                exclude_patterns=[" a ", "", "b"])
    assert cfg.exclude_patterns == ["a", "b"]


def test_normalize_pattern_none() -> None:
    cfg = DuplicateFinderConfig(scan_folder_path=".")
    assert cfg.exclude_patterns is None


def test_normalize_str_file_size_valid(temp_dir: str) -> None:
    cfg = DuplicateFinderConfig(
        scan_folder_path=temp_dir,
        max_file_size_str="10MB",
        min_file_size_str="1KB"
    )
    assert isinstance(cfg.max_file_size, int)
    assert isinstance(cfg.min_file_size, int)
    assert cfg.max_file_size > cfg.min_file_size


@pytest.mark.parametrize("size_str", ["10", "2.5GB", "100KiB"])
def test_normalize_str_file_size_various(size_str: str, temp_dir: str) -> None:
    cfg = DuplicateFinderConfig(scan_folder_path=temp_dir,
                                max_file_size_str=size_str)
    assert isinstance(cfg.max_file_size, int)


@pytest.mark.parametrize("size_str", ["10M", "abc", "1.2.3GB", ""])
def test_normalize_str_file_size_invalid(size_str: str, temp_dir: str) -> None:
    with pytest.raises(ValueError):
        DuplicateFinderConfig(scan_folder_path=temp_dir,
                              max_file_size_str=size_str)


def test_normalize_file_path_none(temp_dir: str) -> None:
    cfg = DuplicateFinderConfig(scan_folder_path=temp_dir,
                                output_file_path=None)
    assert cfg.output_file_path is None


def test_normalize_file_path_valid(temp_dir: str) -> None:
    path = Path(temp_dir) / "output.txt"
    cfg = DuplicateFinderConfig(scan_folder_path=temp_dir,
                                output_file_path=str(path))
    assert cfg.output_file_path == str(path.resolve())


def test_normalize_threads_counter_default(temp_dir: str) -> None:
    cfg = DuplicateFinderConfig(scan_folder_path=temp_dir,
                                threads_count=0)
    assert cfg.threads_count > 0


def test_normalize_threads_counter_custom(temp_dir: str) -> None:
    cfg = DuplicateFinderConfig(scan_folder_path=temp_dir,
                                threads_count=4)
    assert cfg.threads_count == 4
