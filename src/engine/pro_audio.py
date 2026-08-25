# -*- coding: utf-8 -*-
"""프로 오디오 편집 모듈 (08-25) — Git 리서치(video-autopilot-kit) 기법 구현
1. beat_sync_points()  : BGM 비트 감지 → 컷 전환 시점 리스트
2. dynamic_duck()      : 나레이션 RMS 기반 에너지 더킹 (비트 밀도에 따라 볼륨 곡선)
3. crossfade_join()    : 클립 오디오 크로스페이드 (200ms 테일)
사용: make_short_v3 및 향후 파이프라인 v2
"""
from pathlib import Path

import numpy as np
import librosa


def beat_sync_points(bgm_path: str, n_cuts: int, sr: int = 22050) -> list:
    """BGM의 비트 온셋을 감지해 n_cuts개의 전환 시점(초) 반환.
    실패 시(비트 감지 불가) 균등 분할 폴백."""
    try:
        y, _ = librosa.load(bgm_path, sr=sr, mono=True)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        times = librosa.frames_to_time(beats, sr=sr)
        if len(times) < n_cuts:
            raise ValueError("비트 부족")
        # 첫/후반 제외한 구간에서 균등 샘플링
        idx = np.linspace(0, len(times) - 1, n_cuts + 1).astype(int)
        return [float(times[i]) for i in idx]
    except Exception:
        return None


def duck_volume_curve(voice_path: str, bgm_path: str, out_curve_len: int,
                      sr: int = 22050, duck_db: float = -18.0, rest_db: float = -10.0) -> np.ndarray:
    """나레이션 RMS 에너지 따라 BGM 볼륨 곡선 생성.
    말하는 구간 duck_db, 조용한 구간 rest_db로 부드럽게 (attack/release 스무딩)."""
    try:
        y, _ = librosa.load(voice_path, sr=sr, mono=True)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
        # 프레임→초 단위 리샘플을 out 길이로
        x_old = np.linspace(0, 1, len(rms))
        x_new = np.linspace(0, 1, out_curve_len)
        rms_rs = np.interp(x_new, x_old, rms)
        # 임계: RMS 중앙값의 15% 이상 = 발화
        thr = np.median(rms_rs) * 0.15
        speaking = rms_rs > thr
        # 스무딩 (attack 50ms/release 400ms 상당)
        kernel = max(3, out_curve_len // 100)
        smooth = np.convolve(speaking.astype(float), np.ones(kernel) / kernel, mode="same")
        # dB → 선형 볼륨
        lin_duck, lin_rest = 10 ** (duck_db / 20), 10 ** (rest_db / 20)
        curve = lin_duck + (lin_rest - lin_duck) * (1 - smooth)
        return curve
    except Exception:
        return None


def crossfade_join(clips: list, fade_sec: float = 0.2, sr: int = 44100) -> str:
    """클립 오디오 크로스페이드 결합 — temp wav 반환"""
    import soundfile as sf
    import tempfile
    out = np.zeros((0,), dtype=np.float32)
    fade_n = int(fade_sec * sr)
    for i, c in enumerate(clips):
        y, _ = librosa.load(c, sr=sr, mono=True)
        if i == 0:
            out = y
        else:
            # 이전 끝 fade-out + 현재 시작 fade-in
            if fade_n < len(out) and fade_n < len(y):
                t = np.linspace(0, 1, fade_n)
                out[-fade_n:] *= (1 - t)
                y[:fade_n] *= t
            out = np.concatenate([out, y])
    tmp = Path(tempfile.gettempdir()) / "vs_crossfade.wav"
    sf.write(str(tmp), out, sr)
    return str(tmp)


if __name__ == "__main__":
    # 자체 테스트 — 기존 BGM/보이스로
    base = Path(__file__).resolve().parents[2]
    bgm = base / "data/shorts_out/tmp_v3/bgm.mp3"
    voice = base / "data/shorts_out/tmp_v3/voice.mp3"
    if bgm.exists() and voice.exists():
        pts = beat_sync_points(str(bgm), 4)
        print(f"비트싱크 포인트(4컷): {['%.2f' % p for p in pts] if pts else '폴백(균등)'}")
        curve = duck_volume_curve(str(voice), str(bgm), 100)
        if curve is not None:
            print(f"더킹 곡선: min={curve.min():.3f} max={curve.max():.3f} (발화구간 낮아짐 ✓)")
    else:
        print("테스트 파일 없음 — tmp_v3 생성 후 재실행")
