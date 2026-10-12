from collections.abc import Callable
from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import (
    DEEP_SLOTS,
    STANDARD_SLOTS,
    Build,
    BuildRelic,
    Nightfarer,
    Relic,
    RelicEffect,
    Vessel,
)


class SignUpForm(UserCreationForm[User]):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class RelicForm(forms.ModelForm[Relic]):
    effects = forms.ModelMultipleChoiceField(
        queryset=RelicEffect.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 12}),
        help_text=f"Pick up to {Relic.MAX_EFFECTS} effects.",
    )

    class Meta:
        model = Relic
        fields = ["name", "colour", "is_deep", "effects"]

    def clean_effects(self) -> Any:
        effects = self.cleaned_data["effects"]
        if len(effects) > Relic.MAX_EFFECTS:
            raise forms.ValidationError(
                f"A relic can have at most {Relic.MAX_EFFECTS} effects."
            )
        return effects

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        effects = cleaned.get("effects") or []
        if not cleaned.get("is_deep") and any(e.deep_only for e in effects):
            self.add_error("effects", "Deep-only effects need a Deep of Night relic.")
        return cleaned


class InstanceDataSelect(forms.Select):
    """A select whose options carry data-* attributes taken from the model
    instance, so the build form can colour slots without another request."""

    def __init__(
        self, *args: Any, data: Callable[[Any], dict[str, str]], **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        self.data = data

    def create_option(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        option = super().create_option(*args, **kwargs)
        instance = getattr(option["value"], "instance", None)
        if instance is not None:
            option["attrs"].update(
                {f"data-{key}": value for key, value in self.data(instance).items()}
            )
        return option


def vessel_data(vessel: Vessel) -> dict[str, str]:
    slots = STANDARD_SLOTS + DEEP_SLOTS
    return {"slots": ",".join(vessel.slot_colour(n) for n in slots)}


def relic_data(relic: Relic) -> dict[str, str]:
    return {"colour": relic.colour}


class VesselChoiceField(forms.ModelChoiceField[Vessel]):
    widget = InstanceDataSelect(data=vessel_data)

    def label_from_instance(self, obj: Vessel) -> str:
        return f"{obj.name} ({obj.slot_summary()})"


def slot_field_name(slot: int) -> str:
    return f"slot_{slot}"


class BuildForm(forms.ModelForm[Build]):
    class Meta:
        model = Build
        fields = ["name", "vessel", "description"]
        field_classes = {"vessel": VesselChoiceField}
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 6, "placeholder": "How does it play? What's it for?"}
            )
        }

    def __init__(self, *args: Any, nightfarer: Nightfarer, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.nightfarer = nightfarer
        vessel_field = self.fields["vessel"]
        assert isinstance(vessel_field, forms.ModelChoiceField)
        vessel_field.queryset = nightfarer.available_vessels()

        current = {}
        if self.instance.pk:
            current = {s.slot: s.relic_id for s in self.instance.slots.all()}
        for slot in STANDARD_SLOTS + DEEP_SLOTS:
            deep = slot in DEEP_SLOTS
            label = f"Deep slot {slot - 3}" if deep else f"Slot {slot}"
            self.fields[slot_field_name(slot)] = forms.ModelChoiceField(
                queryset=Relic.objects.filter(is_deep=deep),
                required=False,
                label=label,
                initial=current.get(slot),
                empty_label="Empty",
                widget=InstanceDataSelect(
                    data=relic_data, attrs={"data-slot": str(slot)}
                ),
            )

    def slot_fields(self) -> list[forms.BoundField]:
        return [self[slot_field_name(s)] for s in STANDARD_SLOTS]

    def deep_slot_fields(self) -> list[forms.BoundField]:
        return [self[slot_field_name(s)] for s in DEEP_SLOTS]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        vessel = cleaned.get("vessel")
        if vessel is None:
            return cleaned
        seen: set[int] = set()
        for slot in STANDARD_SLOTS + DEEP_SLOTS:
            field = slot_field_name(slot)
            relic = cleaned.get(field)
            if relic is None:
                continue
            colour = vessel.slot_colour(slot)
            if not relic.fits_slot(colour):
                self.add_error(
                    field,
                    f"A {relic.get_colour_display().lower()} relic can't go in a "
                    f"{colour} slot.",
                )
            if relic.pk in seen:
                self.add_error(field, "The same relic can't be equipped twice.")
            seen.add(relic.pk)
        return cleaned

    @transaction.atomic
    def save(self, commit: bool = True) -> Build:
        build = super().save(commit=False)
        build.nightfarer = self.nightfarer
        build.save()
        build.slots.all().delete()
        BuildRelic.objects.bulk_create(
            BuildRelic(build=build, slot=slot, relic=relic)
            for slot in STANDARD_SLOTS + DEEP_SLOTS
            if (relic := self.cleaned_data.get(slot_field_name(slot)))
        )
        return build
