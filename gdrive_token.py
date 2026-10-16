"""Sekali jalan untuk ambil refresh token Google Drive.

Pakai: python gdrive_token.py client_secret.json
Browser akan terbuka, login dengan akun Drive yang mau dipakai, lalu salin
nilai yang dicetak ke file .env.
"""
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
print("\nTempel ke .env:\n")
print(f"GDRIVE_CLIENT_ID={creds.client_id}")
print(f"GDRIVE_CLIENT_SECRET={creds.client_secret}")
print(f"GDRIVE_REFRESH_TOKEN={creds.refresh_token}")