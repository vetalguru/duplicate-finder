# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License. See LICENSE file in the project root for full license text.


import subprocess
import sys
from pathlib import Path
import tempfile
import shutil
import pytest


def create_file(path: Path, content="data"):
    path.write_text(content)
    return str(path)


def run_cli(*args, input_text=None):
    result = subprocess.run(
        [sys.executable, "-m", "duplicate_finder", *args],
        capture_output=True,
        input=input_text,
        text=True,
    )
    return result


def test_help_shows_usage():
    result = run_cli("--help")
    assert result.returncode == 0
    assert "usage" in result.stdout.lower()


def test_find_duplicates_in_cli(tmp_path):
    f1 = create_file(tmp_path / "a.txt", "dupe")
    f2 = create_file(tmp_path / "b.txt", "dupe")

    result = run_cli(str(tmp_path))
    assert result.returncode == 0
    assert "Duplicate files" in result.stdout


def test_dry_run_output(tmp_path):
    create_file(tmp_path / "x1.txt", "dupe")
    create_file(tmp_path / "x2.txt", "dupe")

    result = run_cli(str(tmp_path), "--delete", "--dry-run")
    assert result.returncode == 0
    assert "[would delete]" in result.stdout


def test_output_report(tmp_path):
    file1 = create_file(tmp_path / "a.txt", "abc")
    file2 = create_file(tmp_path / "b.txt", "abc")
    report = tmp_path / "report.txt"

    result = run_cli(str(tmp_path), "--output", str(report))
    assert result.returncode == 0
    assert report.exists()
    assert str(file1) in report.read_text()


def test_exclude_via_cli(tmp_path):
    create_file(tmp_path / "keep.txt", "abc")
    create_file(tmp_path / "skip.log", "abc")

    result = run_cli(str(tmp_path), "--exclude", "*.log")
    assert result.returncode == 0
    assert "Duplicate files" not in result.stdout
