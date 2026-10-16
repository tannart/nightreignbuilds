import json
import re
from pathlib import Path
from typing import Any

from django.conf import settings
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
from builds.models import (
    Nightfarer,
    Relic,
    RelicEffect,
    SlotColour,
    Vessel,
    Weapon,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Character-specific effects are written "[Wylder] ...".
NIGHTFARER_PREFIX = re.compile(r"^\[(\w+)\]")

COLOUR_CODES = {
    "R": SlotColour.RED,
    "B": SlotColour.BLUE,
    "Y": SlotColour.YELLOW,
    "G": SlotColour.GREEN,
    "W": SlotColour.WHITE,
}


def vessel_icon(slug: str) -> str:
    """Vessels without an icon file in static/vessels/ get none."""
    icon = f"vessels/{slug}.webp"
    return icon if (settings.BASE_DIR / "static" / icon).exists() else ""


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
                        "icon": vessel_icon(slugify(vessel_name)),
                        **slot_fields(standard, deep),
                    },
                )
        for vessel_name, standard, deep in UNIVERSAL_VESSELS:
            Vessel.objects.update_or_create(
                slug=slugify(vessel_name),
                defaults={
                    "name": vessel_name,
                    "nightfarer": None,
                    "icon": vessel_icon(slugify(vessel_name)),
                    **slot_fields(standard, deep),
                },
            )
        self.seed_relics()
        self.seed_effects()
        self.seed_weapons()
        self.stdout.write(
            self.style.SUCCESS(
                f"{Nightfarer.objects.count()} nightfarers, "
                f"{Vessel.objects.count()} vessels, "
                f"{Relic.objects.exclude(slug=None).count()} catalogued relics, "
                f"{RelicEffect.objects.filter(official=True).count()} effects, "
                f"{Weapon.objects.count()} weapons"
            )
        )

    def seed_relics(self) -> None:
        nightfarers = {n.name: n for n in Nightfarer.objects.all()}
        effects: dict[str, RelicEffect] = {}
        for entry in json.loads((DATA_DIR / "relics.json").read_text()):
            relic, _ = Relic.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "kind": entry["kind"],
                    "colour": entry["colour"],
                    "acquisition": entry["acquisition"],
                    "icon": entry["icon"],
                },
            )
            relic.effects.set(
                [self.effect(name, nightfarers, effects) for name in entry["effects"]]
            )

    def seed_effects(self) -> None:
        """The wider pool of effects that random relics can roll, offered as
        suggestions when people describe their own relics."""
        nightfarers = {n.name: n for n in Nightfarer.objects.all()}
        cache = {e.name: e for e in RelicEffect.objects.all()}
        for name in json.loads((DATA_DIR / "effects.json").read_text()):
            self.effect(name, nightfarers, cache)

    def seed_weapons(self) -> None:
        for entry in json.loads((DATA_DIR / "weapons.json").read_text()):
            Weapon.objects.update_or_create(
                slug=entry["slug"],
                defaults={
                    "name": entry["name"],
                    "category": entry["category"],
                    "icon": entry["icon"],
                },
            )

    def effect(
        self,
        name: str,
        nightfarers: dict[str, Nightfarer],
        cache: dict[str, RelicEffect],
    ) -> RelicEffect:
        if name not in cache:
            match = NIGHTFARER_PREFIX.match(name)
            cache[name], _ = RelicEffect.objects.update_or_create(
                name=name,
                defaults={
                    "nightfarer": nightfarers.get(match[1]) if match else None,
                    "official": True,
                },
            )
        return cache[name]
