import argparse
import os.path
import sys

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

    print("The path is corect")

if __name__ == "__main__":
    main()
