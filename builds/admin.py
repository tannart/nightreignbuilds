from django.contrib import admin

from .models import Build, BuildRelic, Nightfarer, Relic, RelicEffect, Vessel


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
    list_display = ["name", "deep_only", "is_curse"]
    list_filter = ["deep_only", "is_curse"]
    search_fields = ["name"]


@admin.register(Relic)
class RelicAdmin(admin.ModelAdmin[Relic]):
    list_display = ["name", "colour", "is_deep", "created_by"]
    list_filter = ["colour", "is_deep"]
    search_fields = ["name"]
    filter_horizontal = ["effects"]


class BuildRelicInline(admin.TabularInline[BuildRelic, Build]):
    model = BuildRelic
    extra = 0


@admin.register(Build)
class BuildAdmin(admin.ModelAdmin[Build]):
    list_display = ["name", "nightfarer", "vessel", "author", "created_at"]
    list_filter = ["nightfarer"]
    search_fields = ["name", "author__username"]
    inlines = [BuildRelicInline]
