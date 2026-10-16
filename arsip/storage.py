import io
import os

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


@deconstructible
class GoogleDriveStorage(Storage):
    """Simpan berkas ke satu folder Google Drive.

    Yang disimpan di database adalah ID file Drive-nya, bukan path. Pindah akun Drive
    cukup mengganti isi .env (token + ID folder), kode tidak perlu diubah.
    """

    def __init__(self):
        self._service = None

    @property
    def service(self):
        if self._service is None:
            creds = Credentials(
                token=None,
                refresh_token=settings.GDRIVE_REFRESH_TOKEN,
                client_id=settings.GDRIVE_CLIENT_ID,
                client_secret=settings.GDRIVE_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token",
                scopes=SCOPES,
            )
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _save(self, name, content):
        content.seek(0)
        media = MediaIoBaseUpload(io.BytesIO(content.read()), mimetype="application/pdf")
        nama_asli = os.path.basename(name).split("__", 1)[-1]   # buang awalan acak
        meta = {"name": nama_asli, "parents": [settings.GDRIVE_FOLDER_ID]}
        f = self.service.files().create(
            body=meta, media_body=media, fields="id", supportsAllDrives=True,
        ).execute()
        return f["id"]

    def _open(self, name, mode="rb"):
        req = self.service.files().get_media(fileId=name, supportsAllDrives=True)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, req)
        selesai = False
        while not selesai:
            _, selesai = dl.next_chunk()
        return ContentFile(buf.getvalue(), name=name)

    def delete(self, name):
        """Pindahkan ke Sampah Drive (masih bisa dipulihkan sekitar 30 hari)."""
        if not name:
            return
        try:
            self.service.files().update(
                fileId=name, body={"trashed": True}, supportsAllDrives=True,
            ).execute()
        except HttpError as e:
            if e.resp.status != 404:
                raise

    def exists(self, name):
        return False   # nama yang disimpan adalah ID acak dari Drive, tidak mungkin bentrok

    def size(self, name):
        info = self.service.files().get(fileId=name, fields="size", supportsAllDrives=True).execute()
        return int(info.get("size", 0))

    def url(self, name):
        return ""   # berkas hanya dibuka lewat view arsip_berkas, tidak ada link publik