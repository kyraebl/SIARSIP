from django.contrib.auth.views import LoginView


class MasukView(LoginView):
    """Satu pintu login untuk semua akun. Semua akun masuk ke dashboard web."""
    template_name = "login.html"
    redirect_authenticated_user = True

    def get_redirect_url(self):
        url = super().get_redirect_url()
        user = self.request.user
        if url and user.is_authenticated and not user.is_staff and url.startswith("/kelola-sistem/"):
            return ""
        return url