from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from accounts.views import MasukView

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

urlpatterns = [
    path("login/", MasukView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("kelola-sistem/login/", RedirectView.as_view(pattern_name="login", query_string=True)),
    path("", include("arsip.urls")),
    path("kelola-sistem/accounts/", RedirectView.as_view(pattern_name="admin:arsip_arsip_dashboard")),
    path("kelola-sistem/arsip/", RedirectView.as_view(pattern_name="admin:arsip_arsip_dashboard")),
    path("kelola-sistem/master/", RedirectView.as_view(pattern_name="admin:arsip_arsip_dashboard")),
    path("kelola-sistem/", RedirectView.as_view(pattern_name="admin:arsip_arsip_dashboard")),  # baru, harus di atas include admin
    path("kelola-sistem/", admin.site.urls),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)