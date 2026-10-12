from django.urls import path

from . import views

urlpatterns = [
    path("", views.BuildListView.as_view(), name="build-list"),
    path("builds/new/", views.ChooseNightfarerView.as_view(), name="build-choose"),
    path(
        "builds/new/<slug:nightfarer>/",
        views.BuildCreateView.as_view(),
        name="build-create",
    ),
    path("builds/<int:pk>/", views.BuildDetailView.as_view(), name="build-detail"),
    path("builds/<int:pk>/edit/", views.BuildUpdateView.as_view(), name="build-update"),
    path(
        "builds/<int:pk>/delete/",
        views.BuildDeleteView.as_view(),
        name="build-delete",
    ),
    path("relics/", views.RelicListView.as_view(), name="relic-list"),
    path("relics/new/", views.RelicCreateView.as_view(), name="relic-create"),
    path("signup/", views.SignUpView.as_view(), name="signup"),
]
