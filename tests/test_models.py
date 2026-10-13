import pytest
from django.core.exceptions import ValidationError

from builds.models import Colour, SlotColour
from tests.factories import (
    BuildFactory,
    BuildRelicFactory,
    NightfarerFactory,
    RelicEffectFactory,
    RelicFactory,
    VesselFactory,
)


@pytest.mark.parametrize(
    ("relic_colour", "slot_colour", "expected"),
    [
        (Colour.RED, SlotColour.RED, True),
        (Colour.BLUE, SlotColour.RED, False),
        (Colour.GREEN, SlotColour.WHITE, True),
    ],
)
def test_relic_fits_slot(relic_colour, slot_colour, expected):
    relic = RelicFactory.build(colour=relic_colour)
    assert relic.fits_slot(slot_colour) is expected


@pytest.mark.django_db
def test_universal_vessel_available_to_every_nightfarer(nightfarer):
    grail = VesselFactory(nightfarer=None)
    assert grail in nightfarer.available_vessels()


@pytest.mark.django_db
def test_other_nightfarers_vessel_not_available(nightfarer):
    vessel = VesselFactory(nightfarer=NightfarerFactory())
    assert vessel not in nightfarer.available_vessels()


@pytest.mark.django_db
def test_build_rejects_vessel_for_other_nightfarer():
    build = BuildFactory.build(
        nightfarer=NightfarerFactory(),
        vessel=VesselFactory(nightfarer=NightfarerFactory()),
    )
    with pytest.raises(ValidationError):
        build.clean()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("slot", "colour", "is_deep"),
    [
        (1, Colour.BLUE, False),
        (1, Colour.RED, True),
        (4, Colour.RED, False),
    ],
)
def test_build_relic_rejects_invalid_relic(build, slot, colour, is_deep):
    build_relic = BuildRelicFactory.create(
        build=build, slot=slot, relic=RelicFactory(colour=colour, is_deep=is_deep)
    )
    with pytest.raises(ValidationError):
        build_relic.clean()


@pytest.mark.django_db
def test_build_relic_accepts_matching_relic(build):
    build_relic = BuildRelicFactory.create(
        build=build, slot=4, relic=RelicFactory(colour=Colour.RED, is_deep=True)
    )
    build_relic.clean()
    assert build_relic.slot_colour == SlotColour.RED


def test_vessel_slot_summary():
    vessel = VesselFactory.build()
    assert vessel.slot_summary() == "Red, Blue, White | Deep: Red, Green, Yellow"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("scene", "Grand Scene [Red] — Vigor +2"),
        ("unique", "Grand Scene [Red]"),
    ],
)
def test_relic_label_shows_effects_for_scene_relics(kind, expected):
    relic = RelicFactory(name="Grand Scene", kind=kind)
    relic.effects.set([RelicEffectFactory(name="Vigor +2")])
    assert relic.label() == expected
