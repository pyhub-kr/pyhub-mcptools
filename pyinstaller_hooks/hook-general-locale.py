"""General hook to filter locale files from all packages."""

import os
from PyInstaller import compat
from PyInstaller.utils.hooks import logger

# Only keep Korean and English locales
ALLOWED_LOCALES = {'en', 'ko', 'ko-kr', 'en-us', 'en_US', 'ko_KR', 'en_GB'}

def hook(hook_api):
    """Filter out unnecessary locale files from all packages."""

    # Get all collected data files
    datas = hook_api.datas if hasattr(hook_api, 'datas') else []

    filtered_datas = []
    removed_count = 0
    removed_size = 0

    for src, dest in datas:
        # Check if this is a locale file
        if 'locale' in src and os.path.exists(src):
            parts = src.split(os.sep)

            # Try to find locale code in path
            keep = False
            for part in parts:
                if part.lower() in ALLOWED_LOCALES:
                    keep = True
                    break

            if keep:
                filtered_datas.append((src, dest))
            else:
                removed_count += 1
                try:
                    removed_size += os.path.getsize(src)
                except:
                    pass
        else:
            # Keep all non-locale files
            filtered_datas.append((src, dest))

    if removed_count > 0:
        logger.info(f"Removed {removed_count} locale files ({removed_size / 1024 / 1024:.1f} MB)")

    # Update the datas
    if hasattr(hook_api, 'datas'):
        hook_api.datas = filtered_datas