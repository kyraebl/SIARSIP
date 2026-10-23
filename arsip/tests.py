from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import UnitKerja, User
from master.models import Kategori

from .models import Arsip


class RekapBagianTests(TestCase):
    """Tabel "Total berkas per bagian" di dashboard: jumlah berkas (bks) per bagian per bulan."""

    @classmethod
    def setUpTestData(cls):
        cls.tu = UnitKerja.objects.create(nama="Tata Usaha", singkatan="TU")
        cls.pi = UnitKerja.objects.create(nama="Pelayanan Informasi", singkatan="PI")
        cls.pp = UnitKerja.objects.create(nama="Penyusunan Program", singkatan="PP")
        cls.satker = UnitKerja.objects.create(nama="Satuan Kerja", singkatan="Satker")
        cls.kategori = Kategori.objects.create(kode="HK", nama="Hukum")
        cls.admin = User.objects.create_user("admin1", password="x", role=User.Role.ADMIN)
        cls.staf_tu = User.objects.create_user("staf_tu", password="x", unit_kerja=cls.tu)

        # 2026: TU Jan 2+1, TU Mar 1, PI Jan 1, PI Des 4, Satker Okt 2, PP kosong
        cls.buat(cls.tu, date(2026, 1, 5), 2)
        cls.buat(cls.tu, date(2026, 1, 20), 1)
        cls.buat(cls.tu, date(2026, 3, 1), 1)
        cls.buat(cls.pi, date(2026, 1, 31), 1)
        cls.buat(cls.pi, date(2026, 12, 31), 4)
        cls.buat(cls.satker, date(2026, 10, 15), 2)
        # 2025: tidak boleh ikut terhitung di tahun 2026
        cls.buat(cls.tu, date(2025, 1, 10), 5)

    @classmethod
    def buat(cls, unit, tanggal, jumlah):
        return Arsip.objects.create(
            unit_kerja=unit, kategori=cls.kategori, perihal="Contoh",
            tanggal=tanggal, jumlah=jumlah, created_by=cls.admin,
        )

    def rekap(self, user, **params):
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"), params)
        self.assertEqual(response.status_code, 200)
        return response.context["rekap"], response

    @staticmethod
    def per_unit(rekap):
        return {b["unit"].singkatan: b["bulan"] for b in rekap["baris"]}

    def test_admin_melihat_semua_bagian_per_bulan(self):
        rekap, _ = self.rekap(self.admin, tahun=2026)

        self.assertEqual(self.per_unit(rekap), {
            "TU":     [3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            "PI":     [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4],
            "PP":     [0] * 12,
            "Satker": [0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0],
        })

    def test_urutan_bagian_mengikuti_id(self):
        rekap, _ = self.rekap(self.admin, tahun=2026)

        self.assertEqual([b["unit"].singkatan for b in rekap["baris"]], ["TU", "PI", "PP", "Satker"])

    def test_jumlah_per_bulan_dan_total_kumulatif(self):
        rekap, _ = self.rekap(self.admin, tahun=2026)

        self.assertEqual(rekap["jumlah"], [4, 0, 1, 0, 0, 0, 0, 0, 0, 2, 0, 4])
        self.assertEqual(rekap["total"], [4, 4, 5, 5, 5, 5, 5, 5, 5, 7, 7, 11])

    def test_dua_belas_bulan_termasuk_oktober(self):
        rekap, response = self.rekap(self.admin, tahun=2026)

        self.assertTrue(all(len(b["bulan"]) == 12 for b in rekap["baris"]))
        self.assertContains(response, "Oktober")

    def test_hanya_tahun_yang_dipilih_yang_dihitung(self):
        rekap, _ = self.rekap(self.admin, tahun=2025)

        self.assertEqual(self.per_unit(rekap)["TU"], [5] + [0] * 11)
        self.assertEqual(rekap["total"][-1], 5)

    def test_tahun_tidak_valid_memakai_tahun_ini(self):
        for nilai in ["abc", "99999", "-1", "", "2026.5", "1900", "²", "٢٠٢٦"]:
            with self.subTest(tahun=nilai):
                self.client.force_login(self.admin)
                response = self.client.get(reverse("dashboard"), {"tahun": nilai})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["tahun"], date.today().year)

    def test_pilihan_tahun_berasal_dari_data_ditambah_tahun_ini(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(
            response.context["pilihan_tahun"],
            sorted({2025, 2026, date.today().year}),
        )

    def test_staf_hanya_melihat_bagiannya_sendiri(self):
        rekap, _ = self.rekap(self.staf_tu, tahun=2026)

        self.assertEqual(self.per_unit(rekap), {"TU": [3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
        self.assertEqual(rekap["jumlah"], [3, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(rekap["total"][-1], 4)

    def test_staf_tanpa_unit_kerja_tidak_error(self):
        tanpa_unit = User.objects.create_user("tanpa_unit", password="x")

        rekap, _ = self.rekap(tanpa_unit, tahun=2026)

        self.assertEqual(rekap["baris"], [])
        self.assertEqual(rekap["total"], [0] * 12)

    def test_filter_bagian_daftar_isi_tidak_mengubah_rekap(self):
        rekap, _ = self.rekap(self.admin, tahun=2026, bagian=self.pi.pk)

        self.assertEqual(len(rekap["baris"]), 4)
        self.assertEqual(rekap["total"][-1], 11)

    def test_wajib_login(self):
        response = self.client.get(reverse("dashboard"), {"tahun": 2026})

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_form_daftar_isi_membawa_tahun_terpilih(self):
        _, response = self.rekap(self.admin, tahun=2025)

        self.assertContains(response, '<input type="hidden" name="tahun" value="2025">', html=True)