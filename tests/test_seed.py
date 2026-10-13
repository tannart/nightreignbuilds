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
