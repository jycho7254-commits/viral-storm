# -*- coding: utf-8 -*-
"""올리브영 v2 — 형체 문제 해결 (레퍼런스 학습 기반 보충)
핵심 수정:
- 뭉개진 컷(제품 단독 클로즈업) 제거 → 전 컷 "사람 손+행동" 중심
- 레퍼런스 분석: 상위 제품 바이럴은 손이 하는 장면 위주 (제품 단독 노출 적음)
- WAN이 잘하는 것만 시킴: 사람 손/얼굴/사용장면 (제품 정지물 X)
- 컷 수 8→6으로 축소 (형체 명확한 컷만)
"""
import sys, subprocess, glob, os, asyncio
sys.path.insert(0, '.')

OUT = 'data/shorts_out/job_olive_v2.mp4'
TITLE = '[올영꿀템] 볼 트러블 자국 3주 만에 지운 패드 (실사용)'

LINES = [
    '아침에 거울 보다가 놀란 적 있으세요?',
    '볼에 난 트러블 자국 때문에 파운데이션만 두껍게 발랐어요',
    '올리브영 직원분이 딱 하나 골라준 어성초 패드인데요',
    '하루에 한 장씩 볼에 톡톡 닦아주기만 하면 돼요',
    '3주쯤 쓰니까 붉은기가 눈에 띄게 가라앉았어요',
    '지금 올영세일이라 두 개 사는 게 더 싸요',
]

voice = 'data/shorts_out/tmp_hybrid/voice_olive2.mp3'
os.makedirs(os.path.dirname(voice), exist_ok=True)

async def tts():
    import edge_tts
    c = edge_tts.Communicate(' '.join(LINES), 'ko-KR-SunHiNeural', rate='+9%')
    await c.save(voice)
asyncio.run(tts())
print('TTS 완료')

from src.engine.hybrid_shorts import probe_dur
adur = probe_dur(voice)
print(f'음성 {adur:.1f}초')
n = len(LINES)
seg = max(3.0, min(adur / n, 6.0))

# ══ 전 컷 "사람 손+행동" — WAN이 형체를 잘 잡는 조합만 ══
from src.engine.wan_fast import fast_generate
tmp = 'data/shorts_out/tmp_hybrid/olive2'
os.makedirs(tmp, exist_ok=True)
PROMPTS = [
    # 컷1: 거울 보는 여성 (얼굴+손 — 명확한 형체)
    'young woman looking into bathroom mirror touching her cheek with fingers, concerned expression, bright morning light, face clearly visible',
    # 컷2: 손이 패드로 볼 닦기 (손+행동 — 이미 v1에서 명확했던 컷 재사용 계열)
    'woman wiping her cheek gently with a round cotton pad held by fingers, close-up on hand and pad motion, soft bathroom lighting',
    # 컷3: 손바닥에 패드 올리고 패드 짜기? X — 손가락으로 패드 집어 사용 (행동)
    'fingers picking up a round moist cotton pad from a small jar, then pressing it on cheek, hand movement clearly visible, clean table',
    # 컷4: 패드로 볼 톡톡 두드리기 (반복 행동 — 역동성)
    'woman patting her cheek with cotton pad using tapping motion, hand rhythmically moving, soft natural skin, warm tone',
    # 컷5: 매끈해진 볼 만지며 미소 (결과 — v1 컷4 계열, 명확했음)
    'woman touching her smooth clear cheek smiling at mirror, satisfied expression, natural daylight, glowing healthy skin',
    # 컷6: 화장품 가방에 패드 넣는 마무리 (행동 마감)
    'woman putting small cosmetic jar into shopping bag on table, hands folding bag, cozy warm light, shopping haul feeling',
]
clips = []
for i, p in enumerate(PROMPTS):
    cp = f'{tmp}/clip_{i}.mp4'
    if os.path.exists(cp):
        clips.append(cp)
        continue
    fast_generate(prompt=p, out_path=cp, num_frames=49, steps=8, height=480, width=832)
    clips.append(cp)
    print(f'클립 {i+1}/{len(PROMPTS)} 완료')

# 자막
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

# 세그먼트 + 조립 + 후처리
FF = glob.glob(r'C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*-full_build\bin\ffmpeg.exe')[0]
os.makedirs(f'{tmp}/segs', exist_ok=True)
for i in range(n):
    seg_file = f'{tmp}/segs/seg{i}.mp4'
    if os.path.exists(seg_file):
        continue
    r = subprocess.run(
        [FF, '-y', '-stream_loop', '-1', '-t', f'{seg:.2f}', '-i', clips[i % len(clips)],
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
raw = 'data/shorts_out/job_olive_v2_raw.mp4'
r = subprocess.run([FF, '-y', '-f', 'concat', '-safe', '0', '-i', f'{tmp}/list.txt',
                    '-i', voice, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', raw],
                   capture_output=True, text=True, timeout=300, encoding='utf-8', errors='replace')
assert r.returncode == 0, r.stderr[-200:]

vf = "hqdn3d=1.5:1.5:6:6,eq=contrast=1.08:brightness=0.03:saturation=1.12,unsharp=5:5:0.9:5:5:0.0,vignette=PI/7"
r2 = subprocess.run([FF, '-y', '-i', raw, '-vf', vf,
                     '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p',
                     '-c:a', 'copy', OUT],
                    capture_output=True, text=True, timeout=900, encoding='utf-8', errors='replace')
assert r2.returncode == 0, r2.stderr[-200:]
d = probe_dur(OUT)
print(f'완성: {OUT} | {d:.1f}초')
