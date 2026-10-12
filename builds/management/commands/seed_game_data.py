from typing import Any

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from builds.data.game_data import (
    NIGHTFARER_VESSEL_SLOTS,
    NIGHTFARERS,
    UNIVERSAL_VESSELS,
    VESSEL_NAME_TEMPLATES,
    possessive,
)
from builds.models import Nightfarer, SlotColour, Vessel

COLOUR_CODES = {
    "R": SlotColour.RED,
    "B": SlotColour.BLUE,
    "Y": SlotColour.YELLOW,
    "G": SlotColour.GREEN,
    "W": SlotColour.WHITE,
}


def slot_fields(standard: str, deep: str) -> dict[str, str]:
    colours = [COLOUR_CODES[c] for c in standard + deep]
    names = ["slot_1", "slot_2", "slot_3", "deep_slot_1", "deep_slot_2", "deep_slot_3"]
    return dict(zip(names, colours, strict=True))


class Command(BaseCommand):
    help = "Create or update nightfarers and vessels. Safe to run repeatedly."

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        for name in NIGHTFARERS:
            nightfarer, _ = Nightfarer.objects.update_or_create(
                slug=slugify(name), defaults={"name": name}
            )
            slots = NIGHTFARER_VESSEL_SLOTS[name]
            for template, layout in zip(VESSEL_NAME_TEMPLATES, slots, strict=True):
                vessel_name = template.format(owner=possessive(name))
                standard, deep = layout.split("/")
                Vessel.objects.update_or_create(
                    slug=slugify(vessel_name),
                    defaults={
                        "name": vessel_name,
                        "nightfarer": nightfarer,
                        **slot_fields(standard, deep),
                    },
                )
        for vessel_name, standard, deep in UNIVERSAL_VESSELS:
            Vessel.objects.update_or_create(
                slug=slugify(vessel_name),
                defaults={
                    "name": vessel_name,
                    "nightfarer": None,
                    **slot_fields(standard, deep),
                },
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"{Nightfarer.objects.count()} nightfarers, "
                f"{Vessel.objects.count()} vessels"
            )
        )
