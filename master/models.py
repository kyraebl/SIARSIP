from django.db import models
from accounts.models import UnitKerja


class KodeTujuan(models.Model):
    kode = models.CharField(max_length=10, unique=True)      # Aa, Aa1, ...
    nama_jabatan = models.CharField(max_length=150)          # Kepala Sekretariat DSDAN

    class Meta:
        verbose_name_plural = "Pejabat penandatanganan"
        ordering = ["kode"]

    def __str__(self):
        return f"{self.kode} - {self.nama_jabatan}"


class Kategori(models.Model):
    kode = models.CharField(max_length=5, unique=True)       # HK, HM, KP, ...
    nama = models.CharField(max_length=100, blank=True)
    urutan = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Kategori klasifikasi"
        ordering = ["urutan", "kode"]

    def __str__(self):
        return self.kode


class Pengesah(models.Model):
    unit_kerja = models.OneToOneField(UnitKerja, on_delete=models.CASCADE)
    jabatan = models.CharField(max_length=150, default="Kepala Sub Bagian Tata Usaha")
    nama = models.CharField(max_length=100)
    nip = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name_plural = "Pengesah"

    def __str__(self):
        return f"{self.unit_kerja} - {self.nama}"