import factory
from django.contrib.auth.models import User

from builds.models import (
    Build,
    BuildRelic,
    Colour,
    Nightfarer,
    Relic,
    RelicEffect,
    SlotColour,
    Vessel,
    Weapon,
)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"tarnished{n}")
    password = factory.django.Password("password")


class NightfarerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Nightfarer

    name = factory.Sequence(lambda n: f"Nightfarer {n}")
    slug = factory.Sequence(lambda n: f"nightfarer-{n}")


class VesselFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vessel

    name = factory.Sequence(lambda n: f"Vessel {n}")
    slug = factory.Sequence(lambda n: f"vessel-{n}")
    nightfarer = factory.SubFactory(NightfarerFactory)
    slot_1 = SlotColour.RED
    slot_2 = SlotColour.BLUE
    slot_3 = SlotColour.WHITE
    deep_slot_1 = SlotColour.RED
    deep_slot_2 = SlotColour.GREEN
    deep_slot_3 = SlotColour.YELLOW


class RelicEffectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RelicEffect

    name = factory.Sequence(lambda n: f"Effect {n}")


class RelicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Relic

    name = factory.Sequence(lambda n: f"Relic {n}")
    colour = Colour.RED
    kind = Relic.Kind.UNIQUE


class BuildFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Build

    name = factory.Sequence(lambda n: f"Build {n}")
    author = factory.SubFactory(UserFactory)
    nightfarer = factory.SubFactory(NightfarerFactory)
    vessel = factory.SubFactory(
        VesselFactory, nightfarer=factory.SelfAttribute("..nightfarer")
    )


class BuildRelicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BuildRelic

    build = factory.SubFactory(BuildFactory)
    slot = 1
    relic = factory.SubFactory(RelicFactory)


class WeaponFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Weapon

    name = factory.Sequence(lambda n: f"Weapon {n}")
    slug = factory.Sequence(lambda n: f"weapon-{n}")
    category = "Greatsword"
