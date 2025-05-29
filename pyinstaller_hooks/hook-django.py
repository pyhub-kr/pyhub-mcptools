"""PyInstaller hook for Django to exclude unnecessary locale files."""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import os

# Collect Django submodules
hiddenimports = collect_submodules('django')

# Collect data files but filter out unnecessary locale files
datas = []
ALLOWED_LOCALES = {'en', 'ko', 'ko-kr', 'en-us', 'en_US', 'ko_KR'}  # Only keep English and Korean

# Get Django's locale data
django_datas = collect_data_files('django')

for src, dest in django_datas:
    # Check if this is a locale file
    if 'locale' in src:
        # Extract locale code from path
        parts = src.split(os.sep)
        if 'locale' in parts:
            locale_idx = parts.index('locale')
            if locale_idx + 1 < len(parts):
                locale_code = parts[locale_idx + 1]
                # Only include allowed locales
                if locale_code.lower() in ALLOWED_LOCALES:
                    datas.append((src, dest))
    else:
        # Include all non-locale files
        datas.append((src, dest))

# Also handle Django's contrib apps
for app in ['admin', 'auth', 'contenttypes', 'sessions', 'messages', 'staticfiles']:
    app_datas = collect_data_files(f'django.contrib.{app}')
    for src, dest in app_datas:
        if 'locale' in src:
            parts = src.split(os.sep)
            if 'locale' in parts:
                locale_idx = parts.index('locale')
                if locale_idx + 1 < len(parts):
                    locale_code = parts[locale_idx + 1]
                    if locale_code.lower() in ALLOWED_LOCALES:
                        datas.append((src, dest))
        else:
            datas.append((src, dest))
