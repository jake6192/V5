import os
import zipfile
from datetime import datetime
import sys

def get_zip_name():
    now = datetime.now()
    return f"app_v{now.strftime('%d%m%H%M')}.zip"

def should_exclude(rel_path, script_name):
    excluded_dirs = {'.git', 'venv'}
    excluded_files = {'.gitignore', '.gitattributes', 'todo.txt', script_name}
    parts = rel_path.split(os.sep)

    # Exclude directory if any part of path is in excluded_dirs
    if any(part in excluded_dirs for part in parts):
        return True

    filename = os.path.basename(rel_path)
    if filename in excluded_files:
        return True
    if filename.endswith('.zip'):
        return True

    return False

def zip_directory(base_path, zip_path, script_name):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for foldername, _, filenames in os.walk(base_path):
            for filename in filenames:
                full_path = os.path.join(foldername, filename)
                rel_path = os.path.relpath(full_path, base_path)

                if should_exclude(rel_path, script_name):
                    continue

                zipf.write(full_path, arcname=rel_path)

if __name__ == '__main__':
    script_name = os.path.basename(__file__)
    zip_name = get_zip_name()
    zip_directory(os.getcwd(), zip_name, script_name)
    print(f"\n✅ Created ZIP: {zip_name}")
