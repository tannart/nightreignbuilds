import pytest
from django.core.management import call_command

from builds.models import (
    Nightfarer,
    Relic,
    RelicEffect,
    SlotColour,
    Vessel,
    Weapon,
)


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed_game_data")
    call_command("seed_game_data")
    counts = (Nightfarer.objects.count(), Vessel.objects.count(), Relic.objects.count())
    assert counts == (10, 74, 118)


@pytest.mark.django_db
def test_seed_sets_slot_colours():
    call_command("seed_game_data")
    urn = Vessel.objects.get(name="Wylder's Urn")
    assert [urn.slot_1, urn.slot_2, urn.slot_3] == [
        SlotColour.RED,
        SlotColour.RED,
        SlotColour.BLUE,
    ]


@pytest.mark.django_db
def test_seed_loads_unique_relic():
    call_command("seed_game_data")
    relic = Relic.objects.get(slug="silver-tear")
    assert (relic.colour, relic.kind) == ("red", Relic.Kind.UNIQUE)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("effect", "nightfarer"),
    [
        ("[Scholar] Prevent slowing of Character Skill progress", "Scholar"),
        ("[Wylder] Art gauge greatly filled when ability is activated", "Wylder"),
    ],
)
def test_seed_links_character_effects(effect, nightfarer):
    call_command("seed_game_data")
    assert RelicEffect.objects.get(name=effect).nightfarer.name == nightfarer


@pytest.mark.django_db
def test_seeded_relic_icons_exist(settings):
    call_command("seed_game_data")
    static = settings.BASE_DIR / "static"
    missing = [r.icon for r in Relic.objects.all() if not (static / r.icon).exists()]
    assert missing == []


@pytest.mark.django_db
def test_seeded_weapon_icons_exist(settings):
    call_command("seed_game_data")
    static = settings.BASE_DIR / "static"
    missing = [w.icon for w in Weapon.objects.all() if not (static / w.icon).exists()]
    assert missing == []


@pytest.mark.django_db
def test_seed_loads_weapons():
    call_command("seed_game_data")
    assert Weapon.objects.get(slug="wylder-s-greatsword").category == "Greatsword"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("shop", "currency"),
    [("Small Jar Bazaar", "Murk"), ("Signboard", "Sovereign Sigil")],
)
def test_shop_prices_name_their_currency(shop, currency):
    call_command("seed_game_data")
    priced = Relic.objects.filter(acquisition__contains=shop)
    assert all(currency in r.acquisition for r in priced)


@pytest.mark.django_db
def test_collector_signboard_spelled_as_in_game():
    call_command("seed_game_data")
    assert not Relic.objects.filter(acquisition__contains="Collector's").exists()


@pytest.mark.django_db
def test_seeded_vessel_icons_exist(settings):
    call_command("seed_game_data")
    static = settings.BASE_DIR / "static"
    icons = Vessel.objects.exclude(icon="").values_list("icon", flat=True)
    assert [i for i in icons if not (static / i).exists()] == []


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug, icon",
    [
        ("wylders-goblet", "vessels/wylders-goblet.webp"),
        ("duchess-chalice", "vessels/duchess-chalice.webp"),
        ("scadutree-grail", "vessels/scadutree-grail.webp"),
        ("sealed-wylders-urn", "vessels/sealed-wylders-urn.webp"),
    ],
)
def test_seed_sets_vessel_icon(slug, icon):
    call_command("seed_game_data")
    assert Vessel.objects.get(slug=slug).icon == icon


@pytest.mark.django_db
def test_seeded_nightfarer_icons_exist(settings):
    call_command("seed_game_data")
    static = settings.BASE_DIR / "static"
    icons = [n.icon for n in Nightfarer.objects.all()]
    assert [i for i in icons if not (static / i).exists()] == []


@pytest.mark.django_db
def test_seed_adds_deep_relic_curses():
    call_command("seed_game_data")
    curse = RelicEffect.objects.get(name="Taking Damage Causes Poison Buildup")
    assert (curse.is_curse, curse.deep_only) == (True, True)
