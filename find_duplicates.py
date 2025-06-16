import argparse
import hashlib
import os
import sys

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

def main() -> None:
    parser = argparse.ArgumentParser(
        description = "Script to find and delete duplicates of the files"
    )

    parser.add_argument(
        "folder_path",
        type = str,
        help="Mandatory parameter: path to folder for search"
    )

    args = parser.parse_args()
    path_from_user = args.folder_path
    print(f"Path to search: {path_from_user}")
    if not os.path.isdir(path_from_user):
        print(f"ERROR: the path '{path_from_user}' is no a directory or doesn't exists", file=sys.stderr)
        sys.exit(1)

    print("The path is correct")

    test_file =os.path.join(path_from_user, "test_file.txt")
    file_hash = calc_file_hash(test_file)
    if not file_hash:
        print(f"Error: unable to calculate hash for file: {test_file}")
        sys.exit(1)

    print(f"File hash: {file_hash}")

if __name__ == "__main__":
    main()
