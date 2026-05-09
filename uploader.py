"""
uploader.py – Handles YouTube OAuth and video uploads.
Credentials are cached in token.pickle so the browser prompt only
appears on the very first run.
"""

from __future__ import annotations

import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import YOUTUBE_CATEGORY_ID, YOUTUBE_PRIVACY, YOUTUBE_SCOPES


TOKEN_FILE = "token.pickle"
CLIENT_SECRET_FILE = "client_secret.json"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def get_authenticated_service():
    """Return an authenticated YouTube Data API v3 service object."""
    creds = _load_cached_credentials()

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  [uploader] Refreshing access token…")
            creds.refresh(Request())
        else:
            print("  [uploader] Opening browser for OAuth…")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, YOUTUBE_SCOPES)
            creds = flow.run_local_server(port=0)
        _save_credentials(creds)

    return build("youtube", "v3", credentials=creds)


def _load_cached_credentials():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as fh:
            return pickle.load(fh)
    return None


def _save_credentials(creds) -> None:
    with open(TOKEN_FILE, "wb") as fh:
        pickle.dump(creds, fh)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_video(
    service,
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = YOUTUBE_CATEGORY_ID,
    privacy: str = YOUTUBE_PRIVACY,
) -> str:
    """
    Upload *file_path* to YouTube.
    Returns the video ID.
    """
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
        },
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    print(f"  [uploader] Uploading '{title}'…")
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"  [uploader]   {pct}%", end="\r")

    video_id = response["id"]
    print(f"  [uploader] Upload complete → https://www.youtube.com/watch?v={video_id}")
    return video_id
