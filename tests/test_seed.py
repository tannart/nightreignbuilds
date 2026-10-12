import pytest
from django.core.management import call_command

from builds.models import Nightfarer, SlotColour, Vessel


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed_game_data")
    call_command("seed_game_data")
    assert (Nightfarer.objects.count(), Vessel.objects.count()) == (10, 74)


@pytest.mark.django_db
def test_seed_sets_slot_colours():
    call_command("seed_game_data")
    urn = Vessel.objects.get(name="Wylder's Urn")
    assert [urn.slot_1, urn.slot_2, urn.slot_3] == [
        SlotColour.RED,
        SlotColour.RED,
        SlotColour.BLUE,
    ]
