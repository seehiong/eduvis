import os
import zipfile
import shutil

def pack_eduvis():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source_dir = os.path.join(root_dir, "eduvis")
    public_dir = os.path.join(root_dir, "studio", "public")
    zip_path = os.path.join(public_dir, "eduvis.zip")

    # Create studio/public directory if it doesn't exist
    os.makedirs(public_dir, exist_ok=True)

    print(f"Archiving {source_dir} to {zip_path}...")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude pycache and build artifacts
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            if ".pytest_cache" in dirs:
                dirs.remove(".pytest_cache")

            for file in files:
                if file.endswith((".pyc", ".pyo", ".pyd")):
                    continue
                file_path = os.path.join(root, file)
                # Compute relative archive path inside the zip file
                arcname = os.path.relpath(file_path, os.path.dirname(source_dir))
                zipf.write(file_path, arcname)

    # Copy showcase reference and lesson examples into public folder
    showcase_src = os.path.join(root_dir, "showcase")
    showcase_dst = os.path.join(public_dir, "showcase")

    # Remove existing showcase folder in public if exists
    if os.path.exists(showcase_dst):
        shutil.rmtree(showcase_dst)

    print(f"Copying showcase examples from {showcase_src} to {showcase_dst}...")

    # Copy selected showcase files
    shutil.copytree(showcase_src, showcase_dst, ignore=shutil.ignore_patterns("__pycache__", "assets"))

    print("Success! EduVis Python codebase and showcase files archived for Pyodide.")

if __name__ == "__main__":
    pack_eduvis()
