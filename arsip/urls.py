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
    path('export-total-excel/', views.export_total_excel, name='export_total_excel'),
    path('export-total-pdf/', views.export_total_pdf, name='export_total_pdf'),
    path("rekap/export/", views.rekap_export, name="rekap_export"),
]