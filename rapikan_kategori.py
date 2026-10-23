from django.db import transaction

from arsip.models import Arsip
from master.models import Kategori

PAKAI = ["HK", "HM", "KP", "KU", "OR", "PA", "PR", "PS", "PW", "UM", "SA", "SM"]

with transaction.atomic():
    ada = set(Kategori.objects.values_list("kode", flat=True))
    for kode in PAKAI:
        if kode not in ada:
            print(f"PERHATIAN: {kode} belum ada di database")
    for pos, kode in enumerate(PAKAI):
        Kategori.objects.filter(kode=kode).update(urutan=pos)
    for k in Kategori.objects.exclude(kode__in=PAKAI):
        n = Arsip.objects.filter(kategori=k).count()
        if n:
            print(f"DILEWATI {k.kode}: masih dipakai {n} arsip")
        else:
            k.delete()
            print(f"Dihapus {k.kode}")

for k in Kategori.objects.all():
    print(f"{k.urutan + 1:>2}. {k.kode}  {k.nama}")