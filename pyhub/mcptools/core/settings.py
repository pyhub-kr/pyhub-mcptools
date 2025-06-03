from pathlib import Path

from environ import Env
from platformdirs import (
    user_cache_path,
    user_config_path,
    user_data_path,
    user_log_path,
)

from pyhub.mcptools.core.utils import (
    get_current_language_code,
    get_current_timezone,
    get_databases,
    make_filecache_setting,
)

env = Env()


APP_NAME, APP_AUTHOR = "pyhub.mcptools", "pyhub"

# 앱 사용자 데이터 저장 경로
APP_DATA_DIR = user_data_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
# 설정 파일 저장 경로
APP_CONFIG_DIR = user_config_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
# 캐시 파일 저장 경로
APP_CACHE_DIR = user_cache_path(APP_NAME, APP_AUTHOR, ensure_exists=True)
# 유저 로그 저장 경로
APP_LOG_DIR = user_log_path(APP_NAME, APP_AUTHOR, ensure_exists=True)

# 지정 버전의 pyhub.mcptools 다운로드 경로
APP_DIR_PATH = user_data_path("pyhub.mcptools.cli", APP_AUTHOR, ensure_exists=True)

GLOBAL_ENV_FILE_PATH = APP_DATA_DIR / "global-env.json"

DEFAULT_ENV_PATH = APP_CONFIG_DIR / ".env"
if DEFAULT_ENV_PATH.is_file():
    print(f"loaded env from {DEFAULT_ENV_PATH}")
    env.read_env(DEFAULT_ENV_PATH, overwrite=True)


if "ENV_PATH" in env:
    env_path = Path(env.str("ENV_PATH")).expanduser().resolve()
    env.read_env(env_path, overwrite=True)


ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["127.0.0.1"])
ASGI_APPLICATION = "pyhub.mcptools.core.asgi.application"
ROOT_URLCONF = "pyhub.mcptools.urls"

BASE_DIR = Path(__file__).parent.parent.parent.resolve()
CURRENT_DIR = Path.cwd().resolve()

DEBUG = env.bool("DEBUG", default=False)

SECRET_KEY = env.str(
    "SECRET_KEY",
    default="QhR@6vn$L9%w8j*&TtZ5!yA#uJrH3kY^WomGqXBsVzNcE2l$ip",
)

INSTALLED_APPS = [
    "channels",
    "pyhub.mcptools.core",
    "pyhub.mcptools.browser",
    "pyhub.mcptools.microsoft.excel",
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
        location_path=APP_CACHE_DIR,
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


#
# CHANNEL_LAYER_DEFAULT_REDIS_HOST = env.str("CHANNEL_LAYER_DEFAULT_REDIS_HOST", default="127.0.0.1")
# CHANNEL_LAYER_DEFAULT_REDIS_PORT = env.int("CHANNEL_LAYER_DEFAULT_REDIS_PORT", default=None)
#
# if CHANNEL_LAYER_DEFAULT_REDIS_HOST and CHANNEL_LAYER_DEFAULT_REDIS_PORT:
#     print(f"run channel layer on {CHANNEL_LAYER_DEFAULT_REDIS_PORT}")
#     CHANNEL_LAYERS = {
#         "default": {
#             "BACKEND": "channels_redis.core.RedisChannelLayer",
#             "CONFIG": {
#                 "hosts": [(CHANNEL_LAYER_DEFAULT_REDIS_HOST, CHANNEL_LAYER_DEFAULT_REDIS_PORT)],
#             },
#         },
#     }
#

DATABASE_ROUTERS = ["pyhub.mcptools.core.routers.Router"]

DATABASES = get_databases(APP_DATA_DIR)

# "AUTH_USER_MODEL": ...,  # TODO:

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
        "logfile": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": APP_LOG_DIR / "django.log",
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 10,  # 10 MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "httpx": {
            "handlers": ["null"],
            "level": "CRITICAL",
            "propagate": False,
        },
        "django": {
            "handlers": ["logfile"],
            "level": "INFO",
            "propagate": True,
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

# Limit languages to Korean and English only
LANGUAGES = [
    ("ko", "한국어"),
    ("en", "English"),
]

# Disable locale middleware if not needed
if "django.middleware.locale.LocaleMiddleware" in MIDDLEWARE:
    MIDDLEWARE.remove("django.middleware.locale.LocaleMiddleware")

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/
STATIC_URL = env.str("STATIC_URL", default="static/")

STATIC_ROOT = env.path("STATIC_ROOT", default=APP_DATA_DIR / "staticfiles")

STATICFILES_DIRS = []

# "STATICFILES_FINDERS": [
#     "django.contrib.staticfiles.finders.FileSystemFinder",
#     "django.contrib.staticfiles.finders.AppDirectoriesFinder",
# ],
MEDIA_URL = env.str("MEDIA_URL", default="media/")
MEDIA_ROOT = env.path("MEDIA_ROOT", default=APP_DATA_DIR / "mediafiles")

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# pyhub.mcptools

EXPERIMENTAL = env.bool("PYHUB_MCPTOOLS_EXPERIMENTAL", default=False)

EXCEL_DEFAULT_TIMEOUT = env.int("EXCEL_DEFAULT_TIMEOUT", default=60)

# https://api.together.xyz/
TOGETHER_API_KEY = env.str("TOGETHER_API_KEY", default=None)

# https://unsplash.com/oauth/applications/
UNSPLASH_ACCESS_KEY = env.str("UNSPLASH_ACCESS_KEY", default=None)
UNSPLASH_SECRET_KEY = env.str("UNSPLASH_SECRET_KEY", default=None)

# perplexity
# https://docs.perplexity.ai/guides/prompt-guide
PERPLEXITY_SYSTEM_PROMPT = env.str(
    "PERPLEXITY_SYSTEM_PROMPT",
    default="""You are a helpful AI assistant.

Rules:
1. Provide only the final answer. It is important that you do not include any explanation on the steps below.
2. Do not show the intermediate steps information.

Steps:
1. Decide if the answer should be a brief sentence or a list of suggestions.
2. If it is a list of suggestions, first, write a brief and natural introduction based on the original query.
3. Followed by a list of suggestions, each suggestion should be split by two newlines.""",
)
PERPLEXITY_MODEL = env.str("PERPLEXITY_MODEL", default="sonar")
PERPLEXITY_API_KEY = env.str("PERPLEXITY_API_KEY", default=None)
PERPLEXITY_MAX_TOKENS = env.int("PERPLEXITY_MAX_TOKENS", 1024)
PERPLEXITY_TEMPERATURE = env.float("PERPLEXITY_TEMPERATURE", default=0.2)
# low, medium, high
PERPLEXITY_SEARCH_CONTEXT_SIZE = env.str("PERPLEXITY_SEARCH_CONTEXT_SIZE", default="low")

# ONLY_EXPOSE_TOOLS
ONLY_EXPOSE_TOOLS = env.list("ONLY_EXPOSE_TOOLS", default=None)

USE_APPLE_TOOLS = env.bool("USE_APPLE_TOOLS", default=False)

USE_IMAGES_TOOLS = env.bool("USE_IMAGES_TOOLS", default=False)

USE_PYTHON_TOOLS = env.bool("USE_PYTHON_TOOLS", default=False)

USE_SENTIMENT_TOOLS = env.bool("USE_SENTIMENT_TOOLS", default=False)

#
# filesystem
#
_path = env.str("FS_LOCAL_HOME", default=None)
FS_LOCAL_HOME = None if _path is None else Path(_path).expanduser().resolve()

FS_LOCAL_ALLOWED_DIRECTORIES = [
    Path(_path).expanduser().resolve() for _path in env.list("FS_LOCAL_ALLOWED_DIRECTORIES", default=[])
]
if FS_LOCAL_HOME is not None:
    FS_LOCAL_ALLOWED_DIRECTORIES.append(FS_LOCAL_HOME)


#
# maps
#

# https://api.ncloud-docs.com/docs/ai-naver-mapsdirections-driving
# https://console.ncloud.com/naver-service/application

NAVER_MAP_CLIENT_ID = env.str("NAVER_MAP_CLIENT_ID", default=None)
NAVER_MAP_CLIENT_SECRET = env.str("NAVER_MAP_CLIENT_SECRET", default=None)
