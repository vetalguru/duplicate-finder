# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import fnmatch
import os
import re
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from duplicate_finder import utils as utils


class DuplicateFinder:
    def __init__(self):
        self.folder_path = Path
        self.exclude_patterns = None
        self.include_patterns = None
        self.min_size = None
        self.max_size = None
        self.sort_by_group = False
        self.sort_by_size = False
        self.output_report_path = None
        self.delete = False
        self.dry_run = False
        self.interactive = False
        self.delete_report_path = None
        self.threads = None
        self.verify_content = True
        # Internal state for storing results
        self.file_groups: dict[int, list[Path]] = {}
        self.duplicates: list[list[Path]] = []

    def run(
        self,
        folder_path_to_scan: Path,
        exclude_patterns=None,
        include_patterns=None,
        min_file_size: str = None,
        max_file_size: str = None,
        sort_by_group: bool = False,
        sort_by_size: bool = False,
        output_report_path: Path | None = None,
        delete: bool = False,
        dry_run: bool = False,
        interactive: bool = False,
        delete_report_path: Path | None = None,
        threads: int = None,
        verify_content: bool = True,
    ) -> list[list[Path]]:
        # Clear internal state before running
        self._clear_results()

        # Validate and normalize input parameters
        self.folder_path = self._normalize_folder_path(folder_path_to_scan)
        self.exclude_patterns = self._normalize_patterns(exclude_patterns)
        self.include_patterns = self._normalize_patterns(include_patterns)
        self.output_report_path = (
            self._normalize_output_report_path(output_report_path))
        self.delete_report_path = (
            self._normalize_output_report_path(delete_report_path))
        self.min_size = self._normalize_size(size=min_file_size)
        self.max_size = self._normalize_size(size=max_file_size)
        self.threads = self._normalize_threads(threads=threads)
        self.sort_by_group = sort_by_group
        self.sort_by_size = sort_by_size
        self.delete = delete
        self.dry_run = dry_run
        self.interactive = interactive
        self.verify_content = verify_content

        # Stage 1: Scan the folder and find duplicates
        print(f"Scanning folder: {self.folder_path}")
        self.file_groups = self._group_files_by_size(
            folder_path=self.folder_path,
            include_patterns=self.include_patterns,
            exclude_patterns=self.exclude_patterns,
            min_size=self.min_size,
            max_size=self.max_size,
        )
        if not self.file_groups:
            print("No files found or all files are excluded.")
            return self.duplicates

        # Stage 2: Hash files that have the same size
        self.file_groups = self._group_files_by_hash(
            files_by_size=self.file_groups, max_workers=self.threads
        )
        if not self.file_groups:
            print("No potential duplicates found after hashing.")
            return self.duplicates

        # Stage 3: Sort duplicates and print them
        self.duplicates = self._group_duplicates(self.file_groups,
            sort_by_group=self.sort_by_group, sort_by_size=self.sort_by_size
        )
        # Clear file groups to free memory
        self.file_groups.clear()

        # Stage 3.1: Verify duplicates by comparing file contents
        if self.verify_content:
            print("\nVerifying duplicates by file contents...")
            self.file_groups = (
                self._verify_content(self.file_groups))

        if not self.duplicates:
            return self.duplicates

        # Print found duplicates to console
        self._print_duplicates(self.duplicates)

        # Save duplicates to output report if requested
        if self.output_report_path:
            self._save_report_to_file(self.duplicates, self.output_report_path)

        # Stage 4: Handle deletion if requested
        # Handle interactive or automatic deletion
        if self.interactive:
            self._interactive_deletion(report_path=self.delete_report_path)
        elif self.delete:
            confirm = "y"
            if not self.dry_run:
                confirm = (
                    input(
                        "\nAre you sure you want to"
                        " delete duplicate files? (y/[n]): "
                    )
                    .strip()
                    .lower()
                )
            if confirm == "y":
                self._delete_duplicates(
                    dry_run=self.dry_run, report_path=self.delete_report_path
                )
            else:
                print("Deletion cancelled.")

        return self.duplicates

    def _clear_results(self) -> None:
        # Clear all previous results
        self.file_groups.clear()
        self.duplicates.clear()

    @staticmethod
    def _normalize_folder_path(folder_path: Path):
        if not isinstance(folder_path, Path):
            if isinstance(folder_path, str):
                folder_path = Path(folder_path)
            else:
                raise TypeError(
                    "folder_path must be a Path object, "
                    f"got {type(folder_path).__name__} instead."
                )
        folder_path = folder_path.resolve()
        if not folder_path.is_dir():
            raise ValueError(f"Provided path '{folder_path}'"
                             f" is not a directory.")
        return folder_path

    @staticmethod
    def _normalize_output_report_path(
            output_report_path: Path | None) -> Path | None:
        # Normalize output report path to a Path object
        if output_report_path is None:
            return None
        if not isinstance(output_report_path, Path):
            if isinstance(output_report_path, str):
                output_report_path = Path(output_report_path)
            else:
                raise TypeError(
                    "output_report_path must be a Path object, "
                    f"got {type(output_report_path).__name__} instead."
                )
        return output_report_path.resolve()

    @staticmethod
    def _normalize_patterns(patterns: list[str] | None) -> list[str] | None:
        # Normalize patterns list to ensure they are strings
        if patterns is None:
            return None
        if not isinstance(patterns, list):
            raise TypeError(
                "Patterns must be a list of strings, "
                f"got {type(patterns).__name__} instead."
            )
        return [pattern.strip() for pattern in patterns if pattern.strip()]

    @staticmethod
    def _normalize_size(size: str | None) -> int | None:
        # Normalize size string to an integer in bytes
        if size is None:
            return None

        # Check if the size string has a valid number format
        match = re.match(r"^\s*(\d*\.?\d*)\s*([KMGT]?I?B)?\s*$",
                         size, re.IGNORECASE)
        if not match:
            raise ValueError(
                f"Invalid size format '{size}': must contain a valid number"
            )

        number, unit = match.groups()
        if not number or number == ".":
            raise ValueError(f"Invalid number format in size '{size}'")

        try:
            return utils.str_file_size_to_int(size)
        except ValueError as e:
            raise ValueError(f"Invalid size format '{size}': {e}") from e

    @staticmethod
    def _normalize_threads(threads: int | None) -> int:
        # Normalize threads count to a reasonable value
        if threads is None or threads <= 0:
            return min(32, os.cpu_count() or 8)
        if threads > 32:
            print(
                f"WARNING: Using {threads} threads, "
                "which is more than the recommended maximum of 32."
            )
        return threads

    @staticmethod
    def _group_files_by_size(
        folder_path: Path | None = None,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
    ) -> dict[int, list[Path]]:
        # Group all files by their size
        if not folder_path.is_dir():
            print(f"ERROR: Path '{folder_path}'"
                  f" is not a folder or doesn't exist")
            return {}

        print("Counting files...")
        total = sum(
            1 for p in folder_path.rglob("*")
            if p.is_file() and not p.is_symlink()
        )
        print(f"Found {total} files.")

        print("Scanning files and grouping by size...")
        files_by_size = defaultdict(list)
        processed = 0

        for p in folder_path.rglob("*"):
            try:
                if p.is_file() and not p.is_symlink():
                    # Check file size
                    size = p.stat().st_size
                    if min_size and size < min_size:
                        continue
                    if max_size and size > max_size:
                        continue

                    # Check include patterns
                    if include_patterns:
                        if not any(
                            fnmatch.fnmatch(p.as_posix(), pattern)
                            for pattern in include_patterns
                        ):
                            continue

                    # Check exclude patterns from included files
                    if exclude_patterns:
                        if any(
                            fnmatch.fnmatch(p.as_posix(), pattern)
                            for pattern in exclude_patterns
                        ):
                            continue

                    files_by_size[size].append(p)
                    processed += 1
                    print(f"\r[Size Scan] Progress [{processed}/{total}]",
                          end="")
            except (OSError, PermissionError) as e:
                print(f"\nATTENTION: Skipping {p} due to access error: {e}")

        print(f"\nScanning finished. Processed {processed} of {total} files.")
        return files_by_size

    @staticmethod
    def _group_files_by_hash(
        files_by_size: dict[int, list[Path]], max_workers: int = 8
    ) -> dict[str, list[Path]]:
        if not files_by_size:
            print("No files to hash, skipping hashing step.")
            return {}

        # Calculate hash for files that have the same size
        print("Hashing potential duplicates...")

        potential_duplicates = {
            size: files for size, files in files_by_size.items()
            if len(files) > 1
        }
        files_to_hash = [
            path for files in potential_duplicates.values() for path in files
        ]
        total = len(files_to_hash)

        files_by_hash = defaultdict(list)
        lock = Lock()

        def hash_worker(path):
            return path, utils.calc_file_sha256(path)

        # Parallel hashing by using threads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(hash_worker,
                                path): path for path in files_to_hash
            }
            for i, future in enumerate(as_completed(future_to_path), 1):
                print(f"\r[Hashing] Progress [{i}/{total}]", end="")
                try:
                    path, file_hash = future.result()
                    if file_hash:
                        with lock:
                            files_by_hash[file_hash].append(path)
                except Exception as e:
                    print(f"\nERROR: Failed to hash" f""
                          f" {future_to_path[future]}: {e}")
        print()
        return files_by_hash

    @staticmethod
    def _group_duplicates(files: dict[str, list[Path]],
                          sort_by_group: bool = False,
                          sort_by_size: bool = False
    ) -> list[list[Path]]:
        groups = [
            sorted(group) for group
            in files.values()
            if len(group) > 1
        ]
        if sort_by_group:
            groups.sort(key=len, reverse=True)
        elif sort_by_size:
            groups.sort(key=lambda g: Path(g[0]).stat().st_size, reverse=True)
        return groups

    @staticmethod
    def _print_duplicates(duplicates: list[list[Path]]) -> None:
        # Print found duplicates in grouped format
        if not duplicates:
            print("No duplicates found.")
            return

        total_groups = len(duplicates)

        print("\nDuplicate files:")
        for idx, group in enumerate(duplicates, start=1):
            size = Path(group[0]).stat().st_size
            print(
                f"\nGroup {idx}/{total_groups} ({len(group)}"
                f" file(s), size: {utils.int_file_size_to_str(size)}):"
            )
            for path in group:
                print(f"  - {path}")

    @staticmethod
    def _save_report_to_file(duplicates: list[list[Path]],
                             output_report_path: Path) -> None:
        # Save duplicate report to a specified file
        total_groups = len(duplicates)
        try:
            with open(output_report_path, "w", encoding="utf-8") as f:
                f.write("Duplicate files:\n")
                for idx, group in enumerate(duplicates, 1):
                    size = Path(group[0]).stat().st_size
                    f.write(
                        f"\nGroup {idx}/{total_groups} ({len(group)}"
                        f" file(s), size: {size} bytes):\n"
                    )
                    for path in group:
                        f.write(f"  - {path}\n")
            print(f"\nSaved results to: {output_report_path}")
        except Exception as e:
            print(f"\nERROR: Failed to save to file {output_report_path}: {e}")

    def _delete_duplicates(
        self, dry_run: bool = False, report_path: Path | None = None
    ) -> None:
        # Delete all duplicates (keeping first file
        # in each group), optionally save report
        print("\n[DRY RUN]" if dry_run else "\nDeleting duplicate files...")
        deleted_count = 0
        report_lines = []
        total_deleted_size = 0
        for group in self.duplicates:
            for path in group[1:]:  # Keep just a first file in each group
                try:
                    file_size = Path(path).stat().st_size
                except Exception as e:
                    print(f"ERROR: Could not get size for {path}: {e}")
                    report_lines.append(f"FAILED: {path} ({e})")
                    continue

                if dry_run:
                    print(f"[would delete] {path}")
                    report_lines.append(f"[would delete] {path}")
                else:
                    try:
                        Path(path).unlink()
                        print(f"Deleted: {path}")
                        report_lines.append(f"Deleted: {path}")
                    except Exception as e:
                        print(f"ERROR: Failed to delete {path}: {e}")
                        report_lines.append(f"FAILED: {path} ({e})")
                deleted_count += 1
                total_deleted_size += file_size
        print(
            f"\nTotal"
            f" {'deleted' if not dry_run else 'possible deletions'}:"
            f" {deleted_count}"
        )

        print(
            f"Total"
            f" {'freed' if not dry_run else 'possible freed'}"
            f" ({utils.int_file_size_to_str(total_deleted_size)})"
        )

        # Write deletion report if requested
        if report_path:
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write("Duplicate File Deletion"
                            " Report\n" + "=" * 36 + "\n")
                    f.writelines(line + "\n" for line in report_lines)
                print(f"Report saved to: {report_path}")
            except Exception as e:
                print(f"ERROR: Failed to save report: {e}")

    def _interactive_deletion(self, report_path: Path | None = None) -> None:
        # Prompt user to choose which file to keep in each group
        print("\nInteractive duplicate cleanup started.")
        deleted_count = 0
        total_deleted_size = 0
        report_lines = []
        total_groups = len(self.duplicates)

        for idx, group in enumerate(self.duplicates, start=1):
            print(f"\nGroup {idx}/{total_groups} ({len(group)} files):")
            for i, path in enumerate(group):
                print(f"  [{i + 1}] {path}")

            to_delete = []

            while True:
                choice = input(
                    f"Select the file to KEEP [1–{len(group)}],"
                    f" or press Enter to skip this group: "
                ).strip()

                if not choice:
                    print("Skipped.")
                    report_lines.append(
                        f"Group {idx} skipped: " f" {[str(p) for p in group]}"
                    )
                    break
                try:
                    keep_index = int(choice) - 1
                    if not (0 <= keep_index < len(group)):
                        raise ValueError

                    to_delete = group[:keep_index] + group[keep_index + 1:]
                    break
                except ValueError:
                    print("Invalid input. Please enter a number from the list.")

            for path in to_delete:
                try:
                    try:
                        file_size = Path(path).stat().st_size
                    except Exception as e:
                        print(f"ERROR: Could not get size for {path}: {e}")
                        report_lines.append(f"FAILED: {path} ({e})")
                        continue

                    Path(path).unlink()
                    print(f"Deleted: {path}")
                    report_lines.append(f"Deleted: {path}")
                    deleted_count += 1
                    total_deleted_size += file_size
                except Exception as e:
                    print(f"ERROR: Could not delete {path}: {e}")
                    report_lines.append(f"FAILED: {path} ({e})")

        print(f"\nTotal deleted interactively: {deleted_count}")
        print(
            f"\nTotal deleted size: "
            f"{utils.int_file_size_to_str(total_deleted_size)}"
        )

        if report_path:
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write("Interactive Deletion Report\n" + "=" * 32 + "\n")
                    f.writelines(line + "\n" for line in report_lines)
                print(f"Report saved to: {report_path}")
            except Exception as e:
                print(f"ERROR: Failed to save report: {e}")

    @staticmethod
    def _verify_content(
            file_groups: dict[str, list[Path]]
    ) -> dict[str, list[Path]]:
        verified = defaultdict(list)

        total_comparisons = sum(
            len(group) * (len(group) - 1) // 2
            for group in file_groups.values()
            if len(group) > 1
        )
        completed = 0

        print("Verifying content of potential duplicates...")

        for file_hash, group in file_groups.items():
            if len(group) < 2:
                continue
            while group:
                ref = group.pop(0)
                verified[file_hash].append(ref)
                remaining = []
                for other in group:
                    try:
                        if utils.files_are_identical(ref, other):
                            verified[file_hash].append(other)
                        else:
                            remaining.append(other)
                    except Exception as e:
                        print(f"\nERROR: Failed to compare {ref}"
                              f" and {other}: {e}")
                        remaining.append(other)
                    completed += 1
                    print(f"\r[Verification]"
                          f" Progress [{completed}/{total_comparisons}]",
                          end="")
                group = remaining
        print()
        return verified
