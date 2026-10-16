from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(
        template_name="login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("arsip.urls")),
    path("kelola-sistem/", admin.site.urls),
]