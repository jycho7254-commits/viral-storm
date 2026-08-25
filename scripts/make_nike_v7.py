# -*- coding: utf-8 -*-
"""나이키 에어포스 v6 — 형 피드백 4종 반영 (08-25)
1. 트릭컬 이미지 제거 → 에어포스 5컷만
2. 자막 스타일 업그레이드 — 볼드체+외곽선+그림자+노랑강조 (레퍼런스 AI숏츠 스타일)
3. 감정 실린 보이스 — 문장별 rate/pitch 변주 (훅=신남/본론=차분/CTA=강조)
4. 줄바꿈 — 호흡 단위 끊어읽기 (조사 단위)
+ 비트싱크 컷, 줌펀치, 색감보정
"""
import subprocess, sys, re
from pathlib import Path

sys.path.insert(0, ".")
from src.engine.shorts_maker import tts, sanitize_caption, make_bgm, FFMPEG
from src.engine.pro_audio import beat_sync_points

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data/shorts_out/nike_airforce_v7_20s.mp4"
TMP = BASE / "data/shorts_out/tmp_v7"
TMP.mkdir(parents=True, exist_ok=True)

# ── 문장별 감정 변주 (rate, pitch) ──
SCRIPT = [
    # (대사, rate, pitch, 감정)
    ("이 신발, AI가 아니면 못 담는 화면이에요!", '+12%', '+15Hz', 'hook'),
    ("에어포스는, 진짜 뭐든 잘 어울려요", '+4%', '-4Hz', 'body'),
    ("청바지? 수트? 전부 정답이에요", '+8%', '+8Hz', 'pop'),
    ("화이트 하나로 코디 완성!", '+10%', '+12Hz', 'pop'),
    ("가죽 광택까지 살아있는 디테일", '+2%', '-6Hz', 'body'),
    ("10년을 신어도 질리지 않는 클래식", '+3%', '-3Hz', 'body'),
    ("지금이, 제일 싼 시즌이에요", '+15%', '+22Hz', 'cta'),
]
STILLS = [
    BASE / "data/shorts_assets/44a1b72c9e_w0.png",
    BASE / "data/shorts_assets/44a1b72c9e_w1.png",
    BASE / "data/shorts_assets/24ff718a60_w0.png",
    BASE / "data/shorts_assets/f521f0f22f_w0.png",
    BASE / "data/shorts_assets/f521f0f22f_w1.png",
    BASE / "data/shorts_assets/44a1b72c9e_w0.png",
]


def ass_time(x):
    h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def wrap_breath(text, cpl=13):
    """호흡 단위 줄바꿈 — 쉼표/조사 뒤 우선 끊기 (4번 피드백)"""
    text = text.rstrip('!').strip()
    # 쉼표 우선
    if ',' in text or '，' in text:
        parts = re.split(r'[,，]\s*', text)
        return '\\N'.join(p.strip() + (',' if i < len(parts)-1 else '') for i, p in enumerate(parts) if p.strip())[:3*20]
    # 길면 조사 단위
    if len(text) > cpl:
        mid = text.rfind(' ', 0, cpl)
        if mid < 0:
            mid = cpl
        return text[:mid].strip() + '\\\\N' + text[mid:].strip()
    return text


def main():
    # 1. 감정 보이스 — 문장별 TTS 후 이어붙이기
    parts = []
    for i, (line, rate, pitch, _) in enumerate(SCRIPT):
        seg = TMP / f"voice_{i}.mp3"
        tts(line, str(seg), voice='female', rate=rate, pitch=pitch)
        parts.append(str(seg))
    concat_list = TMP / "list.txt"
    concat_list.write_text('\n'.join(f"file '{p}'" for p in parts), encoding='utf-8')
    full_mp3 = TMP / "voice.mp3"
    subprocess.run([FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_list), '-c', 'copy', str(full_mp3)], capture_output=True)
    r = subprocess.run([FFMPEG, '-i', str(full_mp3)], capture_output=True, text=True)
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    dur = int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
    print(f"감정 보이스 {dur:.1f}초 (5문장 변주)")

    # 2. BGM + 비트싱크
    bgm = make_bgm(str(TMP/'bgm.mp3'), dur)
    wan_clip = str(BASE / "data/shorts_out/wan_v4_shoe_macro.mp4")
    wan_pre = TMP / "wan_pre.mp4"
    subprocess.run([FFMPEG, '-y', '-i', wan_clip,
        '-vf', "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=saturation=1.12",
        '-t', '2.4', '-an', '-c:v', 'libx264', '-crf', '20', str(wan_pre)], capture_output=True)
    wan_dur = 2.4
    seg2 = (dur - wan_dur) / len(STILLS)
    print(f"WAN 훅 {wan_dur}s + 실사 {len(STILLS)}컷 x {seg2:.1f}s")

    # 3. ASS 자막 — 레퍼런스 스타일 (2번 피드백)
    #    볼드+두꺼운외곽선+그림자 / 감정구간 노랑강조 / 호흡 줄바꿈
    ass_lines = [
        '[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1080', 'PlayResY: 1920', 'WrapStyle: 2', '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        # 폰트 팔레트 (08-25): 훅/CTA=BlackHanSans(임팩트), 본론=NotoSansKR, 팝=Jua
        # libass 폰트명은 폰트 내부명 사용 — 파일은 assets/fonts에 두고 FontDir 지정
        'Style: Cap,Noto Sans KR,60,&H00FFFFFF,&H000000FF,&H00101010,&H96000000,-1,0,6,3,2,60,60,430,1',
        'Style: CapHi,Black Han Sans,66,&H0020E8FF,&H000000FF,&H00101010,&H96000000,0,0,7,4,2,60,60,420,1',  # 훅/CTA 임팩트체+노랑
        'Style: CapPop,Jua,62,&H00FFFFFF,&H000000FF,&H00101010,&H96000000,0,0,6,3,2,60,60,425,1',  # 포인트 부드러운체
        '', '[Events]', 'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    t = 0.0
    bounds = [wan_dur] + [seg2]*len(STILLS)
    for (line, _, _, emo), b in zip(SCRIPT, bounds):
        cap = sanitize_caption(line)
        text = wrap_breath(cap)
        style = {'hook': 'CapHi', 'cta': 'CapHi', 'pop': 'CapPop'}.get(emo, 'Cap')
        # 등장 효과: 훅/CTA는 커지면서 팝
        fx = '{\fad(150,150)\t(0,200,\fscx108\fscy108)\t(200,350,\fscx100\fscy100)}' if style == 'CapHi' else '{\fad(150,150)}'
        ass_lines.append(f'Dialogue: 0,{ass_time(t)},{ass_time(t+b)},{style},,0,0,0,,{fx}{text}')
        t += b
    (TMP/'subs.ass').write_text('\n'.join(ass_lines)+'\n', encoding='utf-8-sig')

    # 4. 사이드체인 믹스
    mixed = TMP/'mixed.mp3'
    subprocess.run([FFMPEG, '-y', '-i', str(full_mp3), '-i', bgm,
        '-filter_complex',
        f'[1:a]volume=0.07,atrim=0:{dur}[bg];[0:a]asplit=2[voice][sc];[bg][sc]sidechaincompress=threshold=0.02:ratio=8:attack=50:release=400:makeup=1[bduck];[voice][bduck]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[a]',
        '-map', '[a]', '-b:a', '192k', str(mixed)], capture_output=True)

    # 5. 조립 — 줌펀치+색감+다양한 트랜지션
    inputs = ['-i', str(wan_pre)]
    for p in STILLS:
        inputs += ['-loop', '1', '-framerate', '30', '-t', f'{seg2+0.2:.2f}', '-i', str(p)]
    inputs += ['-i', str(mixed)]
    nA = 1 + len(STILLS)

    fc = [f'[0:v]settb=1/15360[v0];']
    for i in range(1, nA):
        fc.append(
            f'[{i}:v]split=2[sA{i}][sB{i}];'
            f'[sA{i}]scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos,crop=2160:3840,gblur=sigma=45,eq=saturation=1.1[bg{i}];'
            f'[sB{i}]scale=2160:3840:force_original_aspect_ratio=decrease:flags=lanczos[fg{i}];'
            f'[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,'
            f"zoompan=z='if(eq(on\,0)\,1.06\,min(zoom+0.0008\,1.10))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(seg2*30)+30}:s=1080x1920:fps=30,setsar=1,settb=1/15360[v{i}];"
        )
    trans = ['fade', 'smoothup', 'circleopen', 'fade', 'slideleft']
    chain = ''
    prev = 'v0'
    off = wan_dur - 0.3
    for i in range(1, nA):
        out_v = f'x{i}'
        chain += f'[{prev}][v{i}]xfade=transition={trans[(i-1)%len(trans)]}:duration=0.3:offset={max(off,0):.2f}[{out_v}];'
        prev = out_v
        off += seg2 - 0.3
    subs = str(TMP/'subs.ass').replace(chr(92), '/')
    # subtitles 필터 인자 이스케이프: 콜론은 필터 옵션 구분자라 \: 필요 (단일 backslash)
    esc_colon = chr(92) + ':'
    subs_esc = subs.replace(':', esc_colon)
    fonts_dir = str(BASE / 'assets' / 'fonts').replace(chr(92), '/').replace(':', esc_colon)
    fc_txt = ''.join(fc) + chain.rstrip(';') + f";[{prev}]subtitles=filename='{subs_esc}':fontsdir='{fonts_dir}'[vout]"

    cmd = [FFMPEG, '-y'] + inputs + [
        '-filter_complex', fc_txt, '-map', '[vout]', '-map', f'{nA}:a',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-r', '30',
        '-c:a', 'aac', '-b:a', '160k', '-shortest', str(OUT)]
    rr = subprocess.run(cmd, capture_output=True, text=True)
    if rr.returncode != 0:
        print('FFMPEG 에러:', rr.stderr[-800:]); sys.exit(1)
    print(f'완성: {OUT} ({OUT.stat().st_size//1024//1024}MB)')


if __name__ == '__main__':
    main()
