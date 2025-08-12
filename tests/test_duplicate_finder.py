# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

from duplicate_finder.duplicate_finder import DuplicateFinder
from duplicate_finder.duplicate_finder_config import DuplicateFinderConfig


def create_file(path: Path, content: bytes) -> Path:
    path.write_bytes(content)
    return path


def make_config(
    folder: Path,
    *,
    exclude_patterns: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    max_file_size_str: Optional[str] = None,
    min_file_size_str: Optional[str] = None,
    output_file_path: Optional[str] = None,
    sort_by_group_size: bool = False,
    sort_by_file_size: bool = False,
    threads_count: int = 1,
    verify_content: bool = False,
    delete_duplicates: bool = False,
    delete_report_file_path: Optional[str] = None,
    interactive_mode: bool = False,
    dry_run: bool = False,
) -> DuplicateFinderConfig:
    return DuplicateFinderConfig(
        scan_folder_path=str(folder),
        exclude_patterns=exclude_patterns,
        include_patterns=include_patterns,
        max_file_size_str=max_file_size_str,
        min_file_size_str=min_file_size_str,
        output_file_path=output_file_path,
        sort_by_group_size=sort_by_group_size,
        sort_by_file_size=sort_by_file_size,
        threads_count=threads_count,
        verify_content=verify_content,
        delete_duplicates=delete_duplicates,
        delete_report_file_path=delete_report_file_path,
        interactive_mode=interactive_mode,
        dry_run=dry_run,
    )


def test_finds_identical_files(tmp_path: Path) -> None:
    file1 = create_file(tmp_path / "a.txt", b"duplicate content")
    file2 = create_file(tmp_path / "b.txt", b"duplicate content")

    config = make_config(tmp_path, verify_content=True)
    finder = DuplicateFinder()
    result = finder.run(config)

    file_paths = {str(file1.resolve()), str(file2.resolve())}
    assert any(
        file_paths.issubset(set(group))
        for group in result
    ), f"Duplicate groups found: {result}"


def test_no_duplicates(tmp_path: Path) -> None:
    create_file(tmp_path / "a.txt", b"hello")
    create_file(tmp_path / "b.txt", b"world")

    config = make_config(tmp_path)
    finder = DuplicateFinder()
    result = finder.run(config)

    assert result == [] or all(len(group) == 1 for group in result)


def test_exclude_patterns(tmp_path: Path) -> None:
    create_file(tmp_path / "a.txt", b"same")
    create_file(tmp_path / "b.log", b"same")

    config = make_config(tmp_path, exclude_patterns=["*.log"])
    finder = DuplicateFinder()
    result = finder.run(config)

    assert not any("b.log" in str(f) for group in result for f in group)


def test_delete_duplicates(tmp_path: Path) -> None:
    create_file(tmp_path / "a.txt", b"dup")
    create_file(tmp_path / "b.txt", b"dup")

    config = make_config(tmp_path, delete_duplicates=True, dry_run=False)

    finder = DuplicateFinder()
    with patch("builtins.input", return_value="y"):
        finder.run(config)

    remaining_files = list(tmp_path.iterdir())
    assert len(remaining_files) == 1
    assert remaining_files[0].read_bytes() == b"dup"


def test_verify_content_true(tmp_path: Path) -> None:
    create_file(tmp_path / "a.txt", b"abcd")
    create_file(tmp_path / "b.txt", b"abce")

    config = make_config(tmp_path, verify_content=True)
    finder = DuplicateFinder()
    result = finder.run(config)

    assert all(len(group) == 1 for group in result)
