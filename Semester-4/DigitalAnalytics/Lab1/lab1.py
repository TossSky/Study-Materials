import argparse
import os
import shutil


def _validate_path(path, name="Path"):
    if path is None:
        raise ValueError(f"{name} cannot be None")
    if not isinstance(path, str):
        raise ValueError(f"{name} must be a string")
    if path.strip() == "":
        raise ValueError(f"{name} cannot be empty")


def f_create(path):
    try:
        _validate_path(path)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            pass
        print(f"[+] File created successfully: {path}")
    except ValueError as e:
        print(f"[-] Invalid argument. {e}")
        raise
    except IsADirectoryError as e:
        print(f"[-] Path '{path}' is a directory, not a file. {e}")
        raise
    except OSError as e:
        print(f"[-] Invalid path '{path}'. {e}")
        raise
    except Exception as e:
        print(f"[-] Unexpected error for '{path}'. {e}")
        raise


def f_delete(path):
    try:
        _validate_path(path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File '{path}' not found")
        if os.path.isdir(path):
            raise IsADirectoryError(f"Path '{path}' is a directory, not a file")
        os.remove(path)
        print(f"[+] File deleted successfully: {path}")
    except ValueError as e:
        print(f"[-] Invalid argument. {e}")
        raise
    except FileNotFoundError as e:
        print(f"[-] File '{path}' not found. {e}")
        raise
    except IsADirectoryError as e:
        print(f"[-] Path '{path}' is a directory, not a file. {e}")
        raise
    except PermissionError as e:
        print(f"[-] Permission denied for '{path}'. {e}")
        raise
    except OSError as e:
        print(f"[-] Error deleting file '{path}'. {e}")
        raise
    except Exception as e:
        print(f"[-] Unexpected error for '{path}'. {e}")
        raise


def f_write(path, content):
    try:
        _validate_path(path)
        if content is None:
            raise ValueError("Content cannot be None")
        if os.path.isdir(path):
            raise IsADirectoryError(f"Path '{path}' is a directory, not a file")
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[+] Content written successfully to: {path}")
    except ValueError as e:
        print(f"[-] Invalid argument. {e}")
        raise
    except IsADirectoryError as e:
        print(f"[-] Path '{path}' is a directory, not a file. {e}")
        raise
    except PermissionError as e:
        print(f"[-] Permission denied for '{path}'. {e}")
        raise
    except UnicodeEncodeError as e:
        print(f"[-] Encoding error writing to '{path}'. {e}")
        raise
    except OSError as e:
        print(f"[-] Error writing to file '{path}'. {e}")
        raise
    except Exception as e:
        print(f"[-] Unexpected error for '{path}'. {e}")
        raise


def f_read(path):
    try:
        _validate_path(path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"File '{path}' not found")
        if os.path.isdir(path):
            raise IsADirectoryError(f"Path '{path}' is a directory, not a file")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"[+] File read successfully: {path}")
        print(content)
        return content
    except ValueError as e:
        print(f"[-] Invalid argument. {e}")
        raise
    except FileNotFoundError as e:
        print(f"[-] File '{path}' not found. {e}")
        raise
    except IsADirectoryError as e:
        print(f"[-] Path '{path}' is a directory, not a file. {e}")
        raise
    except PermissionError as e:
        print(f"[-] Permission denied for '{path}'. {e}")
        raise
    except OSError as e:
        print(f"[-] Error reading file '{path}'. {e}")
        raise
    except Exception as e:
        print(f"[-] Unexpected error for '{path}'. {e}")
        raise


def f_copy(src, dest):
    try:
        _validate_path(src, "Source path")
        _validate_path(dest, "Destination path")
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source file '{src}' not found")
        if os.path.isdir(src):
            raise IsADirectoryError(f"Source path '{src}' is a directory, not a file")
        if os.path.isdir(dest):
            raise IsADirectoryError(f"Destination path '{dest}' is a directory, not a file")
        parent = os.path.dirname(dest)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.copy2(src, dest)
        print(f"[+] File copied successfully from '{src}' to '{dest}'")
    except ValueError as e:
        print(f"[-] Invalid argument. {e}")
        raise
    except FileNotFoundError as e:
        print(f"[-] Source file '{src}' not found. {e}")
        raise
    except IsADirectoryError as e:
        print(f"[-] Source path '{src}' is a directory, not a file. {e}")
        raise
    except PermissionError as e:
        print(f"[-] Permission denied. {e}")
        raise
    except OSError as e:
        print(f"[-] Error copying file from '{src}' to '{dest}'. {e}")
        raise
    except Exception as e:
        print(f"[-] Unexpected error for '{src}'. {e}")
        raise


def f_rename(src, dest):
    try:
        _validate_path(src, "Source path")
        _validate_path(dest, "Destination path")
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source file '{src}' not found")
        if os.path.isdir(src):
            raise IsADirectoryError(f"Source path '{src}' is a directory, not a file")
        if os.path.isdir(dest):
            raise IsADirectoryError(f"Destination path '{dest}' is a directory, not a file")
        parent = os.path.dirname(dest)
        if parent:
            os.makedirs(parent, exist_ok=True)
        os.rename(src, dest)
        print(f"[+] File renamed successfully from '{src}' to '{dest}'")
    except ValueError as e:
        print(f"[-] Invalid argument. {e}")
        raise
    except FileNotFoundError as e:
        print(f"[-] Source file '{src}' not found. {e}")
        raise
    except IsADirectoryError as e:
        print(f"[-] Source path '{src}' is a directory, not a file. {e}")
        raise
    except PermissionError as e:
        print(f"[-] Permission denied. {e}")
        raise
    except OSError as e:
        print(f"[-] Error renaming file from '{src}' to '{dest}'. {e}")
        raise
    except Exception as e:
        print(f"[-] Unexpected error for '{src}'. {e}")
        raise


def main():
    parser = argparse.ArgumentParser(description="CLI application for file system management")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create
    create_parser = subparsers.add_parser("create", help="Create a new file")
    create_parser.add_argument("path", type=str, help="Path to the file to create")

    # delete
    delete_parser = subparsers.add_parser("delete", help="Delete a file")
    delete_parser.add_argument("path", type=str, help="Path to the file to delete")

    # write
    write_parser = subparsers.add_parser("write", help="Write content to a file")
    write_parser.add_argument("path", type=str, help="Path to the target file")
    write_parser.add_argument("content", type=str, help="Content to write to the file")

    # read
    read_parser = subparsers.add_parser("read", help="Read content from a file")
    read_parser.add_argument("path", type=str, help="Path to the target file")

    # copy
    copy_parser = subparsers.add_parser("copy", help="Copy a file")
    copy_parser.add_argument("src", type=str, help="Path to the source file")
    copy_parser.add_argument("dest", type=str, help="Path to the destination")

    # rename
    rename_parser = subparsers.add_parser("rename", help="Rename a file")
    rename_parser.add_argument("src", type=str, help="Path to the source file")
    rename_parser.add_argument("dest", type=str, help="New full path for the file")

    args = parser.parse_args()

    if args.command == "create":
        f_create(args.path)
    elif args.command == "delete":
        f_delete(args.path)
    elif args.command == "write":
        f_write(args.path, args.content)
    elif args.command == "read":
        f_read(args.path)
    elif args.command == "copy":
        f_copy(args.src, args.dest)
    elif args.command == "rename":
        f_rename(args.src, args.dest)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
