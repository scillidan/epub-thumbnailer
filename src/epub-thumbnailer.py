#!/usr/bin/env python3

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Author: Mariano Simone (http://marianosimone.com)
# Version: 1.1
# Name: epub-thumbnailer
# Description: An implementation of a cover thumbnailer for epub files
# Installation: see README

import os
import re
import sys
from io import BytesIO
from xml.dom import minidom

try:
    from urllib.request import urlopen
except ImportError:
    from urllib import urlopen

import zipfile
from PIL import Image

# 设置标准输出编码为UTF-8
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

img_ext_regex = re.compile(r'^.*\.(jpg|jpeg|png)$', flags=re.IGNORECASE)
cover_regex = re.compile(r'.*cover.*\.(jpg|jpeg|png)', flags=re.IGNORECASE)

def normalize_path(path):
    return path.replace('\\', '/').replace('//', '/')

def get_cover_from_manifest(epub):
    try:
        rootfile_path, rootfile_root = _get_rootfile_root(epub)
        cover_id = None
        for meta in rootfile_root.getElementsByTagName("meta"):
            if meta.getAttribute("name") == "cover":
                cover_id = meta.getAttribute("content")
                break

        manifest = rootfile_root.getElementsByTagName("manifest")[0]
        for item in manifest.getElementsByTagName("item"):
            item_id = item.getAttribute("id")
            item_properties = item.getAttribute("properties")
            item_href = item.getAttribute("href")
            item_href_is_image = img_ext_regex.match(item_href.lower())
            item_id_might_be_cover = item_id == cover_id or ('cover' in item_id and item_href_is_image)
            item_properties_might_be_cover = item_properties == cover_id or ('cover' in item_properties and item_href_is_image)
            if item_id_might_be_cover or item_properties_might_be_cover:
                cover_path = os.path.join(os.path.dirname(rootfile_path), item_href)
                cover_path = normalize_path(cover_path)
                return cover_path
    except Exception as e:
        print(f"  Manifest error: {e}")
    return None

def get_cover_by_guide(epub):
    try:
        rootfile_path, rootfile_root = _get_rootfile_root(epub)
        for ref in rootfile_root.getElementsByTagName("reference"):
            if ref.getAttribute("type") == "cover":
                cover_href = ref.getAttribute("href")
                cover_file_path = os.path.join(os.path.dirname(rootfile_path), cover_href)
                cover_file_path = normalize_path(cover_file_path)
                try:
                    cover_file = epub.open(cover_file_path)
                    cover_dom = minidom.parseString(cover_file.read())
                    imgs = cover_dom.getElementsByTagName("img")
                    if imgs:
                        img = imgs[0]
                        img_path = img.getAttribute("src")
                        full_img_path = os.path.join(os.path.dirname(cover_file_path), img_path)
                        full_img_path = normalize_path(full_img_path)
                        return full_img_path
                except Exception:
                    return None
    except Exception as e:
        print(f"  Guide error: {e}")
    return None

def _get_rootfile_root(epub):
    container = epub.open("META-INF/container.xml")
    container_root = minidom.parseString(container.read())
    elem = container_root.getElementsByTagName("rootfile")[0]
    rootfile_path = elem.getAttribute("full-path")
    rootfile = epub.open(rootfile_path)
    return rootfile_path, minidom.parseString(rootfile.read())

def get_cover_by_filename(epub):
    try:
        no_matching_images = []
        for fileinfo in epub.filelist:
            filename = fileinfo.filename
            if cover_regex.match(filename):
                print(f"  Found cover by filename: {filename}")
                return filename
            if img_ext_regex.match(filename):
                no_matching_images.append(fileinfo)
        
        if no_matching_images:
            best_image = max(no_matching_images, key=lambda f: f.file_size)
            print(f"  Using largest image: {best_image.filename}")
            return best_image.filename
    except Exception as e:
        print(f"  Filename search error: {e}")
    return None

def extract_cover(epub, cover_path):
    if cover_path:
        try:
            print(f"  Attempting to extract: {cover_path}")
            cover = epub.open(cover_path)
            im = Image.open(BytesIO(cover.read()))
            im.thumbnail((size, size), Image.LANCZOS)
            if im.mode == "CMYK":
                im = im.convert("RGB")
            im.save(output_file, "PNG")
            return True
        except Exception as e:
            print(f"  Extraction error: {e}")
    return False

def find_any_image(epub):
    for fileinfo in epub.filelist:
        if img_ext_regex.match(fileinfo.filename):
            print(f"  Fallback: using {fileinfo.filename}")
            return fileinfo.filename
    return None

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: epub-thumbnailer <epub_file> <output_file> <size>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    size = int(sys.argv[3])

    print(f"Processing: {input_file}")
    print(f"Output: {output_file}")
    print(f"Size: {size}px")

    try:
        if os.path.isfile(input_file):
            file_url = open(input_file, "rb")
        else:
            file_url = urlopen(input_file)

        epub = zipfile.ZipFile(BytesIO(file_url.read()), "r")
    except Exception as e:
        print(f"Error opening EPUB file: {e}")
        sys.exit(1)

    extraction_strategies = [
        ("Manifest-based search", get_cover_from_manifest),
        ("Guide-based search", get_cover_by_guide),
        ("Filename search", get_cover_by_filename)
    ]

    cover_found = False
    for strategy_name, strategy_func in extraction_strategies:
        print(f"Trying {strategy_name}...")
        try:
            cover_path = strategy_func(epub)
            if cover_path:
                print(f"  Found potential cover: {cover_path}")
                if extract_cover(epub, cover_path):
                    print("Successfully created thumbnail: " + output_file)
                    cover_found = True
                    break
                else:
                    print(f"  Extraction failed for: {cover_path}")
            else:
                print(f"  No cover found using {strategy_name}")
        except Exception as ex:
            print(f"  Error in {strategy_name}: {ex}")

    if not cover_found:
        print("Trying fallback: any image file")
        try:
            cover_path = find_any_image(epub)
            if cover_path and extract_cover(epub, cover_path):
                print("Successfully created thumbnail using fallback: " + output_file)
                cover_found = True
        except Exception as ex:
            print(f"  Fallback error: {ex}")

    if not cover_found:
        print("Could not find or extract any cover image from the EPUB")
        sys.exit(1)
    else:
        sys.exit(0)