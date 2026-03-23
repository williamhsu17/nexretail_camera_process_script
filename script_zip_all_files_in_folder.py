import os
import zipfile
import sys

def zip_all_folders_in_path(base_path):
    try:
        with os.scandir(base_path) as it:
            folders = [entry.name for entry in it if entry.is_dir(follow_symlinks=False)]
    except FileNotFoundError:
        print(f"Base path not found: {base_path}")
        folders = []
    print(f"Processing base path: {base_path} ... for {len(folders)} folders")
    print("Folders found:")
    for folder in folders:
        print(f"- {folder}")

    for item in folders:
        folder_path = os.path.join(base_path, item)
        zip_filename = os.path.join(base_path, f"{item}.zip")
        idx = folders.index(item) + 1
        print(f"Zipping folder ({idx}/{len(folders)}): {folder_path} -> {zip_filename}")
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(folder_path):
                for file in files:
                    abs_file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_file_path, folder_path)
                    zipf.write(abs_file_path, arcname=os.path.join(item, rel_path))

if __name__ == "__main__":
    paths = [
        "csv/新莊",
        "output/新莊",
        "csv/新竹",
        "output/新竹",
        "csv/西台南",
        "output/西台南",
        # "csv/鳳山",
        # "output/鳳山",
        # "csv/中台中",
        # "output/中台中",
        "csv/新店",
        "output/新店",
    ]
    for path in paths:
        zip_all_folders_in_path(path)