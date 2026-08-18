# -*- coding: utf-8 -*-
"""
YouTube Shorts 업로드 — YouTube Data API v3 (공식, 무료 쿼터 10,000/일)
- 업로드 1건 = 1,600 쿼티 → 일 6건 가능
- 필요: OAuth 클라이언트 (client_secret.json) + 최초 1회 브라우저 동의
- 토큰 저장 후 자동 갱신

셋업 져드:
1. console.cloud.google.com → 새 프로젝트
2. YouTube Data API v3 사용 설정
3. OAuth 동의 화면 (External) → scopes: youtube.upload
4. 사용자 인증 정보 → OAuth 클라이언트 ID (데스크톱) → client_secret.json 다운로드
5. config/youtube_client_secret.json 으로 저장
6. 최초 1회 python src/platforms/youtube_upload.py --auth
"""
import argparse
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CONFIG = BASE / "config"
TOKEN_FILE = CONFIG / "youtube_token.json"
SECRET_FILE = CONFIG / "youtube_client_secret.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_service():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not TOKEN_FILE.exists():
        raise SystemExit(f"토큰 없음 — 최초 1회 인증 필요: python {__file__} --auth")

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload(video_path: str, title: str, description: str = "", tags: list = None, category_id: str = "20"):
    """영상 업로드 (기본 비공개: 숏츠 검수 후 공개 전환)"""
    from googleapiclient.http import MediaFileUpload

    yt = get_service()
    body = {
        "snippet": {
            "title": title[:95],
            "description": description[:4900],
            "tags": (tags or [])[:30],
            "categoryId": category_id,  # 20=Gaming
        },
        "status": {
            "privacyStatus": "unlisted",  # 검수 후 public 전환
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(video_path, chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"    업로드 {int(status.progress() * 100)}%")
    vid = resp["id"]
    url = f"https://www.youtube.com/shorts/{vid}"
    print(f"    완료: {url}")
    return {"id": vid, "url": url}


def do_auth():
    """최초 1회 OAuth 인증 — 브라우저 열림"""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not SECRET_FILE.exists():
        raise SystemExit(f"client_secret 없음: {SECRET_FILE} — Google Cloud Console에서 발급 필요")
    flow = InstalledAppFlow.from_client_secrets_file(str(SECRET_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print("인증 완료 — 토큰 저장:", TOKEN_FILE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth", action="store_true", help="최초 OAuth 인증")
    ap.add_argument("--upload", metavar="MP4", help="업로드할 영상")
    ap.add_argument("--title", default="게임 숏츠")
    args = ap.parse_args()

    if args.auth:
        do_auth()
    elif args.upload:
        upload(args.upload, args.title)
    else:
        ap.print_help()
