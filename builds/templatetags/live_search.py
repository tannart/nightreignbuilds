from typing import Any

from django import template
from django.template.base import FilterExpression, Parser, Token
from django.template.loader import render_to_string

register = template.Library()


class LiveSearchNode(template.Node):
    def __init__(self, nodelist: template.NodeList, options: dict[str, Any]):
        self.nodelist = nodelist
        self.options = options

    def render(self, context: template.Context) -> str:
        options = {key: value.resolve(context) for key, value in self.options.items()}
        request = context["request"]
        keep = str(options.get("keep", "")).split()
        return render_to_string(
            "components/live_search_form.html",
            {
                "live": context["live"],
                "query": context.get("query", ""),
                "placeholder": options.get("placeholder", "Search"),
                "label": options.get("label", "Search"),
                "hidden": [
                    (name, value) for name in keep if (value := request.GET.get(name))
                ],
                "extra": self.nodelist.render(context),
            },
        )


@register.tag
def livesearch(parser: Parser, token: Token) -> LiveSearchNode:
    """A search form that refreshes a LiveSearchMixin view's results as you
    type. Anything between the tags (e.g. a filter <select>) goes inside the
    form; ``keep`` names other query parameters to carry along.

        {% livesearch placeholder="Search relics" keep="colour kind" %}
        {% endlivesearch %}
    """
    options: dict[str, FilterExpression] = {}
    for bit in token.split_contents()[1:]:
        name, _, value = bit.partition("=")
        if not value:
            raise template.TemplateSyntaxError(
                f"livesearch options must be name=value, got {bit!r}"
            )
        options[name] = parser.compile_filter(value)
    nodelist = parser.parse(("endlivesearch",))
    parser.delete_first_token()
    return LiveSearchNode(nodelist, options)
