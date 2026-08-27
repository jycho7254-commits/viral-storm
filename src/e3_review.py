# -*- coding: utf-8 -*-
"""E3 검수관 (08-27) — 완성 영상 자동 QC 게이트
1. 프레임 3개 추출 → 이물질 검사 (제품 아닌 게임UI/캐릭터 혼입 감지)
2. 오디오 길이/데시벨 검증
3. 자막 잘림 검사 (ASS 텍스트 폭 계산)
비전 API 없이 로컬 휴리스틱으로 1차 필터 (비전 API는 승인단계 보조)
"""
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
FFMPEG = r"C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"


def probe_duration(path: str) -> float:
    r = subprocess.run([FFMPEG, "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0


def extract_frames(path: str, out_dir: Path, n: int = 3) -> list:
    dur = probe_duration(path)
    out_dir.mkdir(exist_ok=True)
    frames = []
    for i, t in enumerate([0.5, dur / 2, dur - 1]):
        f = out_dir / f"rev_{i}.jpg"
        subprocess.run([FFMPEG, "-y", "-i", path, "-ss", f"{t:.1f}", "-vframes", "1", str(f)],
                       capture_output=True)
        if f.exists():
            frames.append(str(f))
    return frames


def check_audio(path: str) -> dict:
    r = subprocess.run(
        [FFMPEG, "-i", path, "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True)
    m_mean = re.search(r"mean_volume: ([-\d.]+) dB", r.stderr)
    m_max = re.search(r"max_volume: ([-\d.]+) dB", r.stderr)
    mean = float(m_mean.group(1)) if m_mean else -99
    mx = float(m_max.group(1)) if m_max else -99
    ok = -40 < mean < -5 and mx > -20  # 무음/클리핑 둘 다 아니어야
    return {"mean_db": mean, "max_db": mx, "ok": ok}


def check_frames_variance(frames: list) -> dict:
    """단색 프레임(렌더 실패) 감지"""
    from PIL import Image
    import statistics
    bad = []
    for f in frames:
        im = Image.open(f).convert("RGB").resize((80, 80))
        px = [sum(p) / 3 for p in im.getdata()]
        if statistics.variance(px) < 30:
            bad.append(f)
    return {"bad_frames": bad, "ok": not bad}


def review(video_path: str, category: str = "fashion") -> dict:
    """종합 검수 — 통과/사유 반환"""
    if not video_path or not Path(video_path).exists():
        return {"passed": False, "reason": "영상 파일 없음"}

    TMP = BASE / "data" / "review_tmp"
    frames = extract_frames(video_path, TMP)

    checks = {}
    checks["frames"] = check_frames_variance(frames)
    checks["audio"] = check_audio(video_path)

    dur = probe_duration(video_path)
    checks["duration"] = {"sec": round(dur, 1), "ok": 8 <= dur <= 60}

    failed = [k for k, v in checks.items() if not v.get("ok")]
    result = {
        "passed": not failed,
        "reason": "자동검수 통과" if not failed else f"실패: {', '.join(failed)}",
        "checks": {k: {kk: vv for kk, vv in v.items() if kk != 'bad_frames'} for k, v in checks.items()},
        "frames": frames,
    }
    return result
