"""Live search for list views.

A list view using LiveSearchMixin renders its results through
``components/live_results.html``. When the page's search script asks for
fresh results (by sending the LIVE_SEARCH_HEADER), the view returns just
that fragment instead of the whole page, which the script swaps in.
"""

from typing import Any

from django.http import HttpRequest, HttpResponse
from django.utils.cache import patch_vary_headers
from django.views.generic.list import MultipleObjectMixin

LIVE_SEARCH_HEADER = "X-Live-Search"


class LiveSearchMixin(MultipleObjectMixin):  # type: ignore[type-arg]
    request: HttpRequest
    live_results_template: str
    # Singular name for the count line, e.g. "3 relics matching “tear”".
    live_noun: str

    def get_template_names(self) -> list[str]:
        if self.request.headers.get(LIVE_SEARCH_HEADER):
            return ["components/live_results_response.html"]
        return super().get_template_names()  # type: ignore[misc,no-any-return]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        context["live"] = {
            "target": f"{self.live_noun}-results",
            "template": self.live_results_template,
            "noun": self.live_noun,
        }
        return context

    def render_to_response(
        self, context: dict[str, Any], **kwargs: Any
    ) -> HttpResponse:
        response: HttpResponse = super().render_to_response(  # type: ignore[misc]
            context, **kwargs
        )
        # The same URL returns a page or a fragment depending on the header.
        patch_vary_headers(response, [LIVE_SEARCH_HEADER])
        return response
