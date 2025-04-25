import os

from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "pyhub.mcptools.core.settings",
)

app = Celery("pyhub.mcptools")

# settings 내에서 CELERY_ 접두사 설정을 가져와서 적용
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    간단한 디버깅용 태스크 예시.
    bind=True는 태스크 인스턴스(self)에 접근할 수 있게 합니다.
    ignore_result=True는 결과 백엔드에 결과 저장을 시도하지 않습니다.
    """
    print(f"Request: {self.request!r}")
