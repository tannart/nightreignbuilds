from typing import Any

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.cache import patch_vary_headers
from django.views import View, generic

from .forms import BuilderForm, RelicForm, SignUpForm, SlotChoices, SlotForm
from .models import (
    DEEP_SLOTS,
    STANDARD_SLOTS,
    Build,
    BuildRelic,
    Colour,
    Nightfarer,
    Relic,
    RelicEffect,
    Vessel,
    Weapon,
)

LIVE_SEARCH_HEADER = "X-Live-Search"


class BuildListView(generic.ListView[Build]):
    model = Build
    paginate_by = 24

    def get_queryset(self) -> QuerySet[Build]:
        qs = Build.objects.select_related("author", "nightfarer", "vessel")
        author = self.request.GET.get("author")
        # Share links stay out of listings, except on your own page.
        if not (author and author == self.request.user.get_username()):
            qs = qs.filter(is_listed=True)
        if author:
            qs = qs.filter(author__username=author)
        if nightfarer := self.request.GET.get("nightfarer"):
            qs = qs.filter(nightfarer__slug=nightfarer)
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["nightfarers"] = Nightfarer.objects.all()
        context["selected"] = self.request.GET.get("nightfarer", "")
        context["author"] = self.request.GET.get("author", "")
        return context


class BuildDetailView(generic.DetailView[Build]):
    queryset = Build.objects.select_related(
        "author", "nightfarer", "vessel"
    ).prefetch_related("weapons")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        build = self.object
        relics = {
            s.slot: s.relic
            for s in build.slots.select_related("relic").prefetch_related(
                "relic__effects"
            )
        }
        context["standard_slots"] = [
            slot_display(build, n, relics.get(n)) for n in STANDARD_SLOTS
        ]
        context["deep_slots"] = [
            slot_display(build, n, relics.get(n)) for n in DEEP_SLOTS
        ]
        context["is_author"] = (
            build.author_id is not None and build.author_id == self.request.user.pk
        )
        context["share_url"] = self.request.build_absolute_uri(build.get_absolute_url())
        context["just_shared"] = "shared" in self.request.GET
        return context


def slot_display(build: Build, slot: int, relic: Relic | None) -> dict[str, Any]:
    colour = build.slot_colour(slot)
    return {
        "colour": colour,
        "relic": relic,
        "shown": colour or (relic.colour if relic else "white"),
    }


class BuilderView(View):
    """Build from scratch, edit your own build, or remix any build.

    The form has two submit buttons: "save" lists the build under your name,
    "share" stores it unlisted and hands back a link (no login needed)."""

    template_name = "builds/builder.html"

    def get(self, request: HttpRequest, slug: str | None = None) -> HttpResponse:
        build = self.editable_build(slug)
        source = build
        initial: dict[str, Any] = {}
        if remix := request.GET.get("from"):
            source = get_object_or_404(Build, slug=remix)
            initial = remix_initial(source)
        elif build is None and (farer := request.GET.get("nightfarer")):
            initial["nightfarer"] = Nightfarer.objects.filter(slug=farer).first()
        form = BuilderForm(instance=build, initial=initial)
        return self.render(form, self.slot_forms(None, source))

    def post(self, request: HttpRequest, slug: str | None = None) -> HttpResponse:
        build = self.editable_build(slug)
        action = request.POST.get("action", "share")
        form = BuilderForm(request.POST, instance=build)
        slot_forms = self.slot_forms(request.POST, build)
        if not form.is_valid():
            # Still validate the slots, so all errors show at once.
            for slot_form in slot_forms:
                slot_form.is_valid()
            return self.render(form, slot_forms)

        active = [
            s
            for s in slot_forms
            if s.slot in STANDARD_SLOTS or form.cleaned_data["deep_of_night"]
        ]
        if not all([s.is_valid() for s in active]):
            return self.render(form, slot_forms)
        check_slots(form, active)
        if action == "save":
            if not request.user.is_authenticated:
                form.add_error(None, "Log in to save builds, or get a share link.")
            elif not form.cleaned_data["name"].strip():
                form.add_error("name", "Give your build a name to save it.")
        if not form.is_valid() or any(s.errors for s in active):
            return self.render(form, slot_forms)

        build = save_build(form, active, request.user, listed=action == "save")
        if action == "save":
            messages.success(request, f"Saved “{build.name}”.")
            return redirect(build)
        return redirect(f"{build.get_absolute_url()}?shared")

    def editable_build(self, slug: str | None) -> Build | None:
        if slug is None:
            return None
        build = get_object_or_404(Build, slug=slug)
        if build.author_id is None or build.author_id != self.request.user.pk:
            raise PermissionDenied
        return build

    def slot_forms(self, data: Any, source: Build | None) -> list[SlotForm]:
        current = (
            {s.slot: s.relic for s in source.slots.select_related("relic")}
            if source
            else {}
        )
        user = self.request.user
        standard = SlotChoices(user, deep=False, include=current.values())
        deep = SlotChoices(user, deep=True, include=current.values())
        return [
            SlotForm(
                data,
                slot=n,
                choices=deep if n in DEEP_SLOTS else standard,
                initial={"relic": str(current[n].pk)} if n in current else {},
            )
            for n in STANDARD_SLOTS + DEEP_SLOTS
        ]

    def render(self, form: BuilderForm, slot_forms: list[SlotForm]) -> HttpResponse:
        return render(
            self.request,
            self.template_name,
            {
                "form": form,
                "standard_slot_forms": slot_forms[:3],
                "deep_slot_forms": slot_forms[3:],
                "build": form.instance if form.instance.pk else None,
                "nightfarers": Nightfarer.objects.all(),
                "weapon_names": Weapon.objects.values_list("name", flat=True),
                "effect_names": RelicEffect.objects.filter(official=True).values_list(
                    "name", flat=True
                ),
            },
        )


def remix_initial(source: Build) -> dict[str, Any]:
    initial: dict[str, Any] = {
        "name": f"{source.name} (remix)",
        "nightfarer": source.nightfarer,
        "vessel": source.vessel,
        "deep_of_night": source.deep_of_night,
        "description": source.description,
    }
    for n, weapon in enumerate(source.weapons.all(), start=1):
        initial[f"weapon_{n}"] = weapon.name
    return initial


def check_slots(form: BuilderForm, slots: list[SlotForm]) -> None:
    vessel: Vessel | None = form.cleaned_data.get("vessel")
    seen: set[int] = set()
    for slot in slots:
        colour = slot.colour
        if vessel and colour:
            slot_colour = vessel.slot_colour(slot.slot)
            if slot_colour not in ("white", colour):
                field = "custom_colour" if slot.cleaned_data.get("custom") else "relic"
                slot.add_error(
                    field,
                    f"A {colour} relic can't go in this {slot_colour} slot.",
                )
        relic = slot.cleaned_data.get("relic_obj")
        if relic:
            if relic.pk in seen:
                slot.add_error("relic", "The same relic can't be equipped twice.")
            seen.add(relic.pk)


@transaction.atomic
def save_build(
    form: BuilderForm, slots: list[SlotForm], user: Any, listed: bool
) -> Build:
    build = form.save(commit=False)
    is_new = build.pk is None
    if not build.name.strip():
        build.name = f"{build.nightfarer} build"
    if is_new:
        build.author = user if user.is_authenticated else None
        build.is_listed = listed
    elif listed:
        build.is_listed = True
    build.save()
    build.weapons.set(form.cleaned_data["weapons"])
    build.slots.all().delete()
    BuildRelic.objects.bulk_create(
        BuildRelic(build=build, slot=slot.slot, relic=relic)
        for slot in slots
        if (relic := slot.to_relic(user))
    )
    return build


class AuthorRequiredMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        build = self.get_object()  # type: ignore[attr-defined]
        return bool(build.author_id == self.request.user.pk)  # type: ignore[attr-defined]


class BuildPublishView(LoginRequiredMixin, AuthorRequiredMixin, View):
    def get_object(self) -> Build:
        return get_object_or_404(Build, slug=self.kwargs["slug"])

    def post(self, request: HttpRequest, slug: str) -> HttpResponse:
        build = self.get_object()
        build.is_listed = True
        build.save(update_fields=["is_listed", "updated_at"])
        messages.success(request, f"Saved “{build.name}” to your builds.")
        return redirect(build)


class BuildDeleteView(
    LoginRequiredMixin, AuthorRequiredMixin, generic.DeleteView[Build, Any]
):
    model = Build
    success_url = reverse_lazy("build-list")

    def form_valid(self, form: Any) -> HttpResponse:
        messages.success(self.request, f"Deleted “{self.object.name}”.")
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse("build-list") + f"?author={self.request.user.get_username()}"


class RelicCreateView(
    LoginRequiredMixin,
    SuccessMessageMixin[RelicForm],
    generic.CreateView[Relic, RelicForm],
):
    model = Relic
    success_message = "Relic “%(name)s” added to your relics."
    form_class = RelicForm

    def get_success_url(self) -> str:
        return reverse("relic-list") + "?kind=custom"

    def form_valid(self, form: RelicForm) -> HttpResponse:
        form.instance.created_by = self.request.user  # type: ignore[assignment]
        return super().form_valid(form)


class RelicListView(generic.ListView[Relic]):
    paginate_by = 48

    def get_template_names(self) -> list[str]:
        # The live search asks for just the results to swap into the page.
        if self.request.headers.get(LIVE_SEARCH_HEADER):
            return ["builds/_relic_results.html"]
        return super().get_template_names()

    def render_to_response(
        self, context: dict[str, Any], **kwargs: Any
    ) -> HttpResponse:
        response = super().render_to_response(context, **kwargs)
        patch_vary_headers(response, [LIVE_SEARCH_HEADER])
        return response

    def get_queryset(self) -> QuerySet[Relic]:
        # Custom relics are private: you only see your own.
        visible = ~Q(kind=Relic.Kind.CUSTOM)
        if self.request.user.is_authenticated:
            visible |= Q(created_by=self.request.user)
        qs = Relic.objects.filter(visible).prefetch_related("effects")
        if colour := self.request.GET.get("colour"):
            qs = qs.filter(colour=colour)
        if kind := self.request.GET.get("kind"):
            qs = qs.filter(kind=kind)
        if query := self.request.GET.get("q", "").strip():
            qs = qs.filter(
                Q(name__icontains=query) | Q(effects__name__icontains=query)
            ).distinct()
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        kinds = [(Relic.Kind.UNIQUE, "Unique"), (Relic.Kind.SCENE, "Fixed scene")]
        if self.request.user.is_authenticated:
            kinds.append((Relic.Kind.CUSTOM, "My relics"))
        context["colours"] = Colour.choices
        context["selected"] = self.request.GET.get("colour", "")
        context["kinds"] = kinds
        context["kind"] = self.request.GET.get("kind", "")
        context["query"] = self.request.GET.get("q", "")
        return context


class WeaponListView(generic.ListView[Weapon]):
    paginate_by = 60

    def get_queryset(self) -> QuerySet[Weapon]:
        qs = Weapon.objects.all()
        if category := self.request.GET.get("category"):
            qs = qs.filter(category=category)
        if query := self.request.GET.get("q", "").strip():
            qs = qs.filter(name__icontains=query)
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["categories"] = (
            Weapon.objects.order_by("category")
            .values_list("category", flat=True)
            .distinct()
        )
        context["category"] = self.request.GET.get("category", "")
        context["query"] = self.request.GET.get("q", "")
        return context


class SignUpView(generic.CreateView[User, SignUpForm]):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("build-list")

    def form_valid(self, form: SignUpForm) -> HttpResponse:
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
