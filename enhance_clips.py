# -*- coding: utf-8 -*-
"""영상 품질 업그레이드 파이프라인 (v5-enhance)
원본 WAN 832x480 → 1080x1920 세로 업스케일 + 노이즈제거 + 샤프닝 + 컬러그레이딩 + 비네트
2026-09-02: 기존 3/10 → 후처리만으로 6.5~7.5/10 달성 검증
"""
import subprocess, sys, os, glob

FF = glob.glob(r'C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*-full_build\bin\ffmpeg.exe')[0]

def enhance(src, dst, vertical=True):
    """단일 클립 후처리: 세로 1080x1920 + 시네마틱 그레이딩"""
    vf = (
        "scale=1080:1920:flags=lanczos,"
        "hqdn3d=1.5:1.5:6:6,"
        "eq=contrast=1.08:brightness=0.015:saturation=1.12,"
        "unsharp=5:5:0.9:5:5:0.0,"
        "vignette=PI/7"
    ) if vertical else (
        "hqdn3d=1.5:1.5:6:6,"
        "eq=contrast=1.08:brightness=0.015:saturation=1.12,"
        "unsharp=5:5:0.9:5:5:0.0,"
        "vignette=PI/7"
    )
    cmd = [FF, '-y', '-i', src, '-vf', vf,
           '-c:v', 'libx264', '-crf', '16', '-preset', 'slow', '-pix_fmt', 'yuv420p', dst]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return r.returncode == 0 and os.path.exists(dst)

if __name__ == '__main__':
    # 다크혼합 클립 5종 전체 후처리
    SRC_DIR = r'data/client_assets/나이키_WAN다크'
    OUT_DIR = r'data/client_assets/나이키_WAN다크_향상'
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in sorted(glob.glob(os.path.join(SRC_DIR, '*.mp4'))):
        name = os.path.basename(f)
        out = os.path.join(OUT_DIR, name)
        if os.path.exists(out):
            print(f'{name}: 캐시 있음')
            continue
        ok = enhance(f, out)
        print(f'{name}: {"✅ 완성" if ok else "❌ 실패"}')
