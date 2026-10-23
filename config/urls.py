from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic import RedirectView

from accounts.views import MasukView

urlpatterns = [
    path("login/", MasukView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("kelola-sistem/login/", RedirectView.as_view(pattern_name="login", query_string=True)),
    path("", include("arsip.urls")),
    path("kelola-sistem/accounts/", RedirectView.as_view(pattern_name="admin:index")),
    path("kelola-sistem/arsip/", RedirectView.as_view(pattern_name="admin:index")),
    path("kelola-sistem/master/", RedirectView.as_view(pattern_name="admin:index")),
    path("kelola-sistem/", admin.site.urls),
]