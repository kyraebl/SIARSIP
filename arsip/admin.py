from django.contrib import admin
from django.db.models import Max, Min
from unfold.admin import ModelAdmin

from accounts.models import UnitKerja
from .models import Arsip


@admin.register(Arsip)
class ArsipAdmin(ModelAdmin):
    list_display = ("kode_klasifikasi", "uraian", "tanggal", "jumlah",
                    "keterangan", "keamanan", "unit_kerja")
    list_filter = ("unit_kerja", "keamanan", "keterangan")
    search_fields = ("perihal", "nomor_surat", "uraian")
    readonly_fields = ("uraian",)
    list_before_template = "admin/arsip/export_panel.html"   # kotak Export Excel di atas daftar

    def changelist_view(self, request, extra_context=None):
        batas = Arsip.objects.aggregate(a=Min("tanggal"), b=Max("tanggal"))
        extra_context = {
            **(extra_context or {}),
            "export_units": UnitKerja.objects.order_by("id"),
            "export_dari": f"{batas['a']:%Y-%m}" if batas["a"] else "",
            "export_sampai": f"{batas['b']:%Y-%m}" if batas["b"] else "",
        }
        return super().changelist_view(request, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_exclude(self, request, obj=None):
        return ("created_by",)