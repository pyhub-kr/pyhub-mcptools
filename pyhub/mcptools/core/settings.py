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
    env_path = Path(env.str("ENV_PATH")).expanduser().resolve()
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
