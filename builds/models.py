from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse


class Colour(models.TextChoices):
    RED = "red", "Red"
    BLUE = "blue", "Blue"
    YELLOW = "yellow", "Yellow"
    GREEN = "green", "Green"


class SlotColour(models.TextChoices):
    RED = "red", "Red"
    BLUE = "blue", "Blue"
    YELLOW = "yellow", "Yellow"
    GREEN = "green", "Green"
    WHITE = "white", "White (any colour)"


STANDARD_SLOTS = (1, 2, 3)
DEEP_SLOTS = (4, 5, 6)


class Nightfarer(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def available_vessels(self) -> models.QuerySet["Vessel"]:
        return Vessel.objects.filter(
            models.Q(nightfarer=self) | models.Q(nightfarer__isnull=True)
        )


class Vessel(models.Model):
    """A relic holder (urn, goblet, chalice, grail). Grails with no
    nightfarer can be used by everyone."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    nightfarer = models.ForeignKey(
        Nightfarer,
        on_delete=models.CASCADE,
        related_name="vessels",
        null=True,
        blank=True,
    )
    slot_1 = models.CharField(max_length=10, choices=SlotColour.choices)
    slot_2 = models.CharField(max_length=10, choices=SlotColour.choices)
    slot_3 = models.CharField(max_length=10, choices=SlotColour.choices)
    deep_slot_1 = models.CharField(max_length=10, choices=SlotColour.choices)
    deep_slot_2 = models.CharField(max_length=10, choices=SlotColour.choices)
    deep_slot_3 = models.CharField(max_length=10, choices=SlotColour.choices)

    class Meta:
        ordering = ["nightfarer__name", "name"]

    def __str__(self) -> str:
        return self.name

    def slot_colour(self, slot: int) -> str:
        fields = {
            1: self.slot_1,
            2: self.slot_2,
            3: self.slot_3,
            4: self.deep_slot_1,
            5: self.deep_slot_2,
            6: self.deep_slot_3,
        }
        return fields[slot]

    def slot_summary(self) -> str:
        standard = ", ".join(self.slot_colour(n).title() for n in STANDARD_SLOTS)
        deep = ", ".join(self.slot_colour(n).title() for n in DEEP_SLOTS)
        return f"{standard} | Deep: {deep}"

    def usable_by(self, nightfarer: Nightfarer) -> bool:
        return self.nightfarer_id is None or self.nightfarer_id == nightfarer.pk


class RelicEffect(models.Model):
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    deep_only = models.BooleanField(
        default=False, help_text="Only rolls on Deep of Night relics."
    )
    is_curse = models.BooleanField(
        default=False, help_text="A negative effect attached to deep relics."
    )
    nightfarer = models.ForeignKey(
        Nightfarer,
        on_delete=models.CASCADE,
        related_name="relic_effects",
        null=True,
        blank=True,
        help_text="Set when the effect only works for one nightfarer.",
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Relic(models.Model):
    MAX_EFFECTS = 3

    class Kind(models.TextChoices):
        UNIQUE = "unique", "Unique"
        SCENE = "scene", "Fixed scene"
        CUSTOM = "custom", "Player-found"

    name = models.CharField(max_length=200)
    slug = models.SlugField(
        unique=True,
        null=True,
        blank=True,
        help_text="Set on catalogued relics so seeding can update them in place.",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.CUSTOM)
    colour = models.CharField(max_length=10, choices=Colour.choices)
    is_deep = models.BooleanField(default=False, help_text="Deep of Night relic.")
    acquisition = models.TextField(blank=True, help_text="How to get it.")
    icon = models.CharField(
        max_length=200, blank=True, help_text="Path under static/, e.g. relics/x.webp"
    )
    effects = models.ManyToManyField(RelicEffect, related_name="relics", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relics",
    )

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self) -> str:
        deep = " (Deep)" if self.is_deep else ""
        return f"{self.name} [{self.get_colour_display()}]{deep}"

    def label(self) -> str:
        """Scene relics share names, so tell them apart by their effects."""
        label = str(self)
        if self.kind == self.Kind.SCENE:
            label += " — " + " · ".join(e.name for e in self.effects.all())
        return label

    def fits_slot(self, slot_colour: str) -> bool:
        return slot_colour == SlotColour.WHITE or slot_colour == self.colour


class Build(models.Model):
    name = models.CharField(max_length=120)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="builds"
    )
    nightfarer = models.ForeignKey(
        Nightfarer, on_delete=models.PROTECT, related_name="builds"
    )
    vessel = models.ForeignKey(Vessel, on_delete=models.PROTECT, related_name="builds")
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("build-detail", args=[self.pk])

    def clean(self) -> None:
        if (
            self.vessel_id
            and self.nightfarer_id
            and not self.vessel.usable_by(self.nightfarer)
        ):
            raise ValidationError(
                {"vessel": f"{self.vessel} can't be used by {self.nightfarer}."}
            )


class BuildRelic(models.Model):
    build = models.ForeignKey(Build, on_delete=models.CASCADE, related_name="slots")
    slot = models.PositiveSmallIntegerField(
        choices=[(n, f"Slot {n}") for n in STANDARD_SLOTS]
        + [(n, f"Deep slot {n - 3}") for n in DEEP_SLOTS]
    )
    relic = models.ForeignKey(Relic, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["slot"]
        constraints = [
            models.UniqueConstraint(fields=["build", "slot"], name="unique_build_slot")
        ]

    def __str__(self) -> str:
        return f"{self.build} – {self.get_slot_display()}: {self.relic}"

    @property
    def is_deep_slot(self) -> bool:
        return self.slot in DEEP_SLOTS

    @property
    def slot_colour(self) -> str:
        return self.build.vessel.slot_colour(self.slot)

    def clean(self) -> None:
        if self.relic.is_deep != self.is_deep_slot:
            kind = "deep" if self.is_deep_slot else "standard"
            raise ValidationError({"relic": f"This slot needs a {kind} relic."})
        if not self.relic.fits_slot(self.slot_colour):
            raise ValidationError(
                {
                    "relic": f"A {self.relic.colour} relic can't go in a "
                    f"{self.slot_colour} slot."
                }
            )
