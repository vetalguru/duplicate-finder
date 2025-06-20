import argparse
import fnmatch
import hashlib
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from cli_args import ArgumentParserAdapter


class DuplicateFinder:
    def __init__(self,
                 folder_path: str,
                 exclude_patterns=None):
        if exclude_patterns is None:
            exclude_patterns = []
        self.folder_path = Path(folder_path).resolve()
        self.exclude_patterns = exclude_patterns
        self.files_by_size: dict[int, list[str]] = {}
        self.files_by_hash: dict[str, list[str]] = {}
        self.duplicates: list[list[str]] = []

    def run(self,
            sort_by_group: bool = False,
            sort_by_size: bool = False,
            output_path: str | None = None,
            delete: bool = False,
            dry_run: bool = False,
            delete_report: str | None = None,
            threads: int = 8) -> None:
        self._group_by_size()
        self._group_by_hash(max_workers=threads)
        self._find_duplicates(sort_by_group=sort_by_group, sort_by_size=sort_by_size)
        self._print_duplicates()

        if output_path:
            self._save_to_file(output_path)

        if delete:
            confirm = 'y'
            if not dry_run:
                confirm = input("\nAre you sure you want to delete duplicate files? (y/[n]): ").strip().lower()
            if confirm == 'y':
                self._delete_duplicates(dry_run=dry_run, report_path=delete_report)
            else:
                print("Deletion cancelled.")

    def _is_excluded(self, path: str) -> bool:
        norm_path = Path(path).as_posix()
        return any(fnmatch.fnmatch(norm_path, pattern)
                   for pattern in self.exclude_patterns)

    @staticmethod
    def _calc_file_hash(file_path: str,
                       block_size = 65536) -> str | None:
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(block_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except IOError:
            print(f"ERROR: Unable to read file: {file_path}")
            return None

    def _group_by_size(self) -> None:
        if not self.folder_path.is_dir():
            print(f"ERROR: Path '{self.folder_path}' is not a folder or doesn't exist")
            return

        print("Scanning files and grouping by size...")
        files_by_size = defaultdict(list)
        for path in self.folder_path.rglob("*"):
            if path.is_file() and not path.is_symlink():
                if self._is_excluded(str(path)):
                    continue
                try:
                    size = path.stat().st_size
                    files_by_size[size].append(str(path))
                except OSError:
                    print(f"ATTENTION: Unable to access file: {path}")
        print("Scanning finished")
        self.files_by_size = files_by_size

    def _group_by_hash(self, max_workers: int = 8) -> None:
        print("Hashing potential duplicates...")

        potential_duplicates = {size: files for size, files in self.files_by_size.items() if len(files) > 1}
        files_to_hash = [path for files in potential_duplicates.values() for path in files]
        total = len(files_to_hash)

        files_by_hash = defaultdict(list)

        def hash_worker(path):
            return path, self._calc_file_hash(path)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_path = {executor.submit(hash_worker, path): path for path in files_to_hash}
            for i, future in enumerate(as_completed(future_to_path), 1):
                print(f"\rProgress [{i}/{total}]", end="")
                try:
                    path, file_hash = future.result()
                    if file_hash:
                        files_by_hash[file_hash].append(path)
                except Exception as e:
                    print(f"\nERROR: Failed to hash {future_to_path[future]}: {e}")
        print()
        self.files_by_hash = files_by_hash

    def _find_duplicates(self, sort_by_group: bool = False, sort_by_size: bool = False) -> None:
        groups = [sorted(group) for group in self.files_by_hash.values() if len(group) > 1]
        if sort_by_group:
            groups.sort(key=len, reverse=True)
        elif sort_by_size:
            groups.sort(key=lambda g: Path(g[0]).stat().st_size, reverse=True)
        self.duplicates = groups

    @staticmethod
    def _human_readable_size(size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"

    def _print_duplicates(self) -> None:
        if not self.duplicates:
            print("No duplicates found.")
            return

        print("\nDuplicate files:")
        for idx, group in enumerate(self.duplicates, start=1):
            size = Path(group[0]).stat().st_size
            print(f"\nGroup {idx} ({len(group)} file(s), size: {self._human_readable_size(size)}):")
            for path in group:
                print(f"  - {path}")

    def _save_to_file(self, output_path: str) -> None:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("Duplicate files:\n")
                for idx, group in enumerate(self.duplicates, 1):
                    size = Path(group[0]).stat().st_size
                    f.write(f"\nGroup {idx} ({len(group)} file(s), size: {size} bytes):\n")
                    for path in group:
                        f.write(f"  - {path}\n")
            print(f"\nSaved results to: {output_path}")
        except Exception as e:
            print(f"\nERROR: Failed to save to file {output_path}: {e}")

    def _delete_duplicates(self, dry_run: bool = False, report_path: str | None = None) -> None:
        print("\n[DRY RUN]" if dry_run else "\nDeleting duplicate files...")
        deleted_count = 0
        report_lines = []

        for group in self.duplicates:
            for path in group[1:]:  # Keep just a first file in each group
                if dry_run:
                    print(f"[would delete] {path}")
                    report_lines.append(f"[would delete] {path}")
                else:
                    try:
                        Path(path).unlink()
                        print(f"Deleted: {path}")
                        report_lines.append(f"Deleted: {path}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"ERROR: Failed to delete {path}: {e}")
                        report_lines.append(f"FAILED: {path} ({e})")

        print(f"\nTotal deleted: {deleted_count}" if not dry_run else f"\nTotal possible deletions: {deleted_count}")

        if report_path:
            try:
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write("Duplicate File Deletion Report\n" + "="*36 + "\n")
                    f.writelines(line + "\n" for line in report_lines)
                print(f"Report saved to: {report_path}")
            except Exception as e:
                print(f"ERROR: Failed to save report: {e}")

def main() -> None:
    args = ArgumentParserAdapter().parse()

    finder = DuplicateFinder(args.folder_path, exclude_patterns=args.exclude)
    finder.run(
        sort_by_group=args.sort_by_group_size,
        sort_by_size=args.sort_by_file_size,
        output_path=args.output,
        delete=args.delete,
        dry_run=args.dry_run,
        delete_report=args.delete_report,
        threads=args.threads
)

if __name__ == "__main__":
    main()
