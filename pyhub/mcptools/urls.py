from django.http import HttpResponse
from django.urls import path


def root(request):
    return HttpResponse(
        """
<html>
<head>
</head>
<body>
<h1>pyhub.mcptools</h1>
</body>
</html>
        """
    )


urlpatterns = [
    path("", root, name="root"),
]
