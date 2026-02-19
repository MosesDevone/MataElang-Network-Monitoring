import os
import shutil
import glob
import sys

def create_release():
    print("Creating MataElang OS Release Distribution...")
    
    # Define paths
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    release_dir = os.path.join(project_root, "release")
    frontend_build_dir = os.path.join(project_root, "frontend", "build")

    # 1. Create/Clean Release Directory (Preserve .git)
    if not os.path.exists(release_dir):
        os.makedirs(release_dir)
        print(f"   Created release directory: {release_dir}")
    else:
        print(f"   Cleaning existing release directory (preserving .git): {release_dir}")
        for item in os.listdir(release_dir):
            if item == ".git":
                continue
            item_path = os.path.join(release_dir, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"      [!] Failed to delete {item}: {e}")

    # 2. Copy Key Files
    files_to_copy = [
        ("run_dist.py", "run_matel.py"),
        (".env.example", ".env.example"),
        ("requirements.txt", "requirements.txt"),
    ]

    for src_name, dest_name in files_to_copy:
        src_path = os.path.join(backend_dir, src_name)
        dest_path = os.path.join(release_dir, dest_name)
        if os.path.exists(src_path):
            shutil.copy2(src_path, dest_path)
            print(f"   Copied {src_name} -> {dest_name}")
        else:
            print(f"   ⚠️ Warning: {src_name} not found!")

    # 3. Copy Compiled Binaries (.pyd / .so)
    # We look for .pyd (Windows) and .so (Linux/Mac)
    extensions = ["*.pyd", "*.so"]
    binary_files = []
    for ext in extensions:
        binary_files.extend(glob.glob(os.path.join(backend_dir, ext)))
    
    count_binaries = 0
    for binary in binary_files:
        # Exclude build scripts if they happen to be compiled (unlikely but safe)
        if "build_cython" in binary or "create_release" in binary:
            continue
            
        filename = os.path.basename(binary)
        shutil.copy2(binary, os.path.join(release_dir, filename))
        count_binaries += 1
    
    print(f"   Copied {count_binaries} compiled binary modules.")

    # FALLBACK: If no binaries were found, copy source .py files instead.
    # This ensures a release is created even without a C++ compiler.
    if count_binaries == 0:
        print("   [!] No compiled binaries found. Falling back to source distribution (.py source files).")
        source_files = glob.glob(os.path.join(backend_dir, "*.py"))
        for src_file in source_files:
            filename = os.path.basename(src_file)
            if filename in ["build_cython.py", "create_release.py", "run_dist.py"]:
                 continue
            shutil.copy2(src_file, os.path.join(release_dir, filename))
            print(f"      Copied source: {filename}")

    # 4. Copy Frontend Build
    dest_static = os.path.join(release_dir, "static")
    if os.path.exists(frontend_build_dir):
        shutil.copytree(frontend_build_dir, dest_static)
        print(f"   Copied Frontend build to {dest_static}")
    else:
        print(f"   [!] Warning: Frontend build not found at {frontend_build_dir}")
        print("      Make sure you ran 'npm run build' in the frontend directory first.")
        os.makedirs(dest_static) # Create empty just in case

    # 5. Create a Default Database (Optional)
    # open(os.path.join(release_dir, "matel.db"), 'a').close()
    
    print("\n[+] Release creation successful!")
    print(f"   Your distribution is ready at: {release_dir}")
    print("   Zip this folder and send it to your users.")

if __name__ == "__main__":
    create_release()
