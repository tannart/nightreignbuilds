from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", views.BuildListView.as_view(), name="build-list"),
    path("builder/", views.BuilderView.as_view(), name="builder"),
    path(
        "builds/new/",
        RedirectView.as_view(pattern_name="builder", permanent=True),
    ),
    path("b/<str:slug>/", views.BuildDetailView.as_view(), name="build-detail"),
    path("b/<str:slug>/edit/", views.BuilderView.as_view(), name="build-update"),
    path("b/<str:slug>/save/", views.BuildPublishView.as_view(), name="build-publish"),
    path("b/<str:slug>/delete/", views.BuildDeleteView.as_view(), name="build-delete"),
    path("relics/", views.RelicListView.as_view(), name="relic-list"),
    path("relics/new/", views.RelicCreateView.as_view(), name="relic-create"),
    path("weapons/", views.WeaponListView.as_view(), name="weapon-list"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
]
