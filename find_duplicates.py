import argparse
import fnmatch
import hashlib
from pathlib import Path
from collections import defaultdict


def calc_file_hash(file_path, block_size=65536):
    """
    Calculate SHA256 hash for file file_path
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break

                sha256.update(data)
        return sha256.hexdigest()
    except IOError:
        print(f"ERROR: Unable to read file: {file_path}")
        return None

def is_excluded(path:str, patterns: list[str]) -> bool:
    norm_path = Path(path).as_posix()
    return any(fnmatch.fnmatch(norm_path, pattern) for pattern in patterns)

def get_groups_by_size(
        folder_path: Path,
        exclude_patterns: list[str]
) -> dict[int, list[str]]:
    """
    Scan files and group them by using file size
    """
    if not folder_path.is_dir():
        print(f"ERROR: Path '{folder_path}' is not a folder or doesn't exist")
        return {}

    print("Scanning files and grouping by size...")
    files_by_size = defaultdict(list)
    for path in folder_path.rglob("*"):
        if path.is_file() and not path.is_symlink():
            if is_excluded(str(path), exclude_patterns):
                continue

            try:
                file_size = path.stat().st_size
                files_by_size[file_size].append(str(path))
            except OSError:
                print(f"ATTENTION: Unable to access file: {path}")
                continue

    print("Scanning finished")
    return files_by_size

def get_groups_with_equal_size(files_by_size: dict[int, list[str]]) -> dict[str, list[str]]:
    potential_duplicates = {size: files for size, files in files_by_size.items() if len(files) > 1}
    total_files_to_hash = sum(len(files) for files in potential_duplicates.values())

    progress_counter = 0
    files_by_hash = defaultdict(list)
    for size in potential_duplicates:
        for file_path in potential_duplicates[size]:
            progress_counter += 1
            print(f"\rComparison... [{progress_counter}/{total_files_to_hash}]", end="")

            try:
                file_hash = calc_file_hash(file_path)
                if file_hash:
                    files_by_hash[file_hash].append(file_path)
            except Exception as e:
                print(f"\nERROR: Unable to hash file {file_path}: {e}")
    print()
    return files_by_hash

def get_duplicates(
    files_by_hash: dict[str, list[str]],
    sort_by_group: bool = False,
    sort_by_size: bool = False
) -> list[list[str]]:
    duplicates = [sorted(file_list) for file_list in files_by_hash.values() if len(file_list) > 1]

    if sort_by_group:
        duplicates.sort(key=len, reverse=True)
    elif sort_by_size:
        duplicates.sort(key=lambda group: Path(group[0]).stat().st_size, reverse=True)

    return duplicates

def human_readable_size(size_bytes: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"

def print_duplicates(duplicates: list[list[str]]) -> None:
    if not duplicates:
        print("No duplicates found.")
        return

    print("\nDuplicate files:")
    for idx, group in enumerate(duplicates, start=1):
        file_size = Path(group[0]).stat().st_size
        size_hr = human_readable_size(file_size)
        print(f"\nGroup {idx} ({len(group)} file(s), size: {size_hr}):")

        for path in group:
            print(f"  - {path}")

def save_duplicates_to_file(duplicates: list[list[str]], output_path: str) -> None:
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            if not duplicates:
                return

            f.write("Duplicate files:\n")
            for idx, group in enumerate(duplicates, start=1):
                file_size = Path(group[0]).stat().st_size
                f.write(f"\nGroup {idx} ({len(group)} file(s), size: {file_size} bytes):\n")
                for path in group:
                    f.write(f"  - {path}\n")
        print(f"\nSaved results to: {output_path}")
    except Exception as e:
        print(f"\nERROR: Unable to save to file {output_path}: {e}")

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Script to find and delete duplicates of the files"
    )

    parser.add_argument(
        'folder_path',
        type=str,
        help="Mandatory parameter: path to folder for search"
    )

    sort_group = parser.add_mutually_exclusive_group()
    sort_group.add_argument(
        '--sort-by-group-size',
        action='store_true',
        help="Sort duplicate groups by number of files in group (descending)"
    )
    
    sort_group.add_argument(
        '--sort-by-file-size',
        action='store_true',
        help="Sort duplicate groups by file size (descending)"
    )

    parser.add_argument(
        '--output',
        '-o',
        type=str,
        help="Optional: path to output file (e.g., duplicates.txt)"
    )

    parser.add_argument(
        '--exclude',
        '-e',
        type = str,
        nargs = '*',
        default = [],
        help = (
            "Optional: list of exclude patterns (supports wildcards).\n"
            "Use Unix-style glob syntax:\n"
            "  *.log          — exclude all .log files\n"
            "  temp/*         — exclude files in any 'temp' subdirectory\n"
            "  **/.git/**     — exclude everything inside .git folders (recursive)\n"
            "Patterns are matched against full POSIX-style paths."
        )
    )

    return parser.parse_args()

def main() -> None:
    args = parse_arguments()
    folder_path = Path(args.folder_path).resolve()
    print(f"Path to search: {folder_path}")

    files_by_size = get_groups_by_size(folder_path, args.exclude)
    files_by_hash = get_groups_with_equal_size(files_by_size)

    duplicates = get_duplicates(
        files_by_hash,
        sort_by_group=args.sort_by_group_size,
        sort_by_size=args.sort_by_file_size
    )

    print_duplicates(duplicates)

    if args.output:
        save_duplicates_to_file(duplicates, args.output)

if __name__ == "__main__":
    main()
