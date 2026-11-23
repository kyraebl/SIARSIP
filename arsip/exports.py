import math
from io import BytesIO
from xml.sax.saxutils import escape

from openpyxl.utils import get_column_letter
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.properties import PageSetupProperties
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI",
         "AGUSTUS", "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]
SISI = Side(style="thin")
KOTAK = Border(left=SISI, right=SISI, top=SISI, bottom=SISI)
HEADER = ["NO. BERKAS", "NO. ITEM ARSIP", "KODE KLASIFIKASI", "URAIAN INFORMASI",
          "TANGGAL", "JUMLAH", "KETERANGAN", "KET. KLASIFIKASI KEAMANAN DAN AKSES ARSIP"]
LEBAR = [12, 13, 17, 70, 18, 11, 14, 26]
TENGAH = Alignment(horizontal="center", vertical="center", wrap_text=True)
ATAS = Alignment(horizontal="center", vertical="top", wrap_text=True)
KIRI = Alignment(horizontal="left", vertical="center", wrap_text=True)


def _isi_sheet(ws, item):
    """Isi satu tab. item: dict dengan kunci unit_label, bulan, tahun, grup, pengesah, gabungan."""
    gabungan = item["gabungan"]   
    header = HEADER + (["BAGIAN"] if gabungan else [])
    lebar = LEBAR + ([12] if gabungan else [])
    n = len(header)
    for i, w in enumerate(lebar, start=1):
        ws.column_dimensions[chr(64 + i)].width = w

    ws.merge_cells(f"A1:{chr(64 + n)}1")
    ws["A1"] = "DAFTAR ISI BERKAS"
    ws["A1"].font = Font(bold=True, size=12)
    ws["A1"].alignment = Alignment(horizontal="center")

    info = [("UNIT KERJA", item["unit_label"]),
            ("TAHUN", item["tahun"]),
            ("BULAN", item["bulan"])]
    for baris, (label, isi) in enumerate(info, start=2):
        ws.cell(baris, 1, label)
        ws.cell(baris, 3, f": {isi}")

    for kol, teks in enumerate(header, start=1):
        c = ws.cell(5, kol, teks)
        c.font = Font(bold=True)
        c.alignment = TENGAH
        c.border = KOTAK
    ws.row_dimensions[5].height = 48

    gabung = []
    r = 6
    for g in item["grup"]:
        for k in range(1, n + 1):
            ws.cell(r, k).border = KOTAK
        ws.cell(r, 1, g["kategori"].nama or g["kategori"].kode)
        gabung.append((r, r, 1, n))
        r += 1
        for b in g["berkas"]:
            mulai = r
            for no_item, a in b["baris"]:
                for k in range(1, n + 1):
                    ws.cell(r, k).border = KOTAK
                ws.cell(r, 2, no_item).alignment = TENGAH
                ws.cell(r, 4, a.uraian).alignment = KIRI
                t = ws.cell(r, 5, a.tanggal)
                t.number_format = "d mmmm yyyy"
                t.alignment = TENGAH
                ws.cell(r, 6, a.jumlah_tampil).alignment = TENGAH
                ws.cell(r, 7, a.get_keterangan_display()).alignment = TENGAH
                ws.cell(r, 8, a.get_keamanan_display()).alignment = TENGAH
                if gabungan:
                    ws.cell(r, 9, a.unit_kerja.singkatan).alignment = TENGAH
                ws.row_dimensions[r].height = max(30, 15 * math.ceil(len(a.uraian) / 62))
                r += 1
            ws.cell(mulai, 1, b["no"]).alignment = ATAS
            ws.cell(mulai, 3, b["kode"]).alignment = ATAS
            if r - mulai > 1:
                gabung.append((mulai, r - 1, 1, 1))
                gabung.append((mulai, r - 1, 3, 3))

    for r1, r2, c1, c2 in gabung:
        ws.merge_cells(start_row=r1, end_row=r2, start_column=c1, end_column=c2)

    if not gabungan:
        pengesah = item["pengesah"]
        r += 1
        jabatan = f"{pengesah.jabatan}," if pengesah and pengesah.jabatan else "Kepala Bagian,"
        blok = [
            (r, "Mengetahui,", None),
            (r + 1, jabatan, None),
            (r + 5, pengesah.nama if pengesah and pengesah.nama else "Nama", "single"),
            (r + 6, f"NIP. {pengesah.nip}" if pengesah and pengesah.nip else "NIP.", None),
        ]
        for baris, teks, garis in blok:
            ws.merge_cells(start_row=baris, end_row=baris, start_column=7, end_column=8)
            c = ws.cell(baris, 7, teks)
            c.alignment = Alignment(horizontal="center", vertical="top", wrap_text=True)
            if garis:
                c.font = Font(underline=garis)
        if len(jabatan) > 40:   
            ws.row_dimensions[r + 1].height = 30

    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)


def label_periode(awal, akhir):
    """Teks untuk isian BULAN dan TAHUN di bagian atas sheet."""
    if awal == akhir:
        bulan = BULAN[awal.month - 1]
    else:
        bulan = f"{BULAN[awal.month - 1]} - {BULAN[akhir.month - 1]}"
    tahun = str(awal.year) if awal.year == akhir.year else f"{awal.year} - {akhir.year}"
    return bulan, tahun

def buat_excel(lembar):
    """lembar: daftar dict (nama, unit_label, bulan, tahun, grup, pengesah, gabungan)."""
    wb = Workbook()
    wb.remove(wb.active)
    for item in lembar:
        ws = wb.create_sheet(item["nama"][:31])
        _isi_sheet(ws, item)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

def buat_excel_rekap(judul, tahun, kolom, baris, jumlah, total_semua, grup=None, pakai_no=False):
    """Satu tab rekap. baris: list (nama bagian, [nilai per kolom]). grup: judul kelompok kolom (opsional)."""
    wb = Workbook()
    ws = wb.active
    ws.title = judul[:31]

    awal = ["NO", "BAGIAN"] if pakai_no else ["BAGIAN"]
    na = len(awal)
    n = na + len(kolom)
    huruf = get_column_letter

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n)
    ws["A1"] = judul.upper()
    ws["A1"].font = Font(bold=True, size=12)
    ws["A1"].alignment = Alignment(horizontal="center")
    ws["A2"] = "TAHUN"
    ws["C2"] = f": {tahun}"

    r0 = 4
    if grup:
        for k, teks in enumerate(awal, start=1):
            ws.merge_cells(start_row=r0, start_column=k, end_row=r0 + 1, end_column=k)
            ws.cell(r0, k, teks)
        ws.merge_cells(start_row=r0, start_column=na + 1, end_row=r0, end_column=n)
        ws.cell(r0, na + 1, grup)
        for k, teks in enumerate(kolom, start=na + 1):
            ws.cell(r0 + 1, k, teks)
        r = r0 + 2
    else:
        for k, teks in enumerate(awal + list(kolom), start=1):
            ws.cell(r0, k, teks)
        r = r0 + 1
    for rr in range(r0, r):
        for k in range(1, n + 1):
            c = ws.cell(rr, k)
            c.font = Font(bold=True)
            c.alignment = TENGAH
            c.border = KOTAK
    ws.row_dimensions[r0].height = 32
    if grup:
        ws.row_dimensions[r0 + 1].height = 32

    for no, (nama, nilai) in enumerate(baris, start=1):
        if pakai_no:
            ws.cell(r, 1, no)
        ws.cell(r, na, nama)
        for k, v in enumerate(nilai, start=na + 1):
            ws.cell(r, k, v)
        for k in range(1, n + 1):
            ws.cell(r, k).border = KOTAK
            ws.cell(r, k).alignment = TENGAH
        r += 1

    if na > 1:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=na)
    ws.cell(r, 1, "Jumlah")
    for k, v in enumerate(jumlah, start=na + 1):
        ws.cell(r, k, v)
    r += 1
    if na > 1:
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=na)
    ws.cell(r, 1, "Total")
    ws.merge_cells(start_row=r, start_column=na + 1, end_row=r, end_column=n)
    ws.cell(r, na + 1, total_semua)
    for rr in (r - 1, r):
        for k in range(1, n + 1):
            c = ws.cell(rr, k)
            c.font = Font(bold=True)
            c.alignment = TENGAH
            c.border = KOTAK

    ws.column_dimensions["A"].width = 8 if pakai_no else 14
    for k in range(2, n + 1):
        ws.column_dimensions[huruf(k)].width = 14 if (pakai_no and k == 2) else 16

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

HEADER_INAKTIF = ["NO BERKAS", "NO URUT", "KODE", "INDEK/JUDUL", "URAIAN MASALAH / KEGIATAN", "TAHUN", "JUMLAH"]
LEBAR_INAKTIF = [10, 10, 12, 28, 70, 9, 12, 12, 8, 14, 32]


def buat_excel_inaktif(lembar):
    """lembar: list (nama tab, unit, daftar ArsipInaktif)."""
    wb = Workbook()
    wb.remove(wb.active)
    n = len(LEBAR_INAKTIF)
    for nama, unit, daftar in lembar:
        ws = wb.create_sheet(nama[:31])
        for i, w in enumerate(LEBAR_INAKTIF, start=1):
            ws.column_dimensions[get_column_letter(i)].width = w

        for baris, teks in ((1, "DAFTAR ARSIP INAKTIF"), (2, unit.nama.upper())):
            ws.merge_cells(start_row=baris, end_row=baris, start_column=1, end_column=n)
            ws.cell(baris, 1, teks).font = Font(bold=True, size=12)
            ws.cell(baris, 1).alignment = Alignment(horizontal="center")

        for k, teks in enumerate(HEADER_INAKTIF, start=1):
            ws.merge_cells(start_row=4, end_row=5, start_column=k, end_column=k)
            ws.cell(4, k, teks)
        ws.merge_cells(start_row=4, end_row=4, start_column=8, end_column=n)
        ws.cell(4, 8, "KETERANGAN")
        for k, teks in enumerate(["ASLI/COPY", "BOX", "SKKAAD", "LOKASI SIMPAN"], start=8):
            ws.cell(5, k, teks)
        for r in (4, 5):
            for k in range(1, n + 1):
                c = ws.cell(r, k)
                c.font = Font(bold=True)
                c.alignment = TENGAH
                c.border = KOTAK

        r = 6
        kode_lalu = None
        for a in daftar:
            nilai = [a.no_berkas, a.no_urut, a.kode if a.kode != kode_lalu else "", a.indeks,
                     a.uraian, a.tahun, f"{a.jumlah} berkas", a.get_keterangan_display(),
                     a.box, a.get_keamanan_display(), a.lokasi_simpan]
            kode_lalu = a.kode
            for k, v in enumerate(nilai, start=1):
                c = ws.cell(r, k, v)
                c.border = KOTAK
                c.alignment = KIRI if k in (4, 5, 11) else TENGAH
            ws.row_dimensions[r].height = max(30, 15 * math.ceil(len(a.uraian) / 62))
            r += 1

        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

PDF_MARGIN = 1 * cm
PDF_LEBAR = landscape(A4)[0] - 2 * PDF_MARGIN


def _gaya(ukuran=8, rata=TA_LEFT, tebal=False):
    return ParagraphStyle("pdf", fontName="Helvetica-Bold" if tebal else "Helvetica",
                          fontSize=ukuran, leading=ukuran + 2, alignment=rata)


G_JUDUL = _gaya(12, TA_CENTER, True)
G_KIRI = _gaya()
G_TENGAH = _gaya(rata=TA_CENTER)
G_HEAD = _gaya(7, TA_CENTER, True)


def _p(teks, gaya=G_KIRI):
    return Paragraph(escape(str(teks)).replace("\n", "<br/>"), gaya)


def _skala(lebar):
    total = sum(lebar)
    return [w / total * PDF_LEBAR for w in lebar]


def _lebar_inaktif():
    """Lebar kolom (pt). Kolom uraian mengambil sisa halaman."""
    tetap = [38, 32, 44, 100, None, 36, 42, 48, 30, 88, 110]
    sisa = PDF_LEBAR - sum(w for w in tetap if w)
    return [w or sisa for w in tetap]


def _tanggal_id(d):
    return f"{d.day} {BULAN[d.month - 1].title()} {d.year}"


class _TabelPotong(Table):
    """Tabel yang menutup garis bawah di tiap halaman saat terpotong (reportlab hanya melakukannya di potongan pertama)."""

    def split(self, lebar_tersedia, tinggi_tersedia):
        bagian = super().split(lebar_tersedia, tinggi_tersedia)
        if len(bagian) > 1:
            bagian[0].setStyle(TableStyle([("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.black)]))
        return bagian


def _tabel_pdf(rows, lebar, spans, baris_header, tanpa_garis=(), atas=()):
    """Tabel yang boleh terpotong antar halaman.

    spans: ((kolom1, baris1), (kolom2, baris2)). tanpa_garis: set (kolom, baris) yang tidak
    diberi garis bawah, dipakai supaya sel No. Berkas dan Kode tampak menyatu tanpa SPAN
    baris (SPAN baris tidak bisa dipotong antar halaman).
    """
    nk, nb = len(lebar), len(rows)
    gaya = [("BOX", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    gaya += [("LINEAFTER", (c, 0), (c, -1), 0.5, colors.black) for c in range(nk - 1)]
    for r in range(nb - 1):
        c = 0
        while c < nk:
            if (c, r) in tanpa_garis:
                c += 1
                continue
            awal = c
            while c + 1 < nk and (c + 1, r) not in tanpa_garis:
                c += 1
            gaya.append(("LINEBELOW", (awal, r), (c, r), 0.5, colors.black))
            c += 1
    gaya += [("SPAN", a, b) for a, b in spans]
    gaya += [("VALIGN", a, a, "TOP") for a in atas]
    return _TabelPotong(rows, colWidths=lebar, repeatRows=baris_header, style=TableStyle(gaya))


def _cerita_aktif(item):
    gabungan = item["gabungan"]
    header = HEADER + (["BAGIAN"] if gabungan else [])
    lebar = _skala(LEBAR + ([12] if gabungan else []))
    n = len(header)

    info = Table([["UNIT KERJA", f": {item['unit_label']}"], ["TAHUN", f": {item['tahun']}"],
                  ["BULAN", f": {item['bulan']}"]], colWidths=[3.5 * cm, 15 * cm], hAlign="LEFT")
    info.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                              ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0)]))

    rows = [[_p(h, G_HEAD) for h in header]]
    spans, tanpa, atas = [], set(), []
    for g in item["grup"]:
        r = len(rows)
        rows.append([_p(g["kategori"].nama or g["kategori"].kode)] + [""] * (n - 1))
        spans.append(((0, r), (n - 1, r)))
        for b in g["berkas"]:
            mulai = len(rows)
            for i, (no_item, a) in enumerate(b["baris"]):
                baris = [_p(b["no"], G_TENGAH) if i == 0 else "", _p(no_item, G_TENGAH),
                         _p(b["kode"], G_TENGAH) if i == 0 else "", _p(a.uraian),
                         _p(_tanggal_id(a.tanggal), G_TENGAH), _p(a.jumlah_tampil, G_TENGAH),
                         _p(a.get_keterangan_display(), G_TENGAH), _p(a.get_keamanan_display(), G_TENGAH)]
                if gabungan:
                    baris.append(_p(a.unit_kerja.singkatan, G_TENGAH))
                rows.append(baris)
            akhir = len(rows) - 1
            atas += [(0, mulai), (2, mulai)]
            tanpa |= {(c, r) for c in (0, 2) for r in range(mulai, akhir)}

    cerita = [_p("DAFTAR ISI BERKAS", G_JUDUL), Spacer(1, 6), info, Spacer(1, 8),
              _tabel_pdf(rows, lebar, spans, 1, tanpa, atas)]

    if not gabungan:
        pengesah = item["pengesah"]
        jabatan = f"{pengesah.jabatan}," if pengesah and pengesah.jabatan else "Kepala Bagian,"
        nama = pengesah.nama if pengesah and pengesah.nama else "Nama"
        nip = f"NIP. {pengesah.nip}" if pengesah and pengesah.nip else "NIP."
        ttd = Table([[_p("Mengetahui,", G_TENGAH)], [_p(jabatan, G_TENGAH)], [Spacer(1, 40)],
                     [Paragraph(f"<u>{escape(nama)}</u>", G_TENGAH)], [_p(nip, G_TENGAH)]],
                    colWidths=[lebar[6] + lebar[7]], hAlign="RIGHT")
        ttd.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        cerita += [Spacer(1, 14), KeepTogether(ttd)]
    return cerita


def _cerita_inaktif(unit, daftar):
    lebar = _lebar_inaktif()
    n = len(lebar)
    rows = [[_p(h, G_HEAD) for h in HEADER_INAKTIF] + [_p("KETERANGAN", G_HEAD)] + [""] * 3,
            [""] * 7 + [_p(h, G_HEAD) for h in ["ASLI/COPY", "BOX", "SKKAAD", "LOKASI SIMPAN"]]]
    spans = [((k, 0), (k, 1)) for k in range(7)] + [((7, 0), (n - 1, 0))]
    tanpa = {(k, 0) for k in range(7)}

    kode_lalu = None
    for a in daftar:
        rows.append([_p(a.no_berkas, G_TENGAH), _p(a.no_urut, G_TENGAH),
                     _p(a.kode if a.kode != kode_lalu else "", G_TENGAH), _p(a.indeks),
                     _p(a.uraian), _p(a.tahun, G_TENGAH), _p(f"{a.jumlah} berkas", G_TENGAH),
                     _p(a.get_keterangan_display(), G_TENGAH), _p(a.box, G_TENGAH),
                     _p(a.get_keamanan_display(), G_TENGAH), _p(a.lokasi_simpan)])
        kode_lalu = a.kode
    return [_p("DAFTAR ARSIP INAKTIF", G_JUDUL), Spacer(1, 2), _p(unit.nama.upper(), G_JUDUL),
            Spacer(1, 10), _tabel_pdf(rows, lebar, spans, 2, tanpa)]


def _bangun_pdf(bagian_bagian, judul):
    cerita = []
    for i, bagian in enumerate(bagian_bagian):
        if i:
            cerita.append(PageBreak())
        cerita += bagian
    buf = BytesIO()
    SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=PDF_MARGIN, rightMargin=PDF_MARGIN,
                      topMargin=PDF_MARGIN, bottomMargin=PDF_MARGIN, title=judul).build(cerita)
    return buf.getvalue()


def buat_pdf(lembar):
    """lembar sama dengan buat_excel. Satu bagian halaman per tab."""
    return _bangun_pdf([_cerita_aktif(item) for item in lembar], "Daftar Isi Berkas")


def buat_pdf_inaktif(lembar):
    """lembar sama dengan buat_excel_inaktif: list (nama tab, unit, daftar)."""
    return _bangun_pdf([_cerita_inaktif(unit, daftar) for _, unit, daftar in lembar], "Daftar Arsip Inaktif")

# ---------------------------------------------------------------------------
# Rekap dashboard: 4 tabel (bagian, klasifikasi, jenis, sifat) dalam 1 file
# blok = {"judul": str, "kepala": [str], "baris": [(nama_bagian, [angka])], "jumlah": [angka]}
# ---------------------------------------------------------------------------
_ISI_BIRU = PatternFill("solid", fgColor="DCE8F4")


def _tulis_blok(ws, r, c, blok):
    """Tulis satu tabel rekap mulai di (baris r, kolom c). Mengembalikan baris kosong berikutnya."""
    kolom = 1 + len(blok["kepala"]) + 1  # Bagian + data + Total
    ws.cell(r, c, blok["judul"]).font = Font(bold=True, size=12)
    r += 1
    for k, teks in enumerate(["Bagian", *blok["kepala"], "Total"]):
        sel = ws.cell(r, c + k, teks)
        sel.font = Font(bold=True)
        sel.fill = _ISI_BIRU
    ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 45)
    r += 1
    for nama, nilai in blok["baris"]:
        ws.cell(r, c, nama)
        for k, v in enumerate(nilai, start=1):
            ws.cell(r, c + k, v)
        ws.cell(r, c + kolom - 1, sum(nilai))
        r += 1
    ws.cell(r, c, "Jumlah")
    for k, v in enumerate(blok["jumlah"], start=1):
        ws.cell(r, c + k, v)
    ws.cell(r, c + kolom - 1, sum(blok["jumlah"]))
    # border + rata tengah untuk seluruh tabel (header sampai jumlah)
    for rr in range(r - len(blok["baris"]) - 1, r + 1):
        for k in range(kolom):
            sel = ws.cell(rr, c + k)
            sel.border = KOTAK
            sel.alignment = TENGAH
    for k in range(kolom):
        ws.cell(r, c + k).font = Font(bold=True)
        ws.cell(r, c + k).fill = _ISI_BIRU
    return r + 2


def buat_excel_rekap_gabung(tahun, periode, bagian, klasifikasi, jenis, sifat):
    """Satu file, satu sheet. Urutan: bagian, klasifikasi, lalu jenis & sifat berdampingan."""
    wb = Workbook()
    ws = wb.active
    ws.title = f"Rekap {tahun}"
    ws["A1"] = f"REKAP TOTAL BERKAS {tahun} ({periode})"
    ws["A1"].font = Font(bold=True, size=14)

    r = 3
    r = _tulis_blok(ws, r, 1, bagian)
    r = _tulis_blok(ws, r, 1, klasifikasi)
    # jenis (kolom A..D) dan sifat (mulai kolom F) sejajar di baris yang sama
    _tulis_blok(ws, r, 1, jenis)
    _tulis_blok(ws, r, 1 + (1 + len(jenis["kepala"]) + 1) + 1, sifat)

    ws.column_dimensions["A"].width = 14
    for k in range(2, 16):
        ws.column_dimensions[get_column_letter(k)].width = 16

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _tabel_rekap_pdf(blok, lebar):
    """Tabel reportlab untuk satu blok, lebar = total lebar tabel (poin)."""
    head = [_p(t, G_HEAD) for t in ["Bagian", *blok["kepala"], "Total"]]
    rows = [head]
    for nama, nilai in blok["baris"]:
        rows.append([_p(nama, G_TENGAH), *[_p(str(v), G_TENGAH) for v in nilai], _p(str(sum(nilai)), G_TENGAH)])
    G_TEBAL = _gaya(8, TA_CENTER, True)
    rows.append([_p("Jumlah", G_TEBAL), *[_p(v, G_TEBAL) for v in blok["jumlah"]],
                 _p(sum(blok["jumlah"]), G_TEBAL)])
    n = len(head)
    kolom_pertama = min(2.0 * cm, lebar * 0.2)
    sisa = (lebar - kolom_pertama) / (n - 1)
    t = Table(rows, colWidths=[kolom_pertama] + [sisa] * (n - 1), repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCE8F4")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#DCE8F4")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return t


def buat_pdf_rekap(tahun, periode, bagian, klasifikasi, jenis, sifat):
    """PDF landscape A4: bagian, klasifikasi, lalu jenis & sifat berdampingan."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=PDF_MARGIN, rightMargin=PDF_MARGIN,
                            topMargin=PDF_MARGIN, bottomMargin=PDF_MARGIN,
                            title=f"Rekap Berkas {tahun}")
    G_BLOK = _gaya(10, TA_LEFT, True)
    cerita = [_p(f"REKAP TOTAL BERKAS {tahun} ({periode})", G_JUDUL), Spacer(1, 0.4 * cm)]

    for blok in (bagian, klasifikasi):
        cerita += [_p(blok["judul"], G_BLOK), Spacer(1, 0.15 * cm),
                   _tabel_rekap_pdf(blok, PDF_LEBAR), Spacer(1, 0.5 * cm)]

    setengah = (PDF_LEBAR - 1 * cm) / 2
    kiri = [_p(jenis["judul"], G_BLOK), Spacer(1, 0.15 * cm), _tabel_rekap_pdf(jenis, setengah)]
    kanan = [_p(sifat["judul"], G_BLOK), Spacer(1, 0.15 * cm), _tabel_rekap_pdf(sifat, setengah)]
    sejajar = Table([[kiri, "", kanan]], colWidths=[setengah, 1 * cm, setengah])
    sejajar.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]))
    cerita.append(KeepTogether([sejajar]))

    doc.build(cerita)
    return buf.getvalue()