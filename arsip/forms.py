from django import forms
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from .models import Arsip

INPUT = ("w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm "
         "text-slate-800 placeholder-slate-400 focus:border-blue-500 "
         "focus:outline-none focus:ring-2 focus:ring-blue-100")

FILE_INPUT = ("block w-full text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 "
              "file:bg-blue-50 file:px-4 file:py-2 file:text-sm file:font-medium "
              "file:text-blue-700 hover:file:bg-blue-100")

class ArsipForm(forms.ModelForm):
    class Meta:
        model = Arsip
        fields = ["kode_tujuan", "kategori", "sub_kode", "nomor_surat",
                  "perihal", "tanggal", "jumlah", "keterangan", "keamanan", "berkas"]
        labels = {
            "kode_tujuan": "Pejabat Penandatanganan",
            "kategori": "Kategori Utama",
            "sub_kode": "Sub-kode",
            "nomor_surat": "Nomor Surat (kosongkan jika belum keluar)",
            "perihal": "Perihal",
            "tanggal": "Tanggal",
            "jumlah": "Jumlah",
            "keterangan": "Keterangan",
            "keamanan": "Klasifikasi Keamanan",
            "berkas": "Berkas (PDF)",
        }
        widgets = {
            "sub_kode": forms.TextInput(attrs={"inputmode": "numeric", "maxlength": 6, "placeholder": "0101"}),
            "nomor_surat": forms.TextInput(attrs={"placeholder": "29"}),
            "perihal": forms.Textarea(attrs={"rows": 3, "placeholder": "Tanggapan atas penyusunan ..."}),
            "tanggal": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "jumlah": forms.TextInput(attrs={"inputmode": "numeric", "class": "pr-12"}),
            "keterangan": forms.RadioSelect(attrs={"class": "accent-blue-600"}),
            "berkas": forms.FileInput(attrs={"accept": "application/pdf", "class": FILE_INPUT}),
        }

    def __init__(self, *args, unit=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.bebas = bool(unit and unit.uraian_bebas)
        for name, f in self.fields.items():
            if name not in ("keterangan", "berkas"):
                extra = f.widget.attrs.get("class", "")
                f.widget.attrs["class"] = f"{INPUT} {extra}".strip()
        self.fields["kategori"].empty_label = "Pilih kategori"
        if self.bebas:
            # Unit dengan uraian bebas (contoh: Satker): tidak ada pejabat dan nomor surat
            del self.fields["kode_tujuan"]
            del self.fields["nomor_surat"]
            self.fields["perihal"].label = "Uraian Informasi"
            self.fields["perihal"].widget.attrs["placeholder"] = "SPM NO. 01 Pembayaran Belanja Barang ..."
            self.fields["sub_kode"].widget.attrs["placeholder"] = "03"
        else:
            self.fields["kode_tujuan"].required = True
            self.fields["kode_tujuan"].empty_label = "Pilih pejabat penandatanganan"
            self.fields["nomor_surat"].required = False

    def clean_berkas(self):
        f = self.cleaned_data.get("berkas")
        if isinstance(f, UploadedFile):   
            if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
                raise forms.ValidationError(f"Ukuran file maksimal {settings.MAX_UPLOAD_MB} MB.")
            kepala = f.read(5)
            f.seek(0)
            if kepala != b"%PDF-":
                raise forms.ValidationError("File harus berupa PDF yang valid.")
        return f

    def clean_nomor_surat(self):
        return self.cleaned_data["nomor_surat"].strip().upper()    

class ImportExcelForm(forms.Form):
    file = forms.FileField(
        label="File Excel (.xlsx)",
        widget=forms.FileInput(attrs={"accept": ".xlsx", "class": FILE_INPUT}),
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("File harus berformat .xlsx.")
        if f.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
            raise forms.ValidationError(f"Ukuran file maksimal {settings.MAX_UPLOAD_MB} MB.")
        kepala = f.read(4)
        f.seek(0)
        if kepala != b"PK\x03\x04":
            raise forms.ValidationError("File bukan Excel (.xlsx) yang valid.")
        return f