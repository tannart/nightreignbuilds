import pytest

from builds.forms import BuildForm, RelicForm
from builds.models import Colour
from tests.factories import RelicEffectFactory, RelicFactory, VesselFactory


def build_form_data(vessel, **slots):
    return {"name": "Bleed Wylder", "vessel": vessel.pk, "description": "", **slots}


@pytest.mark.django_db
def test_build_form_saves_relics_in_slots(nightfarer, user):
    vessel = VesselFactory(nightfarer=nightfarer)
    relic = RelicFactory(colour=Colour.GREEN)
    form = BuildForm(build_form_data(vessel, slot_3=relic.pk), nightfarer=nightfarer)
    form.instance.author = user
    build = form.save() if form.is_valid() else None
    assert build.slots.get().relic == relic


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("slot", "colour"), [("slot_1", Colour.BLUE), ("slot_2", Colour.YELLOW)]
)
def test_build_form_rejects_wrong_colour(nightfarer, slot, colour):
    vessel = VesselFactory(nightfarer=nightfarer)
    relic = RelicFactory(colour=colour)
    form = BuildForm(build_form_data(vessel, **{slot: relic.pk}), nightfarer=nightfarer)
    assert slot in form.errors


@pytest.mark.django_db
def test_build_form_rejects_duplicate_relic(nightfarer):
    vessel = VesselFactory(nightfarer=nightfarer)
    relic = RelicFactory(colour=Colour.RED)
    form = BuildForm(
        build_form_data(vessel, slot_1=relic.pk, slot_3=relic.pk), nightfarer=nightfarer
    )
    assert "slot_3" in form.errors


@pytest.mark.django_db
def test_build_form_hides_other_nightfarers_vessels(nightfarer):
    other = VesselFactory()
    form = BuildForm(nightfarer=nightfarer)
    assert other not in form.fields["vessel"].queryset


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
