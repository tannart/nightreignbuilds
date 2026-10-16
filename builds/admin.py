from django.contrib import admin

from .models import (
    Build,
    BuildRelic,
    Nightfarer,
    Relic,
    RelicCurse,
    RelicEffect,
    Vessel,
    Weapon,
)


class VesselInline(admin.TabularInline[Vessel, Nightfarer]):
    model = Vessel
    extra = 0
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Nightfarer)
class NightfarerAdmin(admin.ModelAdmin[Nightfarer]):
    list_display = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [VesselInline]


@admin.register(Vessel)
class VesselAdmin(admin.ModelAdmin[Vessel]):
    list_display = [
        "name",
        "nightfarer",
        "slot_1",
        "slot_2",
        "slot_3",
        "deep_slot_1",
        "deep_slot_2",
        "deep_slot_3",
    ]
    list_filter = ["nightfarer"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(RelicEffect)
class RelicEffectAdmin(admin.ModelAdmin[RelicEffect]):
    list_display = ["name", "nightfarer", "official", "deep_only", "is_curse"]
    list_filter = ["official", "nightfarer", "deep_only", "is_curse"]
    search_fields = ["name"]


class RelicCurseInline(admin.TabularInline[RelicCurse, Relic]):
    model = RelicCurse
    extra = 0


@admin.register(Relic)
class RelicAdmin(admin.ModelAdmin[Relic]):
    inlines = [RelicCurseInline]
    list_display = ["name", "kind", "colour", "is_deep", "created_by"]
    list_filter = ["kind", "colour", "is_deep"]
    search_fields = ["name"]
    filter_horizontal = ["effects"]


class BuildRelicInline(admin.TabularInline[BuildRelic, Build]):
    model = BuildRelic
    extra = 0


@admin.register(Build)
class BuildAdmin(admin.ModelAdmin[Build]):
    list_display = [
        "name",
        "slug",
        "nightfarer",
        "author",
        "is_listed",
        "deep_of_night",
        "created_at",
    ]
    list_filter = ["is_listed", "deep_of_night", "nightfarer"]
    search_fields = ["name", "slug", "author__username"]
    readonly_fields = ["slug"]
    filter_horizontal = ["weapons"]
    inlines = [BuildRelicInline]


@admin.register(Weapon)
class WeaponAdmin(admin.ModelAdmin[Weapon]):
    list_display = ["name", "category"]
    list_filter = ["category"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
