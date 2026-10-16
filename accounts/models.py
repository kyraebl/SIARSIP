from django.contrib.auth.models import AbstractUser
from django.db import models


class UnitKerja(models.Model):
    nama = models.CharField(max_length=100)
    singkatan = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name_plural = "Unit kerja"

    def __str__(self):
        return self.singkatan

    uraian_bebas = models.BooleanField(
        "Uraian ditulis bebas", default=False,
        help_text="Centang untuk unit yang uraiannya tidak berformat surat (contoh: SPM NO. 01 Pembayaran ...). "
                  "Unit ini tidak memakai Pejabat Penandatanganan dan Nomor Surat.",
    )


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        STAF = "staf", "Staf"

    unit_kerja = models.ForeignKey(
        UnitKerja, null=True, blank=True,
        on_delete=models.PROTECT, related_name="users",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAF)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser