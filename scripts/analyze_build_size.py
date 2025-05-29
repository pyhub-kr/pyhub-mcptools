#!/usr/bin/env python3
"""Analyze build size and identify large files/directories."""

import os
import sys
from pathlib import Path
from collections import defaultdict

def get_size(path):
    """Get size of file or directory in bytes."""
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total += os.path.getsize(filepath)
            except:
                pass
    return total

def format_size(size):
    """Format size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"

def analyze_directory(directory):
    """Analyze directory and report sizes."""
    print(f"\nAnalyzing: {directory}")
    print("=" * 80)

    # Analyze by file type
    extensions = defaultdict(lambda: {'count': 0, 'size': 0})
    locale_size = 0
    locale_count = 0

    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                size = os.path.getsize(filepath)
                ext = Path(file).suffix.lower() or 'no_ext'
                extensions[ext]['count'] += 1
                extensions[ext]['size'] += size

                # Check if it's a locale file
                if 'locale' in filepath:
                    locale_size += size
                    locale_count += 1
            except:
                pass

    # Report findings
    total_size = get_size(directory)
    print(f"Total size: {format_size(total_size)}")
    print(f"\nLocale files: {locale_count} files, {format_size(locale_size)} ({locale_size/total_size*100:.1f}%)")

    print("\nTop 10 file types by size:")
    sorted_exts = sorted(extensions.items(), key=lambda x: x[1]['size'], reverse=True)[:10]
    for ext, data in sorted_exts:
        percent = data['size'] / total_size * 100
        print(f"  {ext:10} {data['count']:5} files  {format_size(data['size']):>10}  ({percent:5.1f}%)")

    # Find largest directories
    print("\nTop 10 largest directories:")
    dir_sizes = []
    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            dirpath = os.path.join(root, dir)
            size = get_size(dirpath)
            dir_sizes.append((dirpath, size))

    dir_sizes.sort(key=lambda x: x[1], reverse=True)
    for dirpath, size in dir_sizes[:10]:
        rel_path = os.path.relpath(dirpath, directory)
        percent = size / total_size * 100
        print(f"  {rel_path[:50]:50} {format_size(size):>10}  ({percent:5.1f}%)")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = "dist/pyhub.mcptools"

    if os.path.exists(directory):
        analyze_directory(directory)
    else:
        print(f"Directory not found: {directory}")
        print("Usage: python analyze_build_size.py [directory]")