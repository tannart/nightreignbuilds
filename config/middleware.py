from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect


def canonical_host(
    get_response: Callable[[HttpRequest], HttpResponse],
) -> Callable[[HttpRequest], HttpResponse]:
    """Send www.<domain> to the bare domain so every build has one URL."""

    def middleware(request: HttpRequest) -> HttpResponse:
        host = request.get_host()
        if settings.CANONICAL_HOST and host == f"www.{settings.CANONICAL_HOST}":
            url = f"https://{settings.CANONICAL_HOST}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(url)
        return get_response(request)

    return middleware
