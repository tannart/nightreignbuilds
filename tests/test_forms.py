import pytest
from django.contrib.auth.models import AnonymousUser

from builds.forms import BuilderForm, RelicForm, SlotChoices, SlotForm
from builds.models import Colour, Relic
from tests.factories import (
    RelicEffectFactory,
    RelicFactory,
    UserFactory,
    VesselFactory,
    WeaponFactory,
)


def builder_data(nightfarer, **extra):
    return {"nightfarer": nightfarer.pk, "name": "", "description": "", **extra}


def slot_form(data, user=None, slot=1):
    choices = SlotChoices(user or AnonymousUser(), deep=slot > 3)
    return SlotForm(data, slot=slot, choices=choices)


@pytest.mark.django_db
def test_builder_form_finds_weapons_ignoring_case(nightfarer):
    weapon = WeaponFactory(name="Wylder's Greatsword")
    form = BuilderForm(builder_data(nightfarer, weapon_1="wylder's greatsword"))
    form.is_valid()
    assert form.cleaned_data["weapons"] == [weapon]


@pytest.mark.django_db
def test_builder_form_rejects_unknown_weapon(nightfarer):
    form = BuilderForm(builder_data(nightfarer, weapon_2="Banana"))
    assert "weapon_2" in form.errors


@pytest.mark.django_db
def test_builder_form_rejects_other_nightfarers_vessel(nightfarer):
    vessel = VesselFactory()
    form = BuilderForm(builder_data(nightfarer, vessel=vessel.pk))
    assert "vessel" in form.errors


@pytest.mark.django_db
def test_builder_form_allows_universal_vessel(nightfarer):
    grail = VesselFactory(nightfarer=None)
    form = BuilderForm(builder_data(nightfarer, vessel=grail.pk))
    assert form.is_valid()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"slot1-custom": "on", "slot1-custom_effect_1": "Vigor +3"}, "custom_colour"),
        ({"slot1-custom": "on", "slot1-custom_colour": "red"}, "custom_effect_1"),
    ],
)
def test_custom_relic_needs_colour_and_effect(data, field):
    form = slot_form(data)
    assert field in form.errors


@pytest.mark.django_db
def test_slot_form_resolves_catalogue_relic():
    relic = RelicFactory()
    form = slot_form({"slot1-relic": str(relic.pk)})
    form.is_valid()
    assert form.cleaned_data["relic_obj"] == relic


@pytest.mark.django_db
def test_slot_choices_hide_other_peoples_custom_relics(user):
    RelicFactory(kind=Relic.Kind.CUSTOM, created_by=UserFactory())
    mine = RelicFactory(kind=Relic.Kind.CUSTOM, created_by=user)
    assert list(SlotChoices(user, deep=False).relics.values()) == [mine]


@pytest.mark.django_db
def test_slot_choices_group_remembrance_relics():
    RelicFactory(acquisition="Complete Wylder's first Remembrance Quest.")
    labels = [label for label, _ in SlotChoices(AnonymousUser(), deep=False).choices]
    assert labels == ["", "Remembrance relics"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("logged_in", "save", "kept"),
    [(True, "on", True), (True, "", False), (False, "on", False)],
)
def test_custom_relic_saved_to_my_relics_only_when_asked(logged_in, save, kept):
    user = UserFactory() if logged_in else AnonymousUser()
    form = slot_form(
        {
            "slot4-custom": "on",
            "slot4-custom_colour": "blue",
            "slot4-custom_effect_1": "Arcane +2",
            "slot4-save_custom": save,
        },
        user=user,
        slot=4,
    )
    form.is_valid()
    relic = form.to_relic(user)
    assert (relic.is_deep, relic.created_by is not None) == (True, kept)


@pytest.mark.django_db
def test_custom_relic_marks_new_effects_unofficial():
    form = slot_form(
        {
            "slot1-custom": "on",
            "slot1-custom_colour": "green",
            "slot1-custom_effect_1": "Totally real effect",
        }
    )
    form.is_valid()
    relic = form.to_relic(AnonymousUser())
    assert relic.effects.get().official is False


@pytest.mark.django_db
def test_relic_form_limits_effects():
    effects = RelicEffectFactory.create_batch(4)
    form = RelicForm(
        {"name": "Greedy", "colour": Colour.RED, "effects": [e.pk for e in effects]}
    )
    assert "effects" in form.errors


@pytest.mark.django_db
def test_relic_form_rejects_deep_effect_on_normal_relic():
    effect = RelicEffectFactory(deep_only=True)
    form = RelicForm({"name": "Odd", "colour": Colour.RED, "effects": [effect.pk]})
    assert "effects" in form.errors


def deep_custom(**effects):
    return {"slot4-custom": "on", "slot4-custom_colour": "red", **effects}


@pytest.mark.django_db
def test_custom_deep_relic_pairs_curse_with_its_effect():
    form = slot_form(
        deep_custom(
            **{
                "slot4-custom_effect_1": "Vigor +3",
                "slot4-custom_effect_2": "Arcane +1",
                "slot4-custom_curse_2": "Reduced Rune Acquisition",
            }
        ),
        slot=4,
    )
    form.is_valid()
    lines = form.to_relic(AnonymousUser()).effect_lines()
    assert sorted((e.name, c and c.name) for e, c in lines) == [
        ("Arcane +1", "Reduced Rune Acquisition"),
        ("Vigor +3", None),
    ]


@pytest.mark.django_db
def test_curse_needs_an_effect():
    form = slot_form(
        deep_custom(
            **{
                "slot4-custom_effect_1": "Vigor +3",
                "slot4-custom_curse_2": "Continuous HP Loss",
            }
        ),
        slot=4,
    )
    assert "custom_curse_2" in form.errors


@pytest.mark.django_db
@pytest.mark.parametrize(("slot", "expected"), [(1, False), (4, True)])
def test_only_deep_slots_take_curses(slot, expected):
    assert ("custom_curse_1" in slot_form(None, slot=slot).fields) is expected


@pytest.mark.django_db
def test_relic_form_does_not_offer_curses():
    curse = RelicEffectFactory(is_curse=True)
    assert curse not in RelicForm().fields["effects"].queryset
