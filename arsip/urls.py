from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("arsip/", views.arsip_list, name="arsip_list"),
    path("arsip/tambah/", views.arsip_form, name="arsip_tambah"),
    path("arsip/<int:pk>/ubah/", views.arsip_form, name="arsip_ubah"),
    path("arsip/<int:pk>/hapus/", views.arsip_hapus, name="arsip_hapus"),
    path("export/", views.arsip_export, name="arsip_export"),
    path("arsip/<int:pk>/berkas/", views.arsip_berkas, name="arsip_berkas"),
    path("import/", views.arsip_import, name="arsip_import"),
    path("rekap/export/", views.rekap_export, name="rekap_export"),
    path("arsip-inaktif/", views.arsip_inaktif_list, name="arsip_inaktif_list"),
    path("arsip-inaktif/tambah/", views.arsip_inaktif_form, name="arsip_inaktif_tambah"),
    path("arsip-inaktif/<int:pk>/ubah/", views.arsip_inaktif_form, name="arsip_inaktif_ubah"),
    path("arsip-inaktif/<int:pk>/hapus/", views.arsip_inaktif_hapus, name="arsip_inaktif_hapus"),
    path("arsip-inaktif/import/", views.arsip_inaktif_import, name="arsip_inaktif_import"),
    path("arsip-inaktif/export/", views.arsip_inaktif_export, name="arsip_inaktif_export"),
]