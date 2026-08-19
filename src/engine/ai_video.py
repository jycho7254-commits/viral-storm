# -*- coding: utf-8 -*-
"""
AI 비디오 생성기 — Z.AI CogVideoX-3 / Vidu Q1 (텍스트→비디오, 이미지→비디오)
기존 FFmpeg 슬라이드쇼를 대체하는 고품질 AI 영상 파이프라인.

모델:
  - cogvideox-3: 고품질 범용 ($0.2/video, 1080p) — quality/speed 모드
  - viduq1: 빠른 생성
지원: text-to-video, image-to-video (제품 이미지에서 영상 생성 — 바이럴 핵심)
"""
import base64
import json
import os
import time
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
API_KEY = os.environ.get("ZAI_API_KEY", "11a4e2078eda4b91a39ae7c28e2d28bd.LTmBqMWJEy99yVVK")


def _to_data_url(image_path: str) -> str:
    """로컬 이미지를 base64 data URL로 — i2v 입력용"""
    p = Path(image_path)
    mime = "image/png" if p.suffix == ".png" else "image/jpeg"
    b64 = base64.b64encode(p.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def generate_video(
    prompt: str,
    image_path: str = None,
    model: str = "cogvideox-3",
    quality: str = "quality",
    poll_interval: int = 10,
    max_wait: int = 600,
) -> dict:
    """AI 비디오 생성 (동기 래퍼 — 완료까지 폴링)
    image_path 있으면 image-to-video (제품 실사 기반), 없으면 text-to-video
    반환: {ok, video_url, id, elapsed}
    """
    from zai import ZaiClient

    client = ZaiClient(api_key=API_KEY)
    kwargs = {"model": model, "prompt": prompt, "quality": quality}
    if image_path:
        kwargs["image_url"] = _to_data_url(image_path)

    t0 = time.time()
    resp = client.videos.generations(**kwargs)
    vid = resp.id
    print(f"[AI비디오] 작업 시작 id={vid} (model={model}, i2v={bool(image_path)})")

    while time.time() - t0 < max_wait:
        time.sleep(poll_interval)
        r = client.videos.retrieve_videos_result(id=vid)
        s = r.task_status
        el = int(time.time() - t0)
        if s == "SUCCESS":
            # 응답에서 mp4 URL 추출
            video_url = None
            try:
                vr = r.video_result
                if isinstance(vr, list) and vr:
                    video_url = vr[0].get("url") or vr[0].get("video_url")
                elif isinstance(vr, dict):
                    video_url = vr.get("url") or vr.get("video_url")
            except Exception:
                pass
            if not video_url:
                video_url = getattr(r, "url", None)
            print(f"[AI비디오] 완료 ({el}초): {video_url}")
            return {"ok": True, "video_url": video_url, "id": vid, "elapsed": el}
        if s in ("FAIL", "FAILED"):
            print(f"[AI비디오] 실패: {json.dumps(r, default=str)[:300]}")
            return {"ok": False, "error": str(r)[:300], "id": vid}
        print(f"[AI비디오] 대기 중... {el}초 (상태: {s})")
    return {"ok": False, "error": f"타임아웃 {max_wait}초", "id": vid}


def download(url: str, out_path: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=120).read()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    open(out_path, "wb").write(data)
    return out_path


def make_viral_short(
    product_name: str,
    prompt: str,
    image_paths: list = None,
    out_path: str = None,
    model: str = "cogvideox-3",
    voice_script: list = None,
) -> str:
    """바이럴 숏츠 종합 파이프라인:
    1. 제품 이미지 기반 AI 비디오 생성 (i2v) — 클린룸 제품 쇼케이스
    2. (옵션) 나레이션 TTS 합성
    3. FFmpeg로 영상+오디오 mux + 자막
    """
    import sys
    sys.path.insert(0, str(BASE))
    from src.engine.shorts_maker import tts, sanitize_caption, esc, FFMPEG, F as FONT_DIR
    import subprocess

    tmp = BASE / "data" / "shorts_out" / "tmp_ai"
    tmp.mkdir(parents=True, exist_ok=True)
    if not out_path:
        from datetime import datetime
        out_path = str(BASE / "data" / "shorts_out" / f"ai_{int(time.time())}.mp4")

    # 1. AI 비디오 — 첫 이미지 기반 (없으면 t2v)
    img = image_paths[0] if image_paths else None
    vr = generate_video(prompt, image_path=img, model=model)
    if not vr["ok"]:
        raise RuntimeError(f"AI 비디오 실패: {vr.get('error')}")
    raw_mp4 = tmp / "ai_raw.mp4"
    download(vr["video_url"], str(raw_mp4))
    print(f"[AI비디오] 다운로드: {raw_mp4.stat().st_size // 1024}KB")

    # 2. TTS (스크립트 있으면)
    audio = None
    dur_cmd = [FFMPEG.replace("ffmpeg.exe", "ffprobe.exe"), "-v", "quiet",
               "-show_entries", "format=duration", "-of", "csv=p=0", str(raw_mp4)]
    vdur = float(subprocess.run(dur_cmd, capture_output=True, text=True).stdout.strip())
    if voice_script:
        audio = str(tmp / "voice.mp3")
        tts(" ".join(voice_script), audio, voice="female", rate="+6%", pitch="+1Hz")
        from src.engine.shorts_maker import make_bgm
        try:
            bgm = str(tmp / "bgm.mp3")
            make_bgm(bgm, vdur)
            mixed = str(tmp / "mixed.mp3")
            r = subprocess.run(
                [FFMPEG, "-y", "-i", audio, "-stream_loop", "-1", "-i", bgm,
                 "-filter_complex",
                 f"[1:a]volume=0.05,atrim=0:{vdur:.2f}[b];[0:a][b]amix=inputs=2:duration=first[aout]",
                 "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "128k", mixed],
                capture_output=True, text=True, encoding="utf-8", errors="replace")
            if r.returncode == 0:
                audio = mixed
        except Exception:
            pass

    # 3. 세로 리포맷(9:16) + 오디오 mux + 자막
    filters = ["scale=1080:1920:force_original_aspect_ratio=increase", "crop=1080:1920", "setsar=1"]
    if voice_script:
        n = len(voice_script)
        seg = vdur / n
        for i, line in enumerate(voice_script[:n]):
            cap = sanitize_caption(line)[:36]
            start, end = i * seg, (i + 1) * seg
            filters.append(
                f"drawtext=fontfile='{FONT_DIR}/malgun.ttf':text='{esc(cap)}':"
                f"fontcolor=white:fontsize=58:borderw=5:bordercolor=black:"
                f"x=(w-text_w)/2:y=h-320:enable='between(t\\,{start:.2f}\\,{end:.2f})'"
            )
    cmd = [FFMPEG, "-y", "-i", str(raw_mp4)]
    if audio:
        cmd += ["-i", audio]
    cmd += ["-vf", ",".join(filters), "-c:v", "libx264", "-preset", "medium", "-crf", "22",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-movflags", "+faststart"]
    if audio:
        cmd += ["-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest"]
    cmd += [out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"렌더 실패: {r.stderr[-400:]}")
    print(f"[AI비디오] 최종 숏츠: {out_path}")
    return out_path


if __name__ == "__main__":
    # 테스트 — 트릭컬 스크린샷으로 i2v
    img = str(BASE / "data/shorts_assets/trickcal_0.png")
    if not Path(img).exists():
        img = None
    out = make_viral_short(
        product_name="트릭컬 리바이브",
        prompt="Dynamic mobile game showcase: cute chibi characters animate and celebrate, colorful particle effects, vibrant game UI elements floating, smooth camera push-in, cinematic lighting, high quality game commercial",
        image_paths=[img] if img else None,
        voice_script=["이 게임 캐릭터 보고 만류 좀 해봐", "3등신 볼따구가 진짜 예술이야"],
        out_path=str(BASE / "data/shorts_out/ai_test_01.mp4"),
    )
    print("완성:", out)
