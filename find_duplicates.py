import argparse
import hashlib
import os
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


def get_groups_by_size(folder_path: str) -> dict[int, list[str]]:
    """
    Scan files and group them by using file size
    """
    if not os.path.isdir(folder_path):
        print(f"ERROR: Path '{folder_path}' is not a folder or doesn't exists")
        return {}

    files_by_size = defaultdict(list)
    print("Scanning files and grouping by size...")
    for dirpath, _, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            try:
                # Skip file links
                if not os.path.islink(file_path):
                    file_size = os.path.getsize(file_path)
                    files_by_size[file_size].append(file_path)
            except OSError:
                # File can be deleted in time of scanning
                print(f"ATTENTION: Unable to get access to the file: {file_path}")
                continue

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
        duplicates.sort(key=lambda group: os.path.getsize(group[0]), reverse=True)

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
        file_size = os.path.getsize(group[0])
        size_hr = human_readable_size(file_size)
        print(f"\nGroup {idx} ({len(group)} file(s), size: {size_hr}):")

        for path in group:
            print(f"  - {path}")

def main() -> None:
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

    args = parser.parse_args()
    path_from_user = args.folder_path
    print(f"Path to search: {path_from_user}")

    files_by_size = get_groups_by_size(path_from_user)
    files_by_hash = get_groups_with_equal_size(files_by_size)

    duplicates = get_duplicates(
        files_by_hash,
        sort_by_group=args.sort_by_group_size,
        sort_by_size=args.sort_by_file_size
    )

    print_duplicates(duplicates)

if __name__ == "__main__":
    main()
