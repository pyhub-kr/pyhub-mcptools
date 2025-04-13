from pathlib import Path

from environ import Env

from pyhub.mcptools.core.utils import (
    get_current_language_code,
    get_current_timezone,
    get_databases,
    make_filecache_setting,
)

env = Env()

if "ENV_PATH" in env:
    env_path = env.path("ENV_PATH")
    env.read_env(env_path, overwrite=True)


# ASGI_APPLICATION = "pyhub.mcptools.core.asgi.application"
ROOT_URLCONF = "pyhub.mcptools.urls"

HOME_DIR = Path.home().resolve()
PYHUB_CONFIG_DIR = HOME_DIR / ".pyhub"
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
CURRENT_DIR = Path.cwd().resolve()

DEBUG = env.bool("DEBUG", default=False)
# "BASE_DIR": ...,
SECRET_KEY = "pyhub.mcptools"

INSTALLED_APPS = [
    "pyhub.mcptools.core",
    "pyhub.mcptools.browser",
    "pyhub.mcptools.excel",
]
MIDDLEWARE = []

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {},
    }
]

CACHES = {
    "default": make_filecache_setting(
        "pyhub_mcptools_cache",
        max_entries=5_000,
        cull_frequency=5,
        timeout=86400 * 30,
    ),
    "locmem": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pyhub_locmem",
    },
    "dummy": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
}

DATABASE_ROUTERS = ["pyhub.routers.Router"]

DATABASES = get_databases(CURRENT_DIR)

# "AUTH_USER_MODEL": ...,  # TODO:

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "httpx": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
    },
}

LANGUAGE_CODE = get_current_language_code("ko-KR")
# 데이터베이스 저장 목적
TIME_ZONE = env.str("TIME_ZONE", default="UTC")
# 이를 사용하지 않고, 유저의 OS 설정을 따르기
USER_DEFAULT_TIME_ZONE = get_current_timezone()

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = env.str("STATIC_URL", default="static/")

STATIC_ROOT = env.path("STATIC_ROOT", default=PYHUB_CONFIG_DIR / "staticfiles")

STATICFILES_DIRS = []

# "STATICFILES_FINDERS": [
#     "django.contrib.staticfiles.finders.FileSystemFinder",
#     "django.contrib.staticfiles.finders.AppDirectoriesFinder",
# ],
MEDIA_URL = env.str("MEDIA_URL", default="media/")
MEDIA_ROOT = env.path("MEDIA_ROOT", default=PYHUB_CONFIG_DIR / "mediafiles")

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# pyhub.mcptools

EXPERIMENTAL = env.bool("PYHUB_MCPTOOLS_EXPERIMENTAL", default=False)

# https://api.together.xyz/
TOGETHER_API_KEY = env.str("TOGETHER_API_KEY", default=None)

# https://unsplash.com/oauth/applications/
UNSPLASH_ACCESS_KEY = env.str("UNSPLASH_ACCESS_KEY", default=None)
UNSPLASH_SECRET_KEY = env.str("UNSPLASH_SECRET_KEY", default=None)
