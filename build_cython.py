from setuptools import setup
from Cython.Build import cythonize
import os
import glob
import sys
import shutil

# Files to compile
# We compile all .py files in the current directory except build scripts and launchers
exclude = ["build_cython.py", "run_dist.py", "setup.py"]
files = [f for f in glob.glob("*.py") if f not in exclude]

print(f"Compiling the following files using Cython: {files}")

# Default to build_ext --inplace if no args given
if len(sys.argv) < 2:
    sys.argv.append("build_ext")
    sys.argv.append("--inplace")

try:
    setup(
        name="MataElang OS Backend",
        ext_modules=cythonize(files, compiler_directives={'language_level': "3"}),
    )
    print("Compilation successful!")
    
except Exception as e:
    print(f"Compilation failed: {e}")
    print("Ensure you have 'Microsoft Visual C++ Build Tools' installed.")
