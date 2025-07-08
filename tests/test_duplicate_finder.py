# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import tempfile
import stat
import sys
import os
import pytest
from pathlib import Path
from duplicate_finder.duplicate_finder import DuplicateFinder
from unittest.mock import patch


def create_file(path: Path, content: str = "data"):
    path.write_text(content, encoding="utf-8")
    return str(path)


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


def test_empty_directory(temp_dir):
    finder = DuplicateFinder()
    result = finder.run(folder_path=temp_dir)
    assert result == []


def test_identical_files(temp_dir):
    file1 = create_file(temp_dir / "a.txt", "abc123")
    file2 = create_file(temp_dir / "b.txt", "abc123")

    finder = DuplicateFinder()
    result = finder.run(folder_path=temp_dir)
    assert len(result) == 1
    assert set(result[0]) == {file1, file2}


def test_different_size_files(temp_dir):
    create_file(temp_dir / "a.txt", "abc123")
    create_file(temp_dir / "b.txt", "abc123456")

    finder = DuplicateFinder()
    result = finder.run(folder_path=temp_dir)
    assert result == []


def test_excluded_pattern(temp_dir):
    create_file(temp_dir / "a.log", "abc")
    create_file(temp_dir / "b.log", "abc")

    finder = DuplicateFinder()
    result = finder.run(
        folder_path=temp_dir,
        exclude_patterns=["*.log"])
    assert result == []


def test_sort_by_group(temp_dir):
    # Three identical, one unique
    f1 = create_file(temp_dir / "f1.txt", "x")
    f2 = create_file(temp_dir / "f2.txt", "x")
    f3 = create_file(temp_dir / "f3.txt", "x")
    create_file(temp_dir / "u.txt", "y")

    finder = DuplicateFinder()
    result = finder.run(
        folder_path=temp_dir,
        sort_by_group=True)
    assert len(result) == 1
    assert set(result[0]) == {f1, f2, f3}


def test_dry_run_deletion(temp_dir, capsys):
    file1 = create_file(temp_dir / "x1.txt", "dupe")
    file2 = create_file(temp_dir / "x2.txt", "dupe")

    finder = DuplicateFinder()
    finder.run(
        folder_path=temp_dir,
        delete=True,
        dry_run=True)
    assert Path(file1).exists()
    assert Path(file2).exists()

    captured = capsys.readouterr()
    assert "[would delete]" in captured.out


def test_actual_deletion(temp_dir):
    file1 = create_file(temp_dir / "x1.txt", "dupe")
    file2 = create_file(temp_dir / "x2.txt", "dupe")

    finder = DuplicateFinder()

    with patch("builtins.input", side_effect=["1"]):
        result = finder.run(
            folder_path=temp_dir,
            delete=True,
            dry_run=False,
            interactive=True)

    remaining = [Path(p) for p in result[0]]
    assert any(p.exists() for p in remaining)

    deleted = {file1, file2} - set(map(str, remaining))
    for path in deleted:
        assert not Path(path).exists()


def test_zero_byte_files_are_duplicates(temp_dir):
    (temp_dir / "zero1.txt").touch()
    (temp_dir / "zero2.txt").touch()

    finder = DuplicateFinder()
    result = finder.run(folder_path=temp_dir)
    assert len(result) == 1
    assert (set(result[0]) ==
            {str(temp_dir / "zero1.txt"),
             str(temp_dir / "zero2.txt")})


def test_nested_directories(temp_dir):
    nested = temp_dir / "folder" / "subfolder"
    nested.mkdir(parents=True)
    file1 = create_file(nested / "a.txt", "hello")
    file2 = create_file(temp_dir / "copy.txt", "hello")

    finder = DuplicateFinder()
    result = finder.run(folder_path=temp_dir)
    assert len(result) == 1
    assert set(result[0]) == {file1, file2}


def test_exclusion_in_nested_paths(temp_dir):
    (temp_dir / "ignore").mkdir()
    create_file(temp_dir / "keep.txt", "same")
    create_file(temp_dir / "ignore" / "skip.txt", "same")

    finder = DuplicateFinder()
    result = finder.run(
        folder_path=temp_dir,
        exclude_patterns=["*/ignore/*"])
    assert result == []


def test_report_saving(temp_dir):
    file1 = create_file(temp_dir / "x.txt", "abc")
    file2 = create_file(temp_dir / "y.txt", "abc")
    report_path = temp_dir / "dupes.txt"

    finder = DuplicateFinder()
    finder.run(
        folder_path=temp_dir,
        output_report_path=report_path)

    text = report_path.read_text(encoding="utf-8")
    assert "Duplicate files" in text
    assert str(file1) in text and str(file2) in text


@pytest.mark.skipif(
    os.name != "posix", reason="chmod 000 works correctly just in POSIX"
)
def test_unreadable_file_skipped(tmp_path):
    protected = tmp_path / "secret.txt"
    protected.write_text("classified")
    protected.chmod(0)

    try:
        finder = DuplicateFinder()
        result = finder.run(folder_path=tmp_path)
        assert result == []
    finally:
        protected.chmod(stat.S_IWUSR | stat.S_IRUSR)


@pytest.mark.skipif(
    sys.platform.startswith("win") and not hasattr(os, "symlink"),
    reason="Symlink creation requires admin or Developer Mode on Windows",
)
def test_symlinks_are_ignored(temp_dir):
    target = create_file(temp_dir / "real.txt", "hello")
    link = temp_dir / "link.txt"

    try:
        link.symlink_to(Path(target))
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted on this system")

    finder = DuplicateFinder()
    result = finder.run(folder_path=temp_dir)
    assert result == []


def test_identical_files_different_names_and_folders(temp_dir):
    (temp_dir / "a").mkdir()
    (temp_dir / "b").mkdir()
    f1 = create_file(temp_dir / "a" / "file.txt", "same")
    f2 = create_file(temp_dir / "b" / "copy.txt", "same")

    finder = DuplicateFinder()
    result = finder.run(folder_path=temp_dir)
    assert len(result) == 1
    assert set(result[0]) == {f1, f2}


def test_file_with_unreadable_stat(temp_dir, monkeypatch):
    broken_path = temp_dir / "fail.txt"
    broken_path.write_text("data")

    class BrokenPath(type(broken_path)):
        def stat(self_inner):
            raise OSError("fake stat error")

    broken_path_obj = BrokenPath(broken_path)

    class DummyFinder(DuplicateFinder):
        def _group_by_size(self_inner):
            self_inner.files_by_size = {4: [str(broken_path_obj)]}

    finder = DummyFinder()
    result = finder.run(folder_path=temp_dir)
    assert result == []


def test_exclude_exact_filename(temp_dir):
    create_file(temp_dir / "keep.txt", "same")
    create_file(temp_dir / "exclude.txt", "same")

    finder = DuplicateFinder()
    result = finder.run(
        folder_path=temp_dir,
        exclude_patterns=["*/exclude.txt"])
    assert result == []


def test_deletion_report_is_created(temp_dir):
    f1 = create_file(temp_dir / "x.txt", "dupe")
    f2 = create_file(temp_dir / "y.txt", "dupe")
    report = temp_dir / "report.txt"

    finder = DuplicateFinder()
    finder.run(
        folder_path=temp_dir,
        delete=True,
        dry_run=True,
        delete_report_path=report)
    text = report.read_text()
    assert "[would delete]" in text
    assert str(f1) in text or str(f2) in text


def test_no_deletion_prompt_if_no_duplicates(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("hello")
    (tmp_path / "b.txt").write_text("world")

    called = False

    def fake_input(prompt):
        nonlocal called
        called = True
        return "n"

    monkeypatch.setattr("builtins.input", fake_input)

    finder = DuplicateFinder()
    finder.run(
        folder_path=tmp_path,
        delete=True,
        interactive=True)

    assert not called, "Input() should not be called when no duplicates exist"


def test_interactive_deletion_keep_first(tmp_path, monkeypatch, capsys):
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("duplicate")
    f2.write_text("duplicate")

    finder = DuplicateFinder()
    finder.run(folder_path=tmp_path)

    monkeypatch.setattr("builtins.input", lambda _: "1")

    finder._interactive_deletion()

    assert f1.exists()
    assert not f2.exists()

    out = capsys.readouterr().out
    assert "Deleted:" in out


def test_min_size_filter(tmp_path):
    small = tmp_path / "small.txt"
    large1 = tmp_path / "file1.txt"
    large2 = tmp_path / "file2.txt"
    small.write_text("x")  # 1 byte
    large1.write_text("big data")
    large2.write_text("big data")

    finder = DuplicateFinder()
    finder.run(
        folder_path=tmp_path,
        min_size="5")
    assert [group for group in finder.duplicates if small.name in group] == []


def test_filter_by_max_size(tmp_path):
    small = tmp_path / "small.txt"
    small.write_bytes(b"x" * 100)  # 100 bytes

    large = tmp_path / "large.txt"
    large.write_bytes(b"x" * 10_000_000)  # 10 MB

    finder = DuplicateFinder()
    duplicates = finder.run(
        folder_path=tmp_path,
        min_size="0B",
        max_size="1M",
        dry_run=True)
    assert duplicates == []
