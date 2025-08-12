# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import fnmatch
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

from duplicate_finder import utils
from duplicate_finder.duplicate_finder_config import DuplicateFinderConfig


class DuplicateFinder:
    def __init__(self) -> None:
        # Internal state for storing results
        self.duplicates: list[list[str]] = []

    def run(
        self,
        config: DuplicateFinderConfig
    ) -> list[list[str]]:
        # Clear internal state before running
        self._clear_results()

        self.cfg = config

        # Stage 1: Scan the folder and find duplicates
        print(f"Scanning folder: {self.cfg.scan_folder_path}")
        files_by_size = self._get_files_list(
            folder_path=self.cfg.scan_folder_path,
            include_patterns=self.cfg.include_patterns,
            exclude_patterns=self.cfg.exclude_patterns,
            min_size=self.cfg.min_file_size,
            max_size=self.cfg.max_file_size)
        if not files_by_size:
            print("No files found or all files are excluded.")
            return self.duplicates

        # Remove single files from the list, as they cannot be duplicates
        grouped_files = self._remove_single_files_from_file_list(
            files_list=files_by_size)
        files_by_size.clear()
        if not grouped_files:
            print("No potential duplicates found after filtering by size.")
            return self.duplicates

        # Stage 2: Hash files that have the same size
        files_by_hash = self._group_files_by_hash(
            files_by_size=grouped_files,
            max_workers=self.cfg.threads_count)
        grouped_files.clear()
        if not files_by_hash:
            print("No potential duplicates found after hashing.")
            return self.duplicates

        # Stage 3: Sort duplicates and print them
        # Verify duplicates by comparing file contents
        if self.cfg.verify_content:
            files_by_hash = (
                self._verify_content(files_by_hash))

        # Group files into duplicate groups
        self.duplicates = (
            self._group_duplicates(
                files_by_hash,
                sort_by_group=self.cfg.sort_by_group_size,
                sort_by_size=self.cfg.sort_by_file_size))
        # Clear file groups to free memory
        files_by_hash.clear()  # Free space

        if not self.duplicates:
            return self.duplicates

        # Print found duplicates to console
        self._print_duplicates(self.duplicates)

        # Save duplicates to output report if requested
        if self.cfg.output_file_path:
            self._save_report_to_file(
                self.duplicates, self.cfg.output_file_path)

        # Stage 4: Handle deletion if requested
        # Handle interactive or automatic deletion
        if self.cfg.interactive_mode:
            self._delete_duplicates_interactive(
                duplicates=self.duplicates,
                report_path=self.cfg.delete_report_file_path)
        elif self.cfg.delete_duplicates:
            confirm = "y"
            if not self.cfg.dry_run:
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
                    self.duplicates,
                    dry_run=self.cfg.dry_run,
                    report_path=self.cfg.delete_report_file_path)
            else:
                print("Deletion cancelled.")

        return self.duplicates

    def _clear_results(self) -> None:
        # Clear all previous results
        self.duplicates.clear()

    @staticmethod
    def _get_files_list(
        folder_path: str,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        min_size: int | None = None,
        max_size: int | None = None
    ) -> dict[int, list[str]]:
        # Group all files by their size
        input_path = Path(folder_path).expanduser().resolve()
        if not input_path.is_dir():
            print(f"ERROR: Path '{input_path}'"
                  f" is not a folder or doesn't exist")
            return {}

        print("Filtering files...")
        files = defaultdict(list)
        processed = 0
        selected = 0

        for p in input_path.rglob("*"):
            try:
                if p.is_file() and not p.is_symlink():
                    processed += 1
                    print(f"\r[Size Scan] Progress [{processed}]",
                          end="")

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

                    files[size].append(str(p))
                    selected += 1
            except (OSError, PermissionError) as e:
                print(f"\nATTENTION: Skipping {p} due to access error: {e}")

        print(f"\nScanning finished. Selected {selected}"
              f" files from {processed}.")
        print(f"Found {len(files)} unique file sizes.")
        return files

    @staticmethod
    def _remove_single_files_from_file_list(
        files_list: dict[int, list[str]],
    ) -> dict[int, list[str]]:
        # Filter files by size to find potential duplicates
        if not files_list:
            print("No files found, skipping duplicate search.")
            return {}

        result = {}
        print("Grouping files by size...")
        for i, (size, files) in enumerate(files_list.items(), 1):
            if len(files) > 1:
                result[size] = files
            print(f"\r[Grouping] Progress [{i}/{len(files_list)}]",
                  end="",
                  file=sys.stdout,
                  flush=True)
        print()
        print(f"Found {len(result)} potential duplicate groups ")
        return result

    @staticmethod
    def _group_files_by_hash(files_by_size: dict[int, list[str]],
                             max_workers: int = 8) -> dict[str, list[str]]:
        if not files_by_size:
            print("No files to hash, skipping hashing step.")
            return {}

        # Calculate hash for files that have the same size
        print("Hashing potential duplicates...")

        files_to_hash = [
            path for files in files_by_size.values() for path in files
        ]
        total = len(files_to_hash)

        files_by_hash = defaultdict(list)
        lock = Lock()

        def hash_worker(path: str) -> tuple[str, str]:
            return path, utils.calc_file_sha256(path)

        # Parallel hashing by using threads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(hash_worker,
                                path): path for path in files_to_hash
            }
            for i, future in enumerate(as_completed(future_to_path), 1):
                print(f"\r[Hashing] Progress [{i}/{total}]",
                      end="",
                      file=sys.stdout,
                      flush=True)
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
    def _group_duplicates(files: dict[str, list[str]],
                          sort_by_group: bool = False,
                          sort_by_size: bool = False
                          ) -> list[list[str]]:
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
    def _print_duplicates(duplicates: list[list[str]]) -> None:
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
    def _save_report_to_file(duplicates: list[list[str]],
                             output_report_path: str
                             ) -> None:
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

    @staticmethod
    def _delete_duplicates(duplicates: list[list[str]],
                           dry_run: bool = False,
                           report_path: str | None = None
                           ) -> None:
        # Delete all duplicates (keeping first file
        # in each group), optionally save report
        print("\n[DRY RUN]" if dry_run else "\nDeleting duplicate files...")
        deleted_count = 0
        report_lines = []
        total_deleted_size = 0
        for group in duplicates:
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

    @staticmethod
    def _delete_duplicates_interactive(duplicates: list[list[str]],
                                       report_path: str | None = None
                                       ) -> None:
        # Prompt user to choose which file to keep in each group
        print("\nInteractive duplicate cleanup started.")
        deleted_count = 0
        total_deleted_size = 0
        report_lines = []
        total_groups = len(duplicates)

        for idx, group in enumerate(duplicates, start=1):
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
    def _verify_content(file_groups: dict[str, list[str]]
                        ) -> dict[str, list[str]]:
        verified = defaultdict(list)
        total_comparisons = sum(
            len(group) * (len(group) - 1) // 2
            for group in file_groups.values()
            if len(group) > 1
        )

        print("Verifying content of potential duplicates...")

        completed = 0
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
