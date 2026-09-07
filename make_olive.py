# -*- coding: utf-8 -*-
"""올리브영 꿀템 숏츠 — 마스터 패턴 v2 첫 적용
- 46~60초 완주형 (8문장 × 6초 컷)
- 질문형 훅 + 숫자 훅
- 제목 괄호 태그
- 제품: 아비브 어성초 에센스 패드 (올영 인기 진정템)
"""
import sys, subprocess, glob, os, asyncio
sys.path.insert(0, '.')

PY = sys.executable
OUT = 'data/shorts_out/job_olive_v1.mp4'
TITLE = '[올영꿀템] 트러블 흔적 이거 하나로 지우는 중입니다 (3주차)'

# 마스터 패턴 v2 기반 대본 — 질문형 훅 시작, 숫자, 1인칭 경험, CTA
LINES = [
    '아침에 거울 보다가 놀란 적 있으세요?',
    '볼에 난 트러블 자국 때문에 파운데이션만 두껍게 발랐어요',
    '올리브영 가서 직원분한테 물어봤는데 딱 하나 추천받았어요',
    '아비브 어성초 에센스 패드인데요',
    '하루에 패드 한 장으로 톡톡 닦아주기만 하면 돼요',
    '3주쯤 쓰니까 붉은기가 확 눈에 띄게 가라앉았어요',
    '지금 올영세일이라서 두 개 사는 게 더 싸요',
    '트러블 자국 때문에 고민이면 이번 기회에 쟁여보세요',
]

voice = 'data/shorts_out/tmp_hybrid/voice_olive.mp3'
os.makedirs(os.path.dirname(voice), exist_ok=True)

# 1) TTS (30초 타임아웃 — hang 방지)
async def tts():
    import edge_tts
    txt = ' '.join(LINES)
    c = edge_tts.Communicate(txt, 'ko-KR-SunHiNeural', rate='+9%')
    await c.save(voice)
asyncio.run(tts())
print('TTS 완료')

from src.engine.hybrid_shorts import probe_dur
adur = probe_dur(voice)
print(f'음성 {adur:.1f}초')

n = len(LINES)
seg = max(3.0, min(adur / n, 6.0))  # 마스터 v2: 3~6초 유연

# 2) WAN 클립 4종 생성 — 화장품 특화 구도 (사용 컷 + 클로즈업)
from src.engine.wan_fast import fast_generate
tmp = 'data/shorts_out/tmp_hybrid/olive'
os.makedirs(tmp, exist_ok=True)
PROMPTS = [
    'woman gently wiping her cheek with a round cotton pad, soft bathroom lighting, skincare routine, close-up on cheek, clean aesthetic',
    'stack of green herbal essence pads in a jar on white table, morning light, product close-up, fresh and clean',
    'hand holding a soaked cotton pad showing essence texture, macro shot, water droplets, spa feeling',
    'woman touching her clear smooth cheek smiling softly at mirror, natural daylight, before-after glow',
]
clips = []
for i, p in enumerate(PROMPTS):
    cp = f'{tmp}/clip_{i}.mp4'
    if os.path.exists(cp):
        clips.append(cp)
        continue
    fast_generate(prompt=p, out_path=cp, num_frames=49, steps=8, height=480, width=832)
    clips.append(cp)
    print(f'클립 {i+1}/4 완료')

# 3) 자막 PNG (BlackHanSans 훅 폰트)
from PIL import Image, ImageDraw, ImageFont
from src.engine.shorts_maker import sanitize_caption
os.makedirs(f'{tmp}/subs', exist_ok=True)
fp = 'assets/fonts/BlackHanSans-Regular.ttf'
font_h = ImageFont.truetype(fp, 68) if os.path.exists(fp) else ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 60)
for i, ln in enumerate(LINES):
    img = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((540, 1450), sanitize_caption(ln), fill=(255, 255, 255, 255), font=font_h,
           anchor='mm', stroke_width=6, stroke_fill=(30, 60, 40, 255))
    img.save(f'{tmp}/subs/sub{i}.png')
print('자막 완료')

# 4) 세그먼트 렌더 + concat + 후처리
FF = glob.glob(r'C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*-full_build\bin\ffmpeg.exe')[0]
os.makedirs(f'{tmp}/segs', exist_ok=True)
for i in range(n):
    seg_file = f'{tmp}/segs/seg{i}.mp4'
    if os.path.exists(seg_file):
        continue
    r = subprocess.run(
        [FF, '-y', '-stream_loop', '-1', '-t', f'{seg:.2f}', '-i', clips[i % 4],
         '-loop', '1', '-t', f'{seg:.2f}', '-i', f'{tmp}/subs/sub{i}.png',
         '-filter_complex',
         '[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v];'
         '[1:v]format=rgba[s];[v][s]overlay[vout]',
         '-map', '[vout]', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
         '-pix_fmt', 'yuv420p', '-r', '30', seg_file],
        capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print(f'seg{i} FAIL:', r.stderr[-150:])
        sys.exit(1)
print('세그먼트 완료')

open(f'{tmp}/list.txt', 'w').write(''.join(f"file 'segs/seg{i}.mp4'\n" for i in range(n)))
raw = 'data/shorts_out/job_olive_v1_raw.mp4'
r = subprocess.run([FF, '-y', '-f', 'concat', '-safe', '0', '-i', f'{tmp}/list.txt',
                    '-i', voice, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', raw],
                   capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
assert r.returncode == 0, r.stderr[-200:]

# 후처리 (품질 v5)
vf = "hqdn3d=1.5:1.5:6:6,eq=contrast=1.08:brightness=0.03:saturation=1.12,unsharp=5:5:0.9:5:5:0.0,vignette=PI/7"
r2 = subprocess.run([FF, '-y', '-i', raw, '-vf', vf,
                     '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p',
                     '-c:a', 'copy', OUT],
                    capture_output=True, text=True, timeout=900, encoding='utf-8', errors='replace')
assert r2.returncode == 0, r2.stderr[-200:]
d = probe_dur(OUT)
print(f'완성: {OUT} | {d:.1f}초 | 제목: {TITLE}')
