from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.widgets import UnfoldAdminPasswordWidget

from .models import UnitKerja, User

admin.site.unregister(Group)   # menu Grup tidak dipakai, akses diatur lewat Peran saja

PERAN = [
    (User.Role.STAF, "Staf bagian (hanya arsip bagiannya)"),
    (User.Role.ADMIN, "Admin (serba bisa)"),
]


class RapikanAkunMixin:
    """Label berbahasa sederhana dan validasi: akun Staf wajib punya bagian."""

    def _rapikan(self):
        self.fields["first_name"].label = "Nama lengkap"
        self.fields["role"].label = "Peran"
        self.fields["role"].choices = PERAN
        self.fields["unit_kerja"].label = "Bagian"
        self.fields["unit_kerja"].empty_label = "Pilih bagian"
        self.fields["unit_kerja"].help_text = "Wajib untuk Staf. Untuk Admin boleh dikosongkan."
        if "is_active" in self.fields:
            self.fields["is_active"].label = "Akun aktif"
            self.fields["is_active"].help_text = "Matikan untuk mencabut akses tanpa menghapus akun."

    def clean(self):
        data = super().clean()
        if data.get("role") == User.Role.STAF and not data.get("unit_kerja"):
            self.add_error("unit_kerja", "Pilih bagian untuk akun Staf.")
        return data


class AkunBaruForm(RapikanAkunMixin, UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rapikan()


class AkunUbahForm(RapikanAkunMixin, UserChangeForm):
    sandi_baru = forms.CharField(
        label="Sandi baru", required=False,
        widget=UnfoldAdminPasswordWidget(attrs={"autocomplete": "new-password"}),
        help_text="Isi hanya kalau mau mengganti sandi akun ini. Kosongkan kalau tidak.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rapikan()
        if self.instance.pk and self.instance.is_superuser:
            self.initial["role"] = User.Role.ADMIN   # superuser bawaan tampil sebagai Admin

    def clean_sandi_baru(self):
        sandi = self.cleaned_data.get("sandi_baru")
        if sandi:
            validate_password(sandi, self.instance)
        return sandi

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("sandi_baru"):
            user.set_password(self.cleaned_data["sandi_baru"])
        if commit:
            user.save()
        return user


@admin.register(User)
class CustomUserAdmin(UserAdmin, ModelAdmin):
    form = AkunUbahForm
    add_form = AkunBaruForm
    change_password_form = AdminPasswordChangeForm
    fieldsets = (
        ("Akun", {"fields": ("username", "first_name", "sandi_baru")}),
        ("Akses", {"fields": ("role", "unit_kerja", "is_active")}),
    )
    add_fieldsets = (
        ("Akun baru", {"classes": ("wide",), "fields": ("username", "first_name", "password1", "password2")}),
        ("Akses", {"fields": ("role", "unit_kerja")}),
    )
    list_display = ("username", "first_name", "unit_kerja", "peran", "is_active")
    list_filter = ("unit_kerja", "role", "is_active")
    search_fields = ("username", "first_name")
    ordering = ("username",)

    @admin.display(description="Peran")
    def peran(self, obj):
        return "Admin (serba bisa)" if obj.is_admin_role else "Staf bagian"

    def save_model(self, request, obj, form, change):
        # Hak akses diatur otomatis dari Peran, jadi tidak ada kotak izin yang perlu dicentang
        admin_role = obj.role == User.Role.ADMIN
        if change and obj.pk == request.user.pk:   # cegah mengunci diri sendiri
            admin_role = True
            obj.role = User.Role.ADMIN
            obj.is_active = True
        obj.is_staff = admin_role
        obj.is_superuser = admin_role
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.pk == request.user.pk:
            return False   # akun sendiri tidak bisa dihapus
        return super().has_delete_permission(request, obj)


@admin.register(UnitKerja)
class UnitKerjaAdmin(ModelAdmin):
    list_display = ("singkatan", "nama", "uraian_bebas")