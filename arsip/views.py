from accounts.models import UnitKerja
from googleapiclient.errors import HttpError
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils.formats import date_format
from datetime import date
from itertools import accumulate, groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Q, Sum
from django.db.models.functions import ExtractMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from master.models import Kategori, KodeTujuan, Pengesah
from .exports import BULAN, buat_excel, buat_excel_rekap, label_periode
from .forms import ArsipForm, ImportExcelForm
from .importer import ImportGagal, proses_import
from .models import Arsip

URUTAN = ("kategori__urutan", "kategori__kode", "sub_kode", "tanggal", "id")


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
    """Ambil rentang bulan dari ?dari=&sampai=. Default: bulan terbaru yang punya data."""
    awal = _bulan(request.GET.get("dari"))
    akhir = _bulan(request.GET.get("sampai"))
    if not awal:
        terakhir = qs.aggregate(m=Max("tanggal"))["m"] or date.today()
        awal = terakhir.replace(day=1)
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
    awal, akhir = _periode(request, qs)
    q = request.GET.get("q", "").strip()
    per = (_cari(_filter_periode(qs, awal, akhir), q)
           .select_related("kategori", "kode_tujuan", "unit_kerja")
           .order_by(*URUTAN))
    today = date.today()
    stats = [
        ("Total arsip", qs.count()),
        (f"Arsip bulan ini ({date_format(today, 'F Y')})",
         qs.filter(tanggal__year=today.year, tanggal__month=today.month).count()),
    ]
    admin = request.user.is_admin_role
    semua = Arsip.objects.all()   # tabel rekap menampilkan total seluruh bagian untuk semua akun
    tahun, pilihan_tahun = _tahun(request, semua)
    unit_rekap = UnitKerja.objects.order_by("id")
    bulan = request.GET.get("bulan", "")
    bulan = int(bulan) if bulan.isdigit() and 1 <= int(bulan) <= 12 else None
    return render(request, "dashboard.html", {
        "stats": stats,
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
        params = request.GET.copy()
        params["dari"], params["sampai"] = f"{awal:%Y-%m}", f"{akhir:%Y-%m}"
        return redirect(f"{reverse('dashboard')}?{params.urlencode()}")

    label = unit_pilih.singkatan if unit_pilih else "Semua Bagian"
    data = buat_excel(lembar)
    nama_file = f"Daftar Isi Berkas {label} {awal:%Y-%m}"
    if akhir != awal:
        nama_file += f" sd {akhir:%Y-%m}"
    resp = HttpResponse(
        data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = f'attachment; filename="{nama_file}.xlsx"'
    return resp


@login_required
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
    }
    if request.headers.get("HX-Request"):
        return render(request, "arsip/_tabel.html", ctx)
    return render(request, "arsip/list.html", ctx)

@login_required
def arsip_form(request, pk=None):
    if not request.headers.get("HX-Request"):
        return redirect("dashboard")

    user = request.user
    if not user.unit_kerja:
        messages.error(request, "Akun ini belum punya unit kerja. Atur dulu lewat halaman admin.")
        return HttpResponse(headers={"HX-Redirect": reverse("dashboard")})

    obj = get_object_or_404(Arsip.objects.untuk(user), pk=pk) if pk else None
    berkas_lama = obj.berkas.name if obj else ""   
    unit = obj.unit_kerja if obj else user.unit_kerja
    form = ArsipForm(request.POST or None, request.FILES or None, instance=obj, unit=unit)

    if request.method == "POST" and form.is_valid():
        a = form.save(commit=False)
        if not obj:
            a.unit_kerja = user.unit_kerja
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
    }
    return render(request, "arsip/_modal_form.html", ctx)

@login_required
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
    if not user.unit_kerja:
        messages.error(request, "Akun ini belum punya unit kerja, jadi belum bisa import.")
        return HttpResponse(headers={"HX-Redirect": reverse("dashboard")})

    if request.method != "POST":
        return render(request, "arsip/_modal_import.html", {"max_mb": settings.MAX_UPLOAD_MB})

    form = ImportExcelForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "arsip/_hasil_import.html", {"error": form.errors["file"][0]})

    simpan = request.POST.get("simpan") == "1"
    try:
        hasil = proses_import(form.cleaned_data["file"], user, simpan=simpan)
    except ImportGagal as e:
        return render(request, "arsip/_hasil_import.html", {"error": str(e)})

    return render(request, "arsip/_hasil_import.html", {
        "hasil": hasil, "simpan": simpan,
    })