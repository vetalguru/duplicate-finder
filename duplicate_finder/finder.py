# Copyright (c) 2025 Vitalii Shkibtan
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

import fnmatch
import hashlib
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed


class DuplicateFinder:
    def __init__(self, folder_path: str, exclude_patterns=None):
        # Initialize target folder and exclusion list
        if exclude_patterns is None:
            exclude_patterns = []
        self.folder_path = Path(folder_path).resolve()
        self.exclude_patterns = exclude_patterns
        self.files_by_size: dict[int, list[str]] = {}
        self.files_by_hash: dict[str, list[str]] = {}
        self.duplicates: list[list[str]] = []

    def run(
        self,
        sort_by_group: bool = False,
        sort_by_size: bool = False,
        output_path: str | None = None,
        delete: bool = False,
        dry_run: bool = False,
        interactive: bool = False,
        delete_report: str | None = None,
        threads: int = 8,
    ) -> list[list[str]]:
        # Perform the full duplicate detection workflow
        self._group_by_size()
        self._group_by_hash(max_workers=threads)
        self._find_duplicates(
            sort_by_group=sort_by_group,
            sort_by_size=sort_by_size)
        self._print_duplicates()

        if output_path:
            self._save_to_file(output_path)

        # Handle interactive or automatic deletion
        if interactive:
            self._interactive_deletion()
        elif delete:
            confirm = "y"
            if not dry_run:
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
                    dry_run=dry_run,
                    report_path=delete_report)
            else:
                print("Deletion cancelled.")

        return self.duplicates

    def _is_excluded(self, path: str) -> bool:
        # Check if a file path matches any exclusion pattern
        norm_path = Path(path).as_posix()
        return any(
            fnmatch.fnmatch(norm_path, pattern)
            for pattern in self.exclude_patterns
        )

    @staticmethod
    def _calc_file_hash(file_path: str, block_size=65536) -> str | None:
        # Compute SHA256 hash for a given file
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(block_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except IOError:
            print(f"ERROR: Unable to read file: {file_path}")
            return None

    def _group_by_size(self) -> None:
        # Group all files by their size
        if not self.folder_path.is_dir():
            print(
                f"ERROR: Path '{self.folder_path}'"
                f" is not a folder or doesn't exist"
            )
            return

        print("Scanning files and grouping by size...")
        files_by_size = defaultdict(list)

        files = [
            p for p in self.folder_path.rglob("*")
            if p.is_file() and not p.is_symlink()
        ]
        total = len(files)

        for i, path in enumerate(files, 1):
            if self._is_excluded(str(path)):
                continue

            try:
                size = path.stat().st_size
                files_by_size[size].append(str(path))
            except OSError:
                print(f"\nATTENTION: Unable to access file: {path}")

            print(f"\r[Size Scan] Progress [{i}/{total}]", end="")

        print("\nScanning finished")
        self.files_by_size = files_by_size

    def _group_by_hash(self, max_workers: int = 8) -> None:
        # Calculate hash for files that have the same size
        print("Hashing potential duplicates...")

        potential_duplicates = {
            size: files for size, files
            in self.files_by_size.items() if len(files) > 1
        }
        files_to_hash = [
            path for files in potential_duplicates.values() for path in files
        ]
        total = len(files_to_hash)

        files_by_hash = defaultdict(list)

        def hash_worker(path):
            return path, self._calc_file_hash(path)

        # Parallel hashing by using threads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {
                executor.submit(
                    hash_worker, path):
                        path for path in files_to_hash
            }
            for i, future in enumerate(as_completed(future_to_path), 1):
                print(f"\r[Hashing] Progress [{i}/{total}]", end="")
                try:
                    path, file_hash = future.result()
                    if file_hash:
                        files_by_hash[file_hash].append(path)
                except Exception as e:
                    print(f"\nERROR: Failed to hash"
                          f" {future_to_path[future]}: {e}")
        print()
        self.files_by_hash = files_by_hash

    def _find_duplicates(
        self, sort_by_group: bool = False, sort_by_size: bool = False
    ) -> None:
        # Group files by hash; optionally sort the result
        groups = [
            sorted(group) for group
            in self.files_by_hash.values() if len(group) > 1
        ]
        if sort_by_group:
            groups.sort(key=len, reverse=True)
        elif sort_by_size:
            groups.sort(key=lambda g: Path(g[0]).stat().st_size, reverse=True)
        self.duplicates = groups

    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        # Convert byte size into human-readable format
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def _print_duplicates(self) -> None:
        # Print found duplicates in grouped format
        if not self.duplicates:
            print("No duplicates found.")
            return

        print("\nDuplicate files:")
        for idx, group in enumerate(self.duplicates, start=1):
            size = Path(group[0]).stat().st_size
            print(
                f"\nGroup {idx} ({len(group)}"
                f" file(s), size: {self._human_readable_size(size)}):"
            )
            for path in group:
                print(f"  - {path}")

    def _save_to_file(self, output_path: str) -> None:
        # Save duplicate report to a specified file
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("Duplicate files:\n")
                for idx, group in enumerate(self.duplicates, 1):
                    size = Path(group[0]).stat().st_size
                    f.write(
                        f"\nGroup {idx} ({len(group)}"
                        f" file(s), size: {size} bytes):\n"
                    )
                    for path in group:
                        f.write(f"  - {path}\n")
            print(f"\nSaved results to: {output_path}")
        except Exception as e:
            print(f"\nERROR: Failed to save to file {output_path}: {e}")

    def _delete_duplicates(
        self, dry_run: bool = False, report_path: str | None = None
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
                except Exception:
                    file_size = 0

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
            f" size: {self._human_readable_size(total_deleted_size)}"
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

    def _interactive_deletion(self) -> None:
        # Prompt user to manually choose which files to delete in each group
        print("\nInteractive duplicate cleanup started.")
        deleted_count = 0

        for idx, group in enumerate(self.duplicates, start=1):
            print(f"\nGroup {idx} ({len(group)} files):")
            for i, path in enumerate(group):
                print(f"  [{i + 1}] {path}")

            choice = (
                input(
                    "Select files to delete (e.g., 2 3),"
                    " 'all', or press Enter to skip: "
                )
                .strip()
                .lower()
            )
            if not choice:
                continue
            if choice == "all":
                to_delete = group[1:]
            else:
                try:
                    indices = [int(x) - 1 for x in choice.split()]
                    to_delete = [group[i] for i in indices
                                 if 0 <= i < len(group)]
                except ValueError:
                    print("Invalid input. Skipping group.")
                    continue

            for path in to_delete:
                try:
                    Path(path).unlink()
                    print(f"Deleted: {path}")
                    deleted_count += 1
                except Exception as e:
                    print(f"ERROR: Could not delete {path}: {e}")

        print(f"\nTotal deleted interactively: {deleted_count}")
