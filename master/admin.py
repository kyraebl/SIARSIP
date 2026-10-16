from django.contrib import admin
from django.db.models import Max
from unfold.admin import ModelAdmin

from .models import Kategori, KodeTujuan, Pengesah


@admin.register(KodeTujuan)
class KodeTujuanAdmin(ModelAdmin):
    list_display = ("kode", "nama_jabatan")
    search_fields = ("kode", "nama_jabatan")


@admin.register(Kategori)
class KategoriAdmin(ModelAdmin):
    list_display = ("kode", "nama")
    list_display_links = ("kode",)
    sortable_by = ()          # urutan tampil mengikuti urutan yang sudah ditetapkan, tidak bisa diacak lewat judul kolom
    list_per_page = 1000
    exclude = ("urutan",)

    def save_model(self, request, obj, form, change):
        if not change:   # kategori baru otomatis ditaruh di urutan paling bawah
            obj.urutan = (Kategori.objects.aggregate(Max("urutan"))["urutan__max"] or -1) + 1
        super().save_model(request, obj, form, change)


@admin.register(Pengesah)
class PengesahAdmin(ModelAdmin):
    list_display = ("unit_kerja", "jabatan", "nama", "nip")