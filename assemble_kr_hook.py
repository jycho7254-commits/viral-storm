# -*- coding: utf-8 -*-
"""kr_hook_v1 조립 — 클립4개+TTS+자막 (TTS hang 회피 수동 조립)"""
import sys, subprocess, glob, os
sys.path.insert(0, '.')
from src.engine.hybrid_shorts import probe_dur
from src.engine.shorts_maker import sanitize_caption
from PIL import Image, ImageDraw, ImageFont

FF = glob.glob(r'C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*-full_build\bin\ffmpeg.exe')[0]

voice = 'data/shorts_out/tmp_hybrid/voice_fast.mp3'
adur = probe_dur(voice)
print(f'음성: {adur:.1f}초')

lines = [
    '에어포스 신는데 아직도 끈 풀려요?',
    '저도 매번 그랬는데 방법 하나 바꿨더니 끝났어요',
    '위 두 구멍만 건너뛰면 끝',
    '이렇게 묶으면 하루종일 풀릴 일 없어요',
    '발등도 안 아피고 더 예뻐 보여요',
    '오늘부터 바로 해보세요',
]
n = len(lines)
seg = min(adur / n, 2.5)
clips = [f'data/shorts_out/tmp_hybrid/clip_{i}.mp4' for i in range(4)]

# 자막 PNG
os.makedirs('data/shorts_out/tmp_hybrid/subs2', exist_ok=True)
FONT_DIR = 'assets/fonts'
fp = os.path.join(FONT_DIR, 'BlackHanSans-Regular.ttf')
font_h = ImageFont.truetype(fp, 72) if os.path.exists(fp) else ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 64)
for i, ln in enumerate(lines):
    img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((540, 1480), sanitize_caption(ln), fill=(255, 255, 255, 255), font=font_h,
           anchor='mm', stroke_width=6, stroke_fill=(45, 32, 20, 255))
    img.save(f'data/shorts_out/tmp_hybrid/subs2/sub{i}.png')
print('자막 6장 생성')

# 입력: 클립 n개(4종 순환) + 음성 + 자막 n개
inputs = []
for i in range(n):
    inputs += ['-stream_loop', '-1', '-t', f'{seg + 0.3:.2f}', '-i', clips[i % 4]]
inputs += ['-i', voice]
for i in range(n):
    inputs += ['-loop', '1', '-t', f'{seg:.2f}', '-i', f'data/shorts_out/tmp_hybrid/subs2/sub{i}.png']

# 필터: 각 클립 trim/scale → 자막 오버레이 체인
parts = []
for i in range(n):
    parts.append(
        f'[{i}:v]trim=0:{seg:.2f},setpts=PTS-STARTPTS,'
        f'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v{i}]'
    )
for i in range(n):
    parts.append(f'[{n + 1 + i}:v]format=rgba[s{i}]')

chain = []
en = "enable='between(t,{},{})".format('{:.2f}', '{:.2f}')
for i in range(n):
    lo = i * seg
    hi = (i + 1) * seg
    if i == 0:
        chain.append(f'[v0][s0]overlay=enable=\'between(t,{lo:.2f},{hi:.2f})\'[vx0]')
    else:
        chain.append(f'[vx{i-1}][s{i}]overlay=enable=\'between(t,{lo:.2f},{hi:.2f})\'[vx{i}]')

fc = ';'.join(parts + chain)
cmd = [FF, '-y'] + inputs + [
    '-filter_complex', fc,
    '-map', f'[vx{n-1}]', '-map', f'{n}:a',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '128k', '-shortest',
    'data/shorts_out/job_kr_hook_v1_raw.mp4',
]
r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, encoding='utf-8', errors='replace')
print('렌더:', 'OK' if r.returncode == 0 else 'FAIL')
if r.returncode != 0:
    print(r.stderr[-400:])
    sys.exit(1)

# 후처리 (품질 v5)
vf = ("hqdn3d=1.5:1.5:6:6,eq=contrast=1.08:brightness=0.015:saturation=1.12,"
      "unsharp=5:5:0.9:5:5:0.0,vignette=PI/7")
r2 = subprocess.run(
    [FF, '-y', '-i', 'data/shorts_out/job_kr_hook_v1_raw.mp4', '-vf', vf,
     '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'copy',
     'data/shorts_out/job_kr_hook_v1.mp4'],
    capture_output=True, text=True, timeout=900, encoding='utf-8', errors='replace')
print('후처리:', 'OK' if r2.returncode == 0 else 'FAIL')
d = probe_dur('data/shorts_out/job_kr_hook_v1.mp4')
print(f'최종: {d:.1f}초')
