"""Urutkan kode klasifikasi sesuai daftar di bawah. Aman dijalankan berulang kali.

Jalankan dari folder project (yang ada manage.py):
    python manage.py shell -c "exec(open('urutkan_kategori.py', encoding='utf-8').read())"
"""
from django.db import transaction

from master.models import Kategori

# (kode, nama). Nama hanya dipakai kalau kodenya belum ada di database.
URUTAN = [
    ("HK", "Hukum"),
    ("HL", "Hubungan Luar Negeri"),
    ("HM", "Humas"),
    ("KP", "Kepegawaian"),
    ("KU", "Keuangan"),
    ("OR", "Organisasi"),
    ("PA", "Pengolahan Data"),
    ("PB", "Pengadaan Barang/Jasa"),
    ("PM", "Penanaman Modal"),
    ("PR", "Perencanaan"),
    ("PS", "Pengelolaan Aset Barang Milik Negara"),
    ("PW", "Pengawasan"),
    ("UM", "Umum"),
    ("SA", "Sumber Daya Air"),
    ("BM", "Bina Marga"),
    ("CK", "Cipta Karya"),
    ("RU", "Perumahan"),
    ("BK", "Bina Konstruksi"),
    ("IW", "Pengembangan Infrastruktur Wilayah"),
    ("LB", "Penelitian dan Pengembangan"),
    ("SM", "Pengembangan Sumber Daya Manusia"),
]

with transaction.atomic():
    dibuat_baru = []
    for pos, (kode, nama) in enumerate(URUTAN):
        k, dibuat = Kategori.objects.get_or_create(kode=kode, defaults={"nama": nama, "urutan": pos})
        if dibuat:
            dibuat_baru.append(kode)
        elif k.urutan != pos:
            k.urutan = pos
            k.save(update_fields=["urutan"])

    sisa = Kategori.objects.exclude(kode__in=[kode for kode, _ in URUTAN]).order_by("urutan", "kode")
    for pos, k in enumerate(sisa, start=len(URUTAN)):
        if k.urutan != pos:
            k.urutan = pos
            k.save(update_fields=["urutan"])

print("Kategori baru dibuat:", ", ".join(dibuat_baru) or "-")
print("Urutan sekarang:")
for k in Kategori.objects.all():
    print(f"  {k.urutan + 1:>2}. {k.kode}  {k.nama}")