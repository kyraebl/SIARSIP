from django.contrib.auth.views import LoginView
from django.urls import reverse


class MasukView(LoginView):
    """Satu pintu login untuk semua akun. Admin diarahkan ke Kelola Sistem, staf ke dashboard."""
    template_name = "login.html"
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        if self.request.user.is_staff:
            return reverse("admin:index")
        return super().get_default_redirect_url()

    def get_redirect_url(self):
        url = super().get_redirect_url()
        user = self.request.user
        # Staf biasa yang nyasar ke /kelola-sistem/ tidak boleh terjebak loop redirect
        if url and user.is_authenticated and not user.is_staff and url.startswith("/kelola-sistem/"):
            return ""
        return url