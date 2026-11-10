from fileinput import filename
import uuid
import os
import re
import uuid

from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from accounts.models import UnitKerja
from accounts.models import User
from master.models import KodeTujuan, Kategori

def generate_file_path(instance, filename):
    """
    Fungsi ini akan menghasilkan struktur folder:
    berkas/<Singkatan_Unit_Kerja>/<Kode_Klasifikasi>/<Nama_File_Asli>
    Contoh: berkas/PI/KP/Surat_Cuti.pdf
    """
    
    try:
        nama_unit = instance.unit_kerja.singkatan.strip().upper()
    except AttributeError:
        nama_unit = "UMUM"

    try:
        klasifikasi = instance.kategori.kode.strip().upper()
    except AttributeError:
        klasifikasi = "LAINNYA"

    file_path = os.path.join('berkas', str(nama_unit), str(klasifikasi), filename)
    
    return file_path

def path_berkas(instance, filename):
    """Menyimpan file ke dalam folder unit kerja dengan nama aslinya."""
    dasar, ext = os.path.splitext(os.path.basename(filename))
    dasar = re.sub(r"[^\w\s().\-]", "", dasar).strip()[:45] or "berkas"
    return f"berkas/{instance.unit_kerja_id}/{dasar}{ext}"

class ArsipQuerySet(models.QuerySet):
    def untuk(self, user):
        """Filter wewenang: admin lihat semua, staf hanya unitnya sendiri."""
        if user.is_admin_role:
            return self
        return self.filter(unit_kerja=user.unit_kerja)

    def periode(self, bulan_awal, bulan_akhir=None):
        """bulan_awal/bulan_akhir berupa date tanggal 1. Satu bulan jika akhir kosong."""
        from dateutil.relativedelta import relativedelta
        akhir = bulan_akhir or bulan_awal
        batas = akhir + relativedelta(months=1)
        return self.filter(tanggal__gte=bulan_awal, tanggal__lt=batas)


class Arsip(models.Model):
    class Keterangan(models.TextChoices):
        ASLI = "asli", "Asli"
        COPY = "copy", "Copy"

    class Keamanan(models.TextChoices):
        TERBUKA = "terbuka", "Biasa/Umum/Terbuka"
        TERBATAS = "terbatas", "Terbatas"
        RAHASIA = "rahasia", "Rahasia"

    unit_kerja = models.ForeignKey(UnitKerja, on_delete=models.PROTECT, related_name="arsip")
    kode_tujuan = models.ForeignKey(KodeTujuan, on_delete=models.PROTECT, null=True, blank=True)   
    kategori = models.ForeignKey(Kategori, on_delete=models.PROTECT)
    sub_kode = models.CharField(
        max_length=6, blank=True,
        validators=[RegexValidator(r"^\d*$", "Sub-kode hanya boleh angka.")],
    )  
    nomor_surat = models.CharField(max_length=30, blank=True)   
    perihal = models.TextField()
    uraian = models.TextField(editable=False)   
    tanggal = models.DateField()
    jumlah = models.PositiveIntegerField(default=1)
    keterangan = models.CharField(max_length=10, choices=Keterangan.choices, default=Keterangan.ASLI)
    keamanan = models.CharField(max_length=10, choices=Keamanan.choices, default=Keamanan.TERBUKA)
    berkas = models.FileField(upload_to=generate_file_path, null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ArsipQuerySet.as_manager()

    class Meta:
        verbose_name_plural = "Arsip"
        ordering = ["kategori__kode", "sub_kode", "tanggal"]
        indexes = [models.Index(fields=["unit_kerja", "tanggal"])]

    @property
    def kode_klasifikasi(self):
        if self.kode_tujuan_id is None:   
            return f"{self.kategori.kode} {self.sub_kode}".strip()
        return f"{self.kategori.kode}{self.sub_kode}"

    @property
    def catatan(self):
        """Daftar kekurangan data arsip: list of (kode, teks)."""
        c = []
        if self.kode_tujuan_id and not self.nomor_surat:
            c.append(("nomor", "Nomor surat belum keluar"))
            
        file_ada = False
        if self.berkas:
            import os
            from django.conf import settings
            full_path = os.path.join(settings.MEDIA_ROOT, self.berkas.name)
            if os.path.exists(full_path):
                file_ada = True
                
        if not file_ada:
            c.append(("berkas", "Soft file belum diunggah"))
            
        return c

    @property
    def file_fisik_ada(self):
        """Mengecek apakah file benar-benar ada di folder local"""
        if not self.berkas:
            return False
        import os
        from django.conf import settings
        full_path = os.path.join(settings.MEDIA_ROOT, self.berkas.name)
        return os.path.exists(full_path)
    
    @property
    def warna_baris(self):
        """Kelas warna latar baris di tabel. Kosong kalau data sudah lengkap."""
        kode = [k for k, _ in self.catatan]
        if "nomor" in kode:
            return "bg-amber-50"
        if "berkas" in kode:
            return "bg-sky-50"
        return ""

    @property
    def jumlah_tampil(self):
        return f"{self.jumlah} bks"

    def rangkai_uraian(self):
        if self.kode_tujuan_id is None:   
            return self.perihal.strip()
        return (
            f"Surat {self.kode_tujuan.nama_jabatan} "
            f"No: {self.kode_klasifikasi}-{self.kode_tujuan.kode}/{self.nomor_surat} "
            f"Hal {self.perihal.strip()}"
        )

    def save(self, *args, **kwargs):
        self.uraian = self.rangkai_uraian()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        berkas = self.berkas
        super().delete(*args, **kwargs)
        if berkas: 
            berkas.delete(save=False)

    def __str__(self):
        return self.uraian[:80]