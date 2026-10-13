import pytest
from django.template import Context, Template
from django.test import RequestFactory
from django.urls import reverse

from tests.factories import RelicFactory, WeaponFactory


@pytest.fixture
def searchables(db):
    RelicFactory(name="Silver Tear")
    WeaponFactory(name="Silver Sword")


@pytest.mark.parametrize("name", ["relic-list", "weapon-list"])
def test_live_search_returns_only_results(client, searchables, name):
    response = client.get(reverse(name), {"q": "silver"}, HTTP_X_LIVE_SEARCH="1")
    assert ("<html" in response.text, "Silver" in response.text) == (False, True)


@pytest.mark.parametrize(
    ("name", "count"),
    [("relic-list", "1 relic matching"), ("weapon-list", "1 weapon matching")],
)
def test_live_search_sends_result_count(client, searchables, name, count):
    response = client.get(reverse(name), {"q": "silver"}, HTTP_X_LIVE_SEARCH="1")
    assert count in response.text


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["relic-list", "weapon-list"])
def test_live_search_pages_vary_on_header(client, name):
    assert "X-Live-Search" in client.get(reverse(name))["Vary"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("name", "target"),
    [("relic-list", "relic-results"), ("weapon-list", "weapon-results")],
)
def test_search_form_points_at_results(client, name, target):
    response = client.get(reverse(name))
    assert f'data-live-search="{target}"' in response.text


def render_tag(source, query_string=""):
    request = RequestFactory().get(f"/?{query_string}")
    template = Template("{% load live_search %}" + source)
    live = {"target": "thing-results", "noun": "thing"}
    return template.render(Context({"request": request, "live": live}))


@pytest.mark.parametrize(
    ("query_string", "expected"),
    [
        ("colour=red&page=3", ['name="colour" value="red"']),
        ("kind=unique", ['name="kind" value="unique"']),
    ],
)
def test_livesearch_keeps_named_filters(query_string, expected):
    html = render_tag(
        '{% livesearch keep="colour kind" %}{% endlivesearch %}', query_string
    )
    assert [e for e in expected if e in html] == expected


def test_livesearch_drops_unnamed_params():
    html = render_tag("{% livesearch %}{% endlivesearch %}", "page=3")
    assert 'name="page"' not in html


def test_livesearch_renders_extra_controls_unescaped():
    html = render_tag(
        '{% livesearch %}<select name="category"></select>{% endlivesearch %}'
    )
    assert '<select name="category">' in html
