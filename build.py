#!/usr/bin/env python3
import os
import shutil
import subprocess
import sys

def build_final():
    # Clean previous builds
    for folder in ['dist', 'build']:
        if os.path.exists(folder):
            shutil.rmtree(folder)

    print("Building final version...")

    # Build command
    cmd = [
        'pyinstaller',
        'src/epub-thumbnailer.py',
        '--onefile',
        '--name=epub-thumbnailer',
        '--console',
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=PIL.ImageFile',
        '--hidden-import=PIL._imaging',
        '--hidden-import=xml.dom.minidom',
        '--hidden-import=zipfile',
        '--collect-all=PIL',
        '--clean'
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✓ Build successful!")
        return True
    else:
        print("✗ Build failed!")
        print("STDERR:", result.stderr)
        return False

if __name__ == '__main__':
    if build_final():
        print("\nTest the executable with:")
        print('dist\\epub-thumbnailer.exe "file.epub" cover.png 256')
    else:
        sys.exit(1)