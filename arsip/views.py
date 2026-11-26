import openpyxl

from django.http import HttpResponse

from accounts.models import UnitKerja
from googleapiclient.errors import HttpError
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils.formats import date_format
from datetime import date
from functools import wraps
from io import BytesIO
from itertools import accumulate, groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from django.db.models import Max, Q, Sum
from django.db.models.functions import ExtractMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from master.models import Kategori, KodeTujuan, Pengesah
from openpyxl import Workbook
from openpyxl.styles import Font

from .exports import BULAN, KOTAK, TENGAH, buat_excel, buat_excel_inaktif, buat_excel_rekap, buat_excel_rekap_gabung, buat_pdf_rekap, buat_pdf, buat_pdf_inaktif, label_periode
from .models import Arsip, ArsipInaktif
from .forms import ArsipForm, ArsipInaktifForm, ImportExcelForm
from .importer import ImportGagal, proses_import, proses_import_inaktif

URUTAN = ("kategori__urutan", "kategori__kode", "sub_kode", "tanggal", "id")

def bukan_atasan(view):
    """Atasan hanya boleh lihat rekap, tidak boleh menyentuh isi arsip."""
    @wraps(view)
    def _w(request, *a, **kw):
        if request.user.is_atasan:
            raise PermissionDenied
        return view(request, *a, **kw)
    return _w

def _unit_tujuan(request, user):
    """Unit tujuan data baru. Staf: unitnya sendiri. Admin tanpa unit: dipilih lewat parameter unit."""
    if user.unit_kerja:
        return user.unit_kerja
    if user.is_admin_role:
        pk = request.POST.get("unit") or request.GET.get("unit")
        if pk and pk.isdigit():
            return UnitKerja.objects.filter(pk=pk).first()
    return None

def _modal_pilih_unit(request, judul):
    return render(request, "arsip/_modal_pilih_unit.html", {
        "judul": judul, "url": request.path,
        "unit_list": UnitKerja.objects.order_by("singkatan"),
    })

def susun_tabel(qs):
    """Kelompokkan per kategori > kode klasifikasi, lengkap dengan No. Berkas dan No. Item."""
    grup = []
    for _, per_kat in groupby(qs, key=lambda a: a.kategori_id):
        per_kat = list(per_kat)
        berkas = []
        for no, (_, per_kode) in enumerate(groupby(per_kat, key=lambda a: a.sub_kode), start=1):
            per_kode = list(per_kode)
            berkas.append({
                "no": no,
                "kode": per_kode[0].kode_klasifikasi,
                "baris": list(enumerate(per_kode, start=1)),
            })
        grup.append({"kategori": per_kat[0].kategori, "berkas": berkas})
    return grup


def _bulan(teks):
    try:
        y, m = map(int, teks.split("-"))
        return date(y, m, 1)
    except (ValueError, AttributeError):
        return None


def _bulan_berikut(d):
    return date(d.year + (d.month == 12), d.month % 12 + 1, 1)


def _periode(request, qs):
    """Ambil rentang bulan dari ?dari=&sampai=. Default: bulan berjalan."""
    awal = _bulan(request.GET.get("dari"))
    akhir = _bulan(request.GET.get("sampai"))
    if not awal:
        awal = date.today().replace(day=1)
    akhir = akhir or awal
    if akhir < awal:
        awal, akhir = akhir, awal
    return awal, akhir


def _filter_periode(qs, awal, akhir):
    return qs.filter(tanggal__gte=awal, tanggal__lt=_bulan_berikut(akhir))

def _cari(qs, q):
    """Cari di uraian (nomor surat, perihal, dan seterusnya). Kosong = tidak difilter."""
    q = (q or "" ).strip()
    return qs.filter(uraian__icontains=q) if q else qs

def buat_lembar(data, unit, awal, akhir, mode, awalan=""):
    """Kumpulan tab Excel untuk satu kelompok data. unit=None berarti gabungan semua bagian.

    mode "gabung" = satu tab untuk seluruh rentang, selain itu satu tab per bulan.
    """
    gabungan = unit is None
    pengesah = None if gabungan else Pengesah.objects.filter(unit_kerja=unit).first()
    unit_label = "SEMUA BAGIAN" if gabungan else unit.nama.upper()

    def ambil(dari, sampai):
        per = (_filter_periode(data, dari, sampai)
               .select_related("kategori", "kode_tujuan", "unit_kerja")
               .order_by(*URUTAN))
        return susun_tabel(per)

    def tab(nama, dari, sampai, grup):
        bulan_label, tahun_label = label_periode(dari, sampai)
        return {"nama": nama, "unit_label": unit_label, "bulan": bulan_label,
                "tahun": tahun_label, "grup": grup, "pengesah": pengesah, "gabungan": gabungan}

    hasil = []
    if mode == "gabung":
        grup = ambil(awal, akhir)
        if grup:
            hasil.append(tab(awalan.strip(" -") or "Daftar Isi Berkas", awal, akhir, grup))
    else:
        banyak_tahun = awal.year != akhir.year
        b = awal
        while b <= akhir:
            grup = ambil(b, b)
            if grup:
                nama = awalan + BULAN[b.month - 1].title()
                if banyak_tahun:
                    nama += f" {b.year}"
                hasil.append(tab(nama, b, b, grup))
            b = _bulan_berikut(b)
    return hasil

def _kirim_file(request, lembar, nama_file, buat_excel_fn, buat_pdf_fn):
    """Kirim hasil export sebagai Excel atau PDF sesuai ?tipe=. Isinya sama, hanya bentuk file."""
    if request.GET.get("tipe") == "pdf":
        data, jenis, ekstensi = buat_pdf_fn(lembar), "application/pdf", "pdf"
    else:
        data, ekstensi = buat_excel_fn(lembar), "xlsx"
        jenis = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    resp = HttpResponse(data, content_type=jenis)
    resp["Content-Disposition"] = f'attachment; filename="{nama_file}.{ekstensi}"'
    return resp

def _bagian(request, qs):
    """Filter bagian untuk admin: ?bagian=semua atau ?bagian=<id unit>. Staf selalu unitnya sendiri."""
    if not request.user.is_admin_role:
        return qs, "semua", None
    pilih = request.GET.get("bagian", "semua")
    unit = UnitKerja.objects.filter(pk=int(pilih)).first() if pilih.isdigit() else None
    if unit:
        return qs.filter(unit_kerja=unit), str(unit.pk), unit
    return qs, "semua", None

def _tahun(request, qs):
    """Tahun rekap dari ?tahun=. Hanya tahun yang ada datanya (atau tahun ini) yang diterima."""
    ini = date.today().year
    pilihan = sorted({d.year for d in qs.dates("tanggal", "year")} | {ini})
    t = request.GET.get("tahun", "")
    return (int(t) if t.isascii() and t.isdigit() and int(t) in pilihan else ini), pilihan

def rekap_bagian(qs, units, tahun):
    """Total berkas (jumlah bks) per bagian per bulan di satu tahun, plus jumlah per bulan dan total kumulatif."""
    hasil = (qs.filter(tanggal__year=tahun)
               .annotate(bln=ExtractMonth("tanggal"))
               .order_by()
               .values("unit_kerja_id", "bln")
               .annotate(total=Sum("jumlah")))
    isi = {(r["unit_kerja_id"], r["bln"]): r["total"] for r in hasil}
    baris = [{"unit": u, "bulan": [isi.get((u.pk, b), 0) for b in range(1, 13)]} for u in units]
    jumlah = [sum(b["bulan"][i] for b in baris) for i in range(12)]
    return {"baris": baris, "jumlah": jumlah, "total": list(accumulate(jumlah)),
            "total_semua": sum(jumlah)}

KLASIFIKASI_REKAP = [
    ("HK", "Hukum (HK)"),
    ("HM", "Humas (HM)"),
    ("KP", "Kepegawaian (KP)"),
    ("KU", "Keuangan (KU)"),
    ("OR", "Organisasi (OR)"),
    ("PA", "Pengelolaan Data (PA)"),
    ("PR", "Perencanaan (PR)"),
    ("PS", "Pengelolaan Aset BMN (PS)"),
    ("PW", "Pengawasan (PW)"),
    ("UM", "Umum (UM)"),
    ("SA", "Sumber Daya Air (SA)"),
    ("SM", "Pengembangan SDM (SM)"),
]

def _saring_bulan(qs, bulan):
    return qs.filter(tanggal__month=bulan) if bulan else qs


def rekap_klasifikasi(qs, units, tahun, bulan=None):
    kode = [k for k, _ in KLASIFIKASI_REKAP]
    hasil = (_saring_bulan(qs.filter(tanggal__year=tahun, kategori__kode__in=kode), bulan)
               .order_by()
               .values("unit_kerja_id", "kategori__kode")
               .annotate(total=Sum("jumlah")))
    isi = {(r["unit_kerja_id"], r["kategori__kode"]): r["total"] for r in hasil}
    baris = [{"unit": u, "kategori": [isi.get((u.pk, k), 0) for k in kode]} for u in units]
    jumlah = [sum(b["kategori"][i] for b in baris) for i in range(len(kode))]
    return {"kategori": [label for _, label in KLASIFIKASI_REKAP], "baris": baris,
            "jumlah": jumlah, "total_semua": sum(jumlah)}


def rekap_jenis_sifat(qs, units, tahun, bulan=None):
    def hitung(field, pilihan):
        hasil = (_saring_bulan(qs.filter(tanggal__year=tahun), bulan)
                   .order_by()
                   .values("unit_kerja_id", field)
                   .annotate(total=Sum("jumlah")))
        isi = {(r["unit_kerja_id"], r[field]): r["total"] for r in hasil}
        kode = [k for k, _ in pilihan]
        baris = [{"unit": u, "nilai": [isi.get((u.pk, k), 0) for k in kode]} for u in units]
        jumlah = [sum(b["nilai"][i] for b in baris) for i in range(len(kode))]
        return {"kolom": [label for _, label in pilihan], "baris": baris,
                "jumlah": jumlah, "total_semua": sum(jumlah)}

    return {
        "jenis": hitung("keterangan", [("asli", "Asli"), ("copy", "Copy")]),
        "sifat": hitung("keamanan", [("terbuka", "Biasa"), ("terbatas", "Terbatas"), ("rahasia", "Rahasia")]),
    }

@login_required
def dashboard(request):
    qs, bagian, _ = _bagian(request, Arsip.objects.untuk(request.user))
    atasan = request.user.is_atasan
    dasar = Arsip.objects.all() if atasan else qs
    awal, akhir = _periode(request, qs)
    q = request.GET.get("q", "").strip()
    per = (_cari(_filter_periode(qs, awal, akhir), q)
           .select_related("kategori", "kode_tujuan", "unit_kerja")
           .order_by(*URUTAN))
    today = date.today()
    stats = [
        ("Total arsip", dasar.count()),
        (f"Arsip bulan ini ({date_format(today, 'F Y')})",
        dasar.filter(tanggal__year=today.year, tanggal__month=today.month).count()),
    ]
    admin = request.user.is_admin_role
    semua = Arsip.objects.all()   # tabel rekap menampilkan total seluruh bagian untuk semua akun
    tahun, pilihan_tahun = _tahun(request, semua)
    unit_rekap = UnitKerja.objects.order_by("id")
    bulan = request.GET.get("bulan", "")
    bulan = int(bulan) if bulan.isdigit() and 1 <= int(bulan) <= 12 else None
    return render(request, "dashboard.html", {
        "stats": stats,
        "atasan": atasan,
        "rekap": rekap_bagian(semua, unit_rekap, tahun),
        "rekap_klas": rekap_klasifikasi(semua, unit_rekap, tahun, bulan),
        "rekap_js": rekap_jenis_sifat(semua, unit_rekap, tahun, bulan),
        "bulan_rekap": bulan,
        "tahun": tahun,
        "pilihan_tahun": pilihan_tahun,
        "nama_bulan": BULAN,
        "jumlah": per.count(),
        "q": q,
        "grup": susun_tabel(per),
        "dari": f"{awal:%Y-%m}",
        "sampai": f"{akhir:%Y-%m}",
        "mode": request.GET.get("mode", "per_bulan"),
        "units": UnitKerja.objects.order_by("id") if admin else [],
        "bagian": bagian,
        "susunan": request.GET.get("susunan", "gabung"),
        "tampil_bagian": admin and bagian == "semua",
    })

@login_required
def rekap_export(request):
    """Export 4 tabel rekap (bagian, klasifikasi, jenis, sifat) dalam 1 sheet. ?tipe=pdf untuk PDF, default Excel."""
    u = request.user
    if not (u.is_atasan or u.is_admin_role):
        raise PermissionDenied
    semua = Arsip.objects.all()
    tahun, _ = _tahun(request, semua)
    bulan = request.GET.get("bulan", "")
    bulan = int(bulan) if bulan.isdigit() and 1 <= int(bulan) <= 12 else None
    units = UnitKerja.objects.order_by("id")
    bag = rekap_bagian(semua, units, tahun)
    klas = rekap_klasifikasi(semua, units, tahun, bulan)
    js = rekap_jenis_sifat(semua, units, tahun, bulan)
    periode = (BULAN[bulan - 1].title() if bulan else "Januari - Desember")

    def blok(judul, kepala, baris, jumlah):
        return {"judul": judul, "kepala": list(kepala),
                "baris": [(unit.singkatan, nilai) for unit, nilai in baris], "jumlah": jumlah}

    b_bagian = blok(f"Total berkas per bagian, tahun {tahun}", [b.title() for b in BULAN],
                    [(b["unit"], b["bulan"]) for b in bag["baris"]], bag["jumlah"])
    b_klas = blok(f"Total berkas per klasifikasi ({periode})", klas["kategori"],
                  [(b["unit"], b["kategori"]) for b in klas["baris"]], klas["jumlah"])
    b_jenis = blok(f"Total berkas per jenis ({periode})", js["jenis"]["kolom"],
                   [(b["unit"], b["nilai"]) for b in js["jenis"]["baris"]], js["jenis"]["jumlah"])
    b_sifat = blok(f"Total berkas per sifat ({periode})", js["sifat"]["kolom"],
                   [(b["unit"], b["nilai"]) for b in js["sifat"]["baris"]], js["sifat"]["jumlah"])

    if request.GET.get("tipe") == "pdf":
        data = buat_pdf_rekap(tahun, periode, b_bagian, b_klas, b_jenis, b_sifat)
        jenis_file, ekstensi = "application/pdf", "pdf"
    else:
        data = buat_excel_rekap_gabung(tahun, periode, b_bagian, b_klas, b_jenis, b_sifat)
        jenis_file, ekstensi = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    resp = HttpResponse(data, content_type=jenis_file)
    resp["Content-Disposition"] = f'attachment; filename="Rekap Berkas {tahun}.{ekstensi}"'
    return resp

@login_required
def arsip_export(request):
    user = request.user
    qs, bagian, unit_pilih = _bagian(request, Arsip.objects.untuk(user))
    if not user.is_admin_role:
        unit_pilih = user.unit_kerja
        if not unit_pilih:
            messages.error(request, "Akun ini belum punya unit kerja, jadi belum bisa export.")
            return redirect("dashboard")
        qs = qs.filter(unit_kerja=unit_pilih)

    awal, akhir = _periode(request, qs)
    mode = request.GET.get("mode", "per_bulan")
    terpisah = unit_pilih is None and request.GET.get("susunan") == "terpisah"

    lembar = []
    if terpisah:
        for u in UnitKerja.objects.order_by("id"):
            lembar += buat_lembar(qs.filter(unit_kerja=u), u, awal, akhir, mode, awalan=f"{u.singkatan} - ")
    else:
        lembar = buat_lembar(qs, unit_pilih, awal, akhir, mode)

    if not lembar:
        messages.error(request, "Tidak ada arsip pada periode yang dipilih.")
        return redirect("arsip_list")

    label = unit_pilih.singkatan if unit_pilih else "Semua Bagian"
    nama_file = f"Daftar Isi Berkas {label} {awal:%Y-%m}"
    if akhir != awal:
        nama_file += f" sd {akhir:%Y-%m}"
    return _kirim_file(request, lembar, nama_file, buat_excel, buat_pdf)

@login_required
@bukan_atasan
def arsip_list(request):
    qs = (Arsip.objects.untuk(request.user)
          .select_related("kategori", "kode_tujuan")
          .order_by(*URUTAN))
    q = request.GET.get("q", "").strip()
    bulan = request.GET.get("bulan", "")
    kat = request.GET.get("kat", "")
    if bulan:
        try:
            y, m = map(int, bulan.split("-"))
            qs = qs.filter(tanggal__year=y, tanggal__month=m)
        except ValueError:
            pass
    if kat:
        qs = qs.filter(kategori__kode=kat)
    if q:
        qs = qs.filter(uraian__icontains=q)
    ctx = {
        "grup": susun_tabel(qs), "jumlah": qs.count(), "q": q, "bulan": bulan, "kat": kat,
        "kategori_list": Kategori.objects.all(),
        "tahun_ini": date.today().year,
        "units": UnitKerja.objects.order_by("id") if request.user.is_admin_role else [],
    }
    if request.headers.get("HX-Request"):
        return render(request, "arsip/_tabel.html", ctx)
    return render(request, "arsip/list.html", ctx)

def _inaktif_saring(request):
    """Arsip inaktif sesuai wewenang dan filter (bagian untuk admin, tahun, kata kunci)."""
    dasar = ArsipInaktif.objects.untuk(request.user)
    qs, bagian, _ = _bagian(request, dasar)
    q = request.GET.get("q", "").strip()
    tahun = request.GET.get("tahun", "")
    if tahun.isdigit():
        qs = qs.filter(tahun=int(tahun))
    if q:
        qs = qs.filter(Q(uraian__icontains=q) | Q(kode__icontains=q) | Q(indeks__icontains=q))
    qs = qs.select_related("unit_kerja").order_by("unit_kerja_id", "kode", "no_berkas", "no_urut", "id")
    return dasar, qs, q, tahun, bagian

@login_required
@bukan_atasan
def arsip_inaktif_list(request):
    dasar, qs, q, tahun, bagian = _inaktif_saring(request)
    admin = request.user.is_admin_role
    ctx = {
        "daftar": qs, "jumlah": qs.count(), "q": q, "tahun": tahun, "bagian": bagian,
        "tahun_list": dasar.order_by("-tahun").values_list("tahun", flat=True).distinct(),
        "tampil_bagian": admin and bagian == "semua",
        "units": UnitKerja.objects.order_by("id") if admin else [],
    }
    if request.headers.get("HX-Request"):
        return render(request, "arsip/_tabel_inaktif.html", ctx)
    return render(request, "arsip/inaktif_list.html", ctx)

@login_required
@bukan_atasan
def arsip_inaktif_form(request, pk=None):
    if not request.headers.get("HX-Request"):
        return redirect("arsip_inaktif_list")
    user = request.user
    obj = get_object_or_404(ArsipInaktif.objects.untuk(user), pk=pk) if pk else None
    unit = obj.unit_kerja if obj else _unit_tujuan(request, user)
    if not unit:
        if user.is_admin_role:
            return _modal_pilih_unit(request, "Tambah Arsip Inaktif")
        messages.error(request, "Akun ini belum punya unit kerja. Atur dulu lewat halaman admin.")
        return HttpResponse(headers={"HX-Redirect": reverse("arsip_inaktif_list")})

    form = ArsipInaktifForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        if not obj:
            a.unit_kerja = unit
        a.save()
        messages.success(request, "Arsip inaktif berhasil disimpan.")
        return HttpResponse(headers={"HX-Refresh": "true"})
    judul = "Ubah Arsip Inaktif" if obj else "Tambah Arsip Inaktif"
    return render(request, "arsip/_modal_form_inaktif.html", {
        "form": form, "judul": judul, "pilih_unit": not user.unit_kerja and not obj, "unit": unit,
    })

@login_required
@bukan_atasan
def arsip_inaktif_form(request, pk=None):
    if not request.headers.get("HX-Request"):
        return redirect("arsip_inaktif_list")
    user = request.user
    obj = get_object_or_404(ArsipInaktif.objects.untuk(user), pk=pk) if pk else None
    if not obj and not user.unit_kerja:
        messages.error(request, "Akun ini belum punya unit kerja. Atur dulu lewat halaman admin.")
        return HttpResponse(headers={"HX-Redirect": reverse("arsip_inaktif_list")})

    form = ArsipInaktifForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        if not obj:
            a.unit_kerja = user.unit_kerja
        a.save()
        messages.success(request, "Arsip inaktif berhasil disimpan.")
        return HttpResponse(headers={"HX-Refresh": "true"})
    judul = "Ubah Arsip Inaktif" if obj else "Tambah Arsip Inaktif"
    return render(request, "arsip/_modal_form_inaktif.html", {"form": form, "judul": judul})

@login_required
@bukan_atasan
@require_POST
def arsip_inaktif_hapus(request, pk):
    get_object_or_404(ArsipInaktif.objects.untuk(request.user), pk=pk).delete()
    messages.success(request, "Arsip inaktif berhasil dihapus.")
    return redirect("arsip_inaktif_list")

@login_required
@bukan_atasan
def arsip_inaktif_import(request):
    if not request.headers.get("HX-Request"):
        return redirect("arsip_inaktif_list")
    user = request.user
    unit = _unit_tujuan(request, user)
    if not unit:
        if user.is_admin_role:
            return _modal_pilih_unit(request, "Import Arsip Inaktif dari Excel")
        messages.error(request, "Akun ini belum punya unit kerja, jadi belum bisa import.")
        return HttpResponse(headers={"HX-Redirect": reverse("arsip_inaktif_list")})

    if request.method != "POST":
        return render(request, "arsip/_modal_import_inaktif.html", {
            "max_mb": settings.MAX_UPLOAD_MB, "unit": unit, "pilih_unit": not user.unit_kerja})

    form = ImportExcelForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "arsip/_hasil_import_inaktif.html", {"error": form.errors["file"][0]})
    simpan = request.POST.get("simpan") == "1"
    try:
        hasil = proses_import_inaktif(form.cleaned_data["file"], user, simpan=simpan, unit=unit)
    except ImportGagal as e:
        return render(request, "arsip/_hasil_import_inaktif.html", {"error": str(e)})
    return render(request, "arsip/_hasil_import_inaktif.html", {"hasil": hasil, "simpan": simpan})

@login_required
@bukan_atasan
def arsip_inaktif_export(request):
    """Export arsip inaktif. mode per_tahun = satu tab per tahun, gabung = satu tab per bagian."""
    _, qs, _, tahun, _ = _inaktif_saring(request)
    per_unit = {}
    for a in qs:
        per_unit.setdefault(a.unit_kerja, []).append(a)
    if not per_unit:
        messages.error(request, "Tidak ada arsip inaktif untuk diexport.")
        return redirect("arsip_inaktif_list")

    lembar = []
    for unit, daftar in per_unit.items():
        if request.GET.get("mode", "per_tahun") == "per_tahun":
            per_tahun = {}
            for a in daftar:
                per_tahun.setdefault(a.tahun, []).append(a)
            for th in sorted(per_tahun):
                lembar.append((f"{unit.singkatan} {th}", unit, per_tahun[th]))
        else:
            lembar.append((unit.singkatan, unit, daftar))

    label = next(iter(per_unit)).singkatan if len(per_unit) == 1 else "Semua Bagian"
    if tahun.isdigit():
        label += f" {tahun}"
    return _kirim_file(request, lembar, f"Daftar Arsip Inaktif {label}", buat_excel_inaktif, buat_pdf_inaktif)

@login_required
def arsip_form(request, pk=None):
    if not request.headers.get("HX-Request"):
        return redirect("dashboard")

    user = request.user
    obj = get_object_or_404(Arsip.objects.untuk(user), pk=pk) if pk else None
    unit = obj.unit_kerja if obj else _unit_tujuan(request, user)
    if not unit:
        if user.is_admin_role:
            return _modal_pilih_unit(request, "Tambah Arsip")
        messages.error(request, "Akun ini belum punya unit kerja. Atur dulu lewat halaman admin.")
        return HttpResponse(headers={"HX-Redirect": reverse("dashboard")})

    berkas_lama = obj.berkas.name if obj else ""
    form = ArsipForm(request.POST or None, request.FILES or None, instance=obj, unit=unit)

    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        if not obj:
            a.unit_kerja = unit
            a.created_by = user
        a.save()
        if berkas_lama and berkas_lama != a.berkas.name:
            a.berkas.storage.delete(berkas_lama)
        messages.success(request, f"Arsip berhasil disimpan di bulan {date_format(a.tanggal, 'F Y')}.")
        return HttpResponse(headers={"HX-Refresh": "true"})

    ctx = {
        "form": form,
        "judul": "Ubah Arsip" if obj else "Tambah Arsip",
        "max_mb": settings.MAX_UPLOAD_MB,
        "tujuan_map": {str(t.pk): {"kode": t.kode, "jabatan": t.nama_jabatan}
                       for t in KodeTujuan.objects.all()},
        "kategori_map": {str(k.pk): k.kode for k in Kategori.objects.all()},
        "bebas": form.bebas,
        "pilih_unit": not user.unit_kerja and not obj,
        "unit": unit,
    }
    return render(request, "arsip/_modal_form.html", ctx)

@login_required
@bukan_atasan
@require_POST
def arsip_hapus(request, pk):
    obj = get_object_or_404(Arsip.objects.untuk(request.user), pk=pk)
    obj.delete()
    messages.success(request, "Arsip berhasil dihapus.")
    return redirect("arsip_list")

@login_required
def arsip_berkas(request, pk):
    a = get_object_or_404(Arsip.objects.untuk(request.user), pk=pk)
    if not a.berkas:
        raise Http404("Arsip ini belum punya berkas.")

    if settings.USE_R2:
        if not a.berkas.storage.exists(a.berkas.name):
            Arsip.objects.filter(pk=a.pk).update(berkas="")
            messages.error(request, "Berkas tidak ditemukan di penyimpanan. Silakan unggah ulang.")
            return redirect("arsip_list")
        return redirect(a.berkas.url)

    if settings.USE_GDRIVE and not a.berkas.storage.ada(a.berkas.name):
        Arsip.objects.filter(pk=a.pk).update(berkas="")
        messages.error(request, "Berkas sudah dihapus dari Drive. Silakan unggah ulang.")
        return redirect("arsip_list")

    if settings.USE_GDRIVE and settings.GDRIVE_BUKA_DI_DRIVE:
        return redirect(f"https://drive.google.com/file/d/{a.berkas.name}/view")

    try:
        f = a.berkas.open("rb")
    except HttpError as e:
        if e.resp.status == 404:
            Arsip.objects.filter(pk=a.pk).update(berkas="")
            messages.error(request, "Berkas tidak ditemukan di Drive (kemungkinan sudah dihapus). Silakan unggah ulang.")
            return redirect("arsip_list")
        raise

    resp = FileResponse(f, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="arsip-{a.pk}.pdf"'
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Cache-Control"] = "private, no-store"
    return resp

@login_required
def arsip_import(request):
    if not request.headers.get("HX-Request"):
        return redirect("dashboard")

    user = request.user
    unit = _unit_tujuan(request, user)
    if not unit:
        if user.is_admin_role:
            return _modal_pilih_unit(request, "Import dari Excel")
        messages.error(request, "Akun ini belum punya unit kerja, jadi belum bisa import.")
        return HttpResponse(headers={"HX-Redirect": reverse("dashboard")})

    if request.method != "POST":
        return render(request, "arsip/_modal_import.html", {
            "max_mb": settings.MAX_UPLOAD_MB, "unit": unit, "pilih_unit": not user.unit_kerja})

    form = ImportExcelForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "arsip/_hasil_import.html", {"error": form.errors["file"][0]})

    simpan = request.POST.get("simpan") == "1"
    try:
        hasil = proses_import(form.cleaned_data["file"], user, simpan=simpan, unit=unit)
    except ImportGagal as e:
        return render(request, "arsip/_hasil_import.html", {"error": str(e)})

    return render(request, "arsip/_hasil_import.html", {"hasil": hasil, "simpan": simpan})