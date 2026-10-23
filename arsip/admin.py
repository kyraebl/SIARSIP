from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db.models import Max, Min
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.urls import path
from unfold.admin import ModelAdmin

from accounts.models import UnitKerja
from .exports import BULAN
from .forms import ImportExcelForm
from .importer import ImportGagal, proses_import
from .models import Arsip
from .views import _tahun, rekap_bagian, rekap_jenis_sifat, rekap_klasifikasi


@admin.register(Arsip)
class ArsipAdmin(ModelAdmin):
    list_display = ("kode_klasifikasi", "uraian", "tanggal", "jumlah",
                    "keterangan", "keamanan", "unit_kerja")
    list_filter = ("unit_kerja", "keamanan", "keterangan")
    search_fields = ("perihal", "nomor_surat", "uraian")
    readonly_fields = ("uraian",)
    list_before_template = "admin/arsip/export_panel.html"

    def _rekap(self, request):
        """Tabel rekap yang sama dengan dashboard web."""
        semua = Arsip.objects.all()
        tahun, pilihan_tahun = _tahun(request, semua)
        bulan = request.GET.get("bulan", "")
        bulan = int(bulan) if bulan.isdigit() and 1 <= int(bulan) <= 12 else None

        units = UnitKerja.objects.order_by("id")
        bag = rekap_bagian(semua, units, tahun)
        klas = rekap_klasifikasi(semua, units, tahun, bulan)
        js = rekap_jenis_sifat(semua, units, tahun, bulan)

        def tabel(uid, judul, grup, kolom, baris, data, **extra):
            return {"uid": uid, "judul": judul, "grup": grup, "kolom": kolom,
                    "baris": [(b["unit"].singkatan, b[baris]) for b in data["baris"]],
                    "jumlah": data["jumlah"], "total_semua": data["total_semua"], **extra}

        return {
            "rekap_tabel": [
                tabel("bagian", "Total berkas per bagian", None, [b.title() for b in BULAN], "bulan", bag,
                      penuh=True, pakai_no=True),
                tabel("klasifikasi", "Total berkas per klasifikasi", "Klasifikasi Jenis Berkas",
                      klas["kategori"], "kategori", klas, penuh=True, filter_bulan=True),
                tabel("jenis", "Total berkas per jenis", "Jenis", js["jenis"]["kolom"], "nilai",
                      js["jenis"], filter_bulan=True),
                tabel("sifat", "Total berkas per sifat", "Sifat", js["sifat"]["kolom"], "nilai",
                      js["sifat"], filter_bulan=True),
            ],
            "rekap_tahun": tahun,
            "rekap_pilihan_tahun": pilihan_tahun,
            "rekap_bulan": bulan,
            "rekap_nama_bulan": [b.title() for b in BULAN],
        }

    def get_urls(self):
        custom = [
            path("dashboard/", self.admin_site.admin_view(self.dashboard_view),
                 name="arsip_arsip_dashboard"),
            path("import/", self.admin_site.admin_view(self.import_view),
                 name="arsip_arsip_import"),
        ]
        return custom + super().get_urls()

    def dashboard_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied
        context = {**self.admin_site.each_context(request), "title": "Dashboard",
                   **self._rekap(request)}
        return TemplateResponse(request, "admin/arsip/dashboard.html", context)

    def import_view(self, request):
        """Import Excel dari halaman admin. Bagian tujuan dipilih manual karena superadmin tidak punya unit kerja."""
        if request.method != "POST" or not self.has_add_permission(request):
            raise PermissionDenied
        tmpl = "admin/arsip/_hasil_import.html"
        uid = request.POST.get("unit", "")
        unit = UnitKerja.objects.filter(pk=uid).first() if uid.isdigit() else None
        if not unit:
            return render(request, tmpl, {"error": "Pilih bagian tujuan dulu."})
        form = ImportExcelForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, tmpl, {"error": form.errors["file"][0]})
        simpan = request.POST.get("simpan") == "1"
        try:
            hasil = proses_import(form.cleaned_data["file"], request.user, simpan=simpan, unit=unit)
        except ImportGagal as e:
            return render(request, tmpl, {"error": str(e)})
        return render(request, tmpl, {
            "hasil": hasil, "simpan": simpan, "unit": unit,
            "cek_awal": bool(hasil["galat"] or hasil["belum_nomor"]),
        })

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