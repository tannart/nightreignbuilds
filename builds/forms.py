from collections.abc import Callable, Iterable
from functools import reduce
from operator import or_
from typing import Any

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db.models import Q

from .models import (
    DEEP_SLOTS,
    STANDARD_SLOTS,
    Build,
    Colour,
    Relic,
    RelicEffect,
    Vessel,
    Weapon,
)


class SignUpForm(UserCreationForm[User]):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)


class RelicForm(forms.ModelForm[Relic]):
    effects = forms.ModelMultipleChoiceField(
        queryset=RelicEffect.objects.filter(official=True),
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
    instance, so the builder can colour slots without another request."""

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
    return {
        "slots": ",".join(vessel.slot_colour(n) for n in slots),
        "nightfarer": str(vessel.nightfarer_id or ""),
    }


class VesselChoiceField(forms.ModelChoiceField[Vessel]):
    widget = InstanceDataSelect(data=vessel_data)

    def label_from_instance(self, obj: Vessel) -> str:
        return f"{obj.name} ({obj.slot_summary()})"


class NightfarerRadio(forms.RadioSelect):
    option_template_name = "builds/widgets/nightfarer_option.html"


class BuilderForm(forms.ModelForm[Build]):
    weapon_fields = [f"weapon_{n}" for n in range(1, Build.MAX_WEAPONS + 1)]

    class Meta:
        model = Build
        fields = ["name", "nightfarer", "vessel", "deep_of_night", "description"]
        field_classes = {"vessel": VesselChoiceField}
        widgets = {
            "nightfarer": NightfarerRadio,
            "name": forms.TextInput(attrs={"placeholder": "e.g. Bleed Wylder"}),
            "description": forms.Textarea(
                attrs={"rows": 5, "placeholder": "How does it play? What's it for?"}
            ),
        }
        labels = {"deep_of_night": "Deep of Night"}
        help_texts = {"deep_of_night": "Adds three Deep of Night relic slots."}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # A name is only needed to save; share links get a default one.
        self.fields["name"].required = False
        nightfarer = self.fields["nightfarer"]
        assert isinstance(nightfarer, forms.ModelChoiceField)
        nightfarer.empty_label = None
        vessel = self.fields["vessel"]
        assert isinstance(vessel, forms.ModelChoiceField)
        vessel.empty_label = "Any vessel (no colour checks)"

        current = list(self.instance.weapons.all()) if self.instance.pk else []
        for n, field in enumerate(self.weapon_fields):
            self.fields[field] = forms.CharField(
                required=False,
                label=f"Weapon {n + 1}",
                initial=current[n].name if n < len(current) else "",
                widget=forms.TextInput(
                    attrs={"list": "weapon-names", "placeholder": "Start typing…"}
                ),
            )

    def weapon_inputs(self) -> list[forms.BoundField]:
        return [self[f] for f in self.weapon_fields]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        nightfarer, vessel = cleaned.get("nightfarer"), cleaned.get("vessel")
        if nightfarer and vessel and not vessel.usable_by(nightfarer):
            self.add_error("vessel", f"{vessel} can't be used by {nightfarer}.")

        entered = {
            field: name
            for field in self.weapon_fields
            if (name := cleaned.get(field, "").strip())
        }
        found: dict[str, Weapon] = {}
        if entered:
            query = reduce(or_, (Q(name__iexact=n) for n in entered.values()))
            found = {w.name.lower(): w for w in Weapon.objects.filter(query)}
        weapons: list[Weapon] = []
        for field, name in entered.items():
            weapon = found.get(name.lower())
            if weapon is None:
                self.add_error(field, f"No weapon called “{name}”.")
            elif weapon not in weapons:
                weapons.append(weapon)
        cleaned["weapons"] = weapons
        return cleaned


class GroupedRelicSelect(forms.Select):
    """Relic picker grouped into sections, with each option carrying its
    colour so the page can hide relics that won't fit the slot."""

    def __init__(self, *args: Any, colours: dict[str, str], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.colours = colours

    def create_option(
        self, name: str, value: Any, *args: Any, **kwargs: Any
    ) -> dict[str, Any]:
        option = super().create_option(name, value, *args, **kwargs)
        if colour := self.colours.get(str(value)):
            option["attrs"]["data-colour"] = colour
        return option


RelicChoices = list[tuple[str, Any]]


class SlotChoices:
    """Everything a slot's relic picker offers, worked out once per request
    and shared by the three standard (or deep) slots."""

    def __init__(self, user: Any, deep: bool, include: Iterable[Relic] = ()):
        relics = Relic.objects.filter(is_deep=deep).prefetch_related("effects")
        catalogue = list(relics.exclude(kind=Relic.Kind.CUSTOM))
        mine = (
            list(relics.filter(kind=Relic.Kind.CUSTOM, created_by=user))
            if user.is_authenticated
            else []
        )
        shown = {r.pk for r in catalogue + mine}
        extra = [r for r in include if r.pk not in shown and r.is_deep == deep]
        groups = [
            ("Remembrance relics", [r for r in catalogue if r.is_remembrance]),
            (
                "Unique relics",
                [r for r in catalogue if r.kind == "unique" and not r.is_remembrance],
            ),
            ("Scene relics", [r for r in catalogue if r.kind == "scene"]),
            ("My relics", mine),
            ("In this build", extra),
        ]
        self.choices: RelicChoices = [("", "Empty")] + [
            (label, [(str(r.pk), r.label()) for r in items])
            for label, items in groups
            if items
        ]
        self.relics = {str(r.pk): r for r in catalogue + mine + extra}
        self.colours = {pk: r.colour for pk, r in self.relics.items()}


class SlotForm(forms.Form):
    """One relic slot: a relic from the list, or a custom relic described on
    the spot (and optionally saved for reuse)."""

    relic = forms.ChoiceField(required=False)
    custom = forms.BooleanField(required=False, label="Custom relic")
    custom_name = forms.CharField(
        required=False,
        max_length=200,
        label="Name",
        widget=forms.TextInput(attrs={"placeholder": "Optional"}),
    )
    custom_colour = forms.ChoiceField(
        required=False, choices=[("", "Colour…")] + Colour.choices, label="Colour"
    )
    custom_effect_1 = forms.CharField(required=False, max_length=200, label="Effect 1")
    custom_effect_2 = forms.CharField(required=False, max_length=200, label="Effect 2")
    custom_effect_3 = forms.CharField(required=False, max_length=200, label="Effect 3")
    save_custom = forms.BooleanField(
        required=False, initial=True, label="Save to my relics"
    )

    def __init__(
        self, *args: Any, slot: int, choices: SlotChoices, **kwargs: Any
    ) -> None:
        kwargs["prefix"] = f"slot{slot}"
        super().__init__(*args, **kwargs)
        self.slot = slot
        self.is_deep = slot in DEEP_SLOTS
        self.lookup = choices.relics
        field = self.fields["relic"]
        assert isinstance(field, forms.ChoiceField)
        field.label = f"Deep slot {slot - 3}" if self.is_deep else f"Slot {slot}"
        field.widget = GroupedRelicSelect(
            colours=choices.colours, attrs={"data-slot": str(slot)}
        )
        field.choices = choices.choices
        for n in (1, 2, 3):
            self.fields[f"custom_effect_{n}"].widget.attrs.update(
                {"list": "effect-names", "placeholder": "Start typing an effect…"}
            )

    def effect_fields(self) -> list[forms.BoundField]:
        return [self[f"custom_effect_{n}"] for n in (1, 2, 3)]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("custom"):
            cleaned["effects"] = [
                effect
                for n in (1, 2, 3)
                if (effect := cleaned.get(f"custom_effect_{n}", "").strip())
            ]
            if not cleaned.get("custom_colour"):
                self.add_error("custom_colour", "Pick the relic's colour.")
            if not cleaned["effects"]:
                self.add_error("custom_effect_1", "Add at least one effect.")
            cleaned["relic_obj"] = None
        else:
            cleaned["relic_obj"] = self.lookup.get(cleaned.get("relic") or "")
        return cleaned

    @property
    def colour(self) -> str | None:
        if self.cleaned_data.get("custom"):
            return self.cleaned_data.get("custom_colour") or None
        relic = self.cleaned_data.get("relic_obj")
        return relic.colour if relic else None

    @property
    def is_filled(self) -> bool:
        return bool(
            self.cleaned_data.get("custom") or self.cleaned_data.get("relic_obj")
        )

    def to_relic(self, user: Any) -> Relic | None:
        """The relic for this slot, creating the custom one if there is one."""
        if not self.cleaned_data.get("custom"):
            picked: Relic | None = self.cleaned_data.get("relic_obj")
            return picked
        colour = Colour(self.cleaned_data["custom_colour"])
        keep = user.is_authenticated and self.cleaned_data.get("save_custom")
        default_name = f"{'Deep ' if self.is_deep else ''}{colour.label} relic"
        relic = Relic.objects.create(
            name=self.cleaned_data["custom_name"].strip() or default_name,
            colour=colour,
            is_deep=self.is_deep,
            kind=Relic.Kind.CUSTOM,
            created_by=user if keep else None,
        )
        relic.effects.set(
            [
                RelicEffect.objects.get_or_create(
                    name=name, defaults={"official": False}
                )[0]
                for name in self.cleaned_data["effects"]
            ]
        )
        return relic
