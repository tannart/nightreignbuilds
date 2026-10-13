import pytest
from django.urls import reverse

from builds.models import Build, Relic
from tests.factories import (
    BuildFactory,
    BuildRelicFactory,
    RelicEffectFactory,
    RelicFactory,
    UserFactory,
    VesselFactory,
    WeaponFactory,
)


def builder_post(nightfarer, **extra):
    return {
        "nightfarer": nightfarer.pk,
        "name": "",
        "description": "",
        "action": "share",
        **extra,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name", ["build-list", "relic-list", "weapon-list", "builder", "signup", "login"]
)
def test_public_pages_load(client, name):
    assert client.get(reverse(name)).status_code == 200


def test_build_detail_loads_by_slug(client, build):
    response = client.get(f"/b/{build.slug}/")
    assert build.name in response.text


@pytest.mark.django_db
def test_build_list_filters_by_nightfarer(client):
    wanted = BuildFactory()
    BuildFactory()
    response = client.get(reverse("build-list"), {"nightfarer": wanted.nightfarer.slug})
    assert list(response.context["build_list"]) == [wanted]


@pytest.mark.django_db
def test_build_list_hides_share_links(client):
    BuildFactory(is_listed=False)
    assert list(client.get(reverse("build-list")).context["build_list"]) == []


def test_my_builds_include_my_share_links(client, user):
    link = BuildFactory(author=user, is_listed=False)
    client.force_login(user)
    response = client.get(reverse("build-list"), {"author": user.username})
    assert list(response.context["build_list"]) == [link]


def test_anyone_can_get_a_share_link(client, nightfarer):
    response = client.post(reverse("builder"), builder_post(nightfarer))
    build = Build.objects.get()
    assert (response.url, build.author, build.is_listed) == (
        f"/b/{build.slug}/?shared",
        None,
        False,
    )


def test_share_link_gets_default_name(client, nightfarer):
    client.post(reverse("builder"), builder_post(nightfarer))
    assert Build.objects.get().name == f"{nightfarer} build"


def test_saving_needs_login(client, nightfarer):
    client.post(reverse("builder"), builder_post(nightfarer, action="save", name="X"))
    assert not Build.objects.exists()


def test_saving_needs_a_name(client, user, nightfarer):
    client.force_login(user)
    response = client.post(reverse("builder"), builder_post(nightfarer, action="save"))
    assert "name" in response.context["form"].errors


def test_save_lists_build_under_author(client, user, nightfarer):
    client.force_login(user)
    client.post(
        reverse("builder"), builder_post(nightfarer, action="save", name="Mine")
    )
    build = Build.objects.get()
    assert (build.author, build.is_listed) == (user, True)


def test_builder_saves_relics_and_weapons(client, nightfarer):
    relic = RelicFactory()
    weapon = WeaponFactory()
    client.post(
        reverse("builder"),
        builder_post(nightfarer, **{"slot2-relic": relic.pk, "weapon_1": weapon.name}),
    )
    build = Build.objects.get()
    assert (build.slots.get().relic, list(build.weapons.all())) == (relic, [weapon])


@pytest.mark.parametrize(("deep", "expected"), [("", 0), ("on", 1)])
def test_deep_slots_only_count_with_deep_of_night(client, nightfarer, deep, expected):
    client.post(
        reverse("builder"),
        builder_post(
            nightfarer,
            deep_of_night=deep,
            **{
                "slot4-custom": "on",
                "slot4-custom_colour": "red",
                "slot4-custom_effect_1": "Vigor +3",
            },
        ),
    )
    assert Build.objects.get().slots.count() == expected


def test_builder_rejects_relic_that_does_not_fit_vessel(client, nightfarer):
    vessel = VesselFactory(nightfarer=nightfarer)
    relic = RelicFactory(colour="green")
    response = client.post(
        reverse("builder"),
        builder_post(nightfarer, vessel=vessel.pk, **{"slot1-relic": relic.pk}),
    )
    assert "relic" in response.context["standard_slot_forms"][0].errors


def test_builder_rejects_same_relic_twice(client, nightfarer):
    relic = RelicFactory()
    response = client.post(
        reverse("builder"),
        builder_post(nightfarer, **{"slot1-relic": relic.pk, "slot2-relic": relic.pk}),
    )
    assert "relic" in response.context["standard_slot_forms"][1].errors


def test_editing_keeps_slug(client, user):
    build = BuildFactory(author=user)
    client.force_login(user)
    client.post(
        reverse("build-update", args=[build.slug]),
        builder_post(build.nightfarer, action="save", name="Renamed"),
    )
    build.refresh_from_db()
    assert (build.name, Build.objects.count()) == ("Renamed", 1)


def test_edit_form_shows_current_relics(client, user):
    slot = BuildRelicFactory(build__author=user, slot=3)
    client.force_login(user)
    response = client.get(reverse("build-update", args=[slot.build.slug]))
    assert response.context["standard_slot_forms"][2]["relic"].value() == str(
        slot.relic.pk
    )


@pytest.mark.parametrize("name", ["build-update", "build-delete"])
def test_only_author_can_modify(client, build, name):
    client.force_login(UserFactory())
    assert client.get(reverse(name, args=[build.slug])).status_code == 403


def test_anonymous_share_links_cannot_be_edited(client, db):
    build = BuildFactory(author=None, is_listed=False)
    assert client.get(reverse("build-update", args=[build.slug])).status_code == 403


def test_publish_lists_a_share_link(client, user):
    build = BuildFactory(author=user, is_listed=False)
    client.force_login(user)
    client.post(reverse("build-publish", args=[build.slug]))
    build.refresh_from_db()
    assert build.is_listed


def test_remix_prefills_builder(client, build):
    response = client.get(reverse("builder"), {"from": build.slug})
    assert response.context["form"]["name"].value() == f"{build.name} (remix)"


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
def test_relic_list_filters(client, user, params, expected):
    tear = RelicFactory(name="Silver Tear", colour="blue")
    tear.effects.set([RelicEffectFactory(name="Arcane +3")])
    RelicFactory(name="Golden Sprout", colour="green", kind="custom", created_by=user)
    client.force_login(user)
    response = client.get(reverse("relic-list"), params)
    assert [r.name for r in response.context["relic_list"]] == expected


def test_relic_list_hides_other_peoples_relics(client, user):
    RelicFactory(kind=Relic.Kind.CUSTOM, created_by=UserFactory())
    client.force_login(user)
    assert list(client.get(reverse("relic-list")).context["relic_list"]) == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("params", "expected"),
    [({"category": "Bow"}, ["Longbow"]), ({"q": "zwei"}, ["Zweihander"])],
)
def test_weapon_list_filters(client, params, expected):
    WeaponFactory(name="Longbow", category="Bow")
    WeaponFactory(name="Zweihander", category="Colossal Sword")
    response = client.get(reverse("weapon-list"), params)
    assert [w.name for w in response.context["weapon_list"]] == expected
