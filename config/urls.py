from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import include, path


def healthz(request: HttpRequest) -> HttpResponse:
    return HttpResponse("ok")


urlpatterns = [
    path("healthz/", healthz),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("builds.urls")),
]
