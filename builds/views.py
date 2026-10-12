from typing import Any

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import generic

from .forms import BuildForm, RelicForm, SignUpForm
from .models import Build, Nightfarer, Relic


class BuildListView(generic.ListView[Build]):
    model = Build
    paginate_by = 24

    def get_queryset(self) -> QuerySet[Build]:
        qs = Build.objects.select_related("author", "nightfarer", "vessel")
        if nightfarer := self.request.GET.get("nightfarer"):
            qs = qs.filter(nightfarer__slug=nightfarer)
        if author := self.request.GET.get("author"):
            qs = qs.filter(author__username=author)
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["nightfarers"] = Nightfarer.objects.all()
        context["selected"] = self.request.GET.get("nightfarer", "")
        return context


class BuildDetailView(generic.DetailView[Build]):
    queryset = Build.objects.select_related("author", "nightfarer", "vessel")

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
            (build.vessel.slot_colour(n), relics.get(n)) for n in (1, 2, 3)
        ]
        context["deep_slots"] = [
            (build.vessel.slot_colour(n), relics.get(n)) for n in (4, 5, 6)
        ]
        return context


class ChooseNightfarerView(LoginRequiredMixin, generic.ListView[Nightfarer]):
    model = Nightfarer
    template_name = "builds/choose_nightfarer.html"


class BuildCreateView(LoginRequiredMixin, generic.CreateView[Build, BuildForm]):
    model = Build
    form_class = BuildForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["nightfarer"] = get_object_or_404(
            Nightfarer, slug=self.kwargs["nightfarer"]
        )
        return kwargs

    def form_valid(self, form: BuildForm) -> HttpResponse:
        form.instance.author = self.request.user  # type: ignore[assignment]
        return super().form_valid(form)


class AuthorRequiredMixin(UserPassesTestMixin):
    def test_func(self) -> bool:
        build = self.get_object()  # type: ignore[attr-defined]
        return bool(build.author_id == self.request.user.pk)  # type: ignore[attr-defined]


class BuildUpdateView(
    LoginRequiredMixin, AuthorRequiredMixin, generic.UpdateView[Build, BuildForm]
):
    model = Build
    form_class = BuildForm

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["nightfarer"] = self.object.nightfarer
        return kwargs


class BuildDeleteView(
    LoginRequiredMixin, AuthorRequiredMixin, generic.DeleteView[Build, Any]
):
    model = Build
    success_url = reverse_lazy("build-list")


class RelicCreateView(LoginRequiredMixin, generic.CreateView[Relic, RelicForm]):
    model = Relic
    form_class = RelicForm
    success_url = reverse_lazy("relic-list")

    def form_valid(self, form: RelicForm) -> HttpResponse:
        form.instance.created_by = self.request.user  # type: ignore[assignment]
        return super().form_valid(form)


class RelicListView(generic.ListView[Relic]):
    queryset = Relic.objects.prefetch_related("effects")
    paginate_by = 50


class SignUpView(generic.CreateView[User, SignUpForm]):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("build-list")

    def form_valid(self, form: SignUpForm) -> HttpResponse:
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
