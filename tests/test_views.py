import pytest
from django.urls import reverse

from tests.factories import (
    BuildFactory,
    RelicEffectFactory,
    RelicFactory,
    UserFactory,
    VesselFactory,
)


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["build-list", "relic-list", "signup", "login"])
def test_public_pages_load(client, name):
    assert client.get(reverse(name)).status_code == 200


def test_build_detail_loads(client, build):
    response = client.get(build.get_absolute_url())
    assert build.name in response.text


@pytest.mark.django_db
def test_build_list_filters_by_nightfarer(client):
    wanted = BuildFactory()
    BuildFactory()
    response = client.get(reverse("build-list"), {"nightfarer": wanted.nightfarer.slug})
    assert list(response.context["build_list"]) == [wanted]


def test_create_build_requires_login(client, nightfarer):
    response = client.get(reverse("build-create", args=[nightfarer.slug]))
    assert response.status_code == 302


def test_create_build_sets_author(client, user, nightfarer):
    vessel = VesselFactory(nightfarer=nightfarer)
    client.force_login(user)
    client.post(
        reverse("build-create", args=[nightfarer.slug]),
        {"name": "Mine", "vessel": vessel.pk, "description": ""},
    )
    assert user.builds.get().name == "Mine"


@pytest.mark.parametrize("name", ["build-update", "build-delete"])
def test_only_author_can_modify(client, build, name):
    client.force_login(UserFactory())
    assert client.get(reverse(name, args=[build.pk])).status_code == 403


def test_signup_logs_user_in(client, db):
    client.post(
        reverse("signup"),
        {
            "username": "newbie",
            "password1": "s3cret-Pass!",
            "password2": "s3cret-Pass!",
        },
    )
    assert client.get(reverse("build-list")).context["user"].username == "newbie"


@pytest.mark.parametrize("debug", [True, False])
def test_healthz_is_not_redirected(client, settings, debug):
    settings.DEBUG = debug
    settings.SECURE_SSL_REDIRECT = not debug
    settings.SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
    assert client.get("/healthz/").status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"q": "tear"}, ["Silver Tear"]),
        ({"q": "arcane"}, ["Silver Tear"]),
        ({"colour": "green"}, ["Golden Sprout"]),
        ({"kind": "custom"}, ["Golden Sprout"]),
    ],
)
def test_relic_list_filters(client, params, expected):
    tear = RelicFactory(name="Silver Tear", colour="blue", kind="unique")
    tear.effects.set([RelicEffectFactory(name="Arcane +3")])
    RelicFactory(name="Golden Sprout", colour="green", kind="custom")
    response = client.get(reverse("relic-list"), params)
    assert [r.name for r in response.context["relic_list"]] == expected
