# -*- coding: utf-8 -*-
"""E2 스튜디오 렌더 모듈 (08-27) — orchestrator에서 make_short 엔진 호출
make_nike_v6.py 계열의 렌더 파이프라인을 함수화: 대사+감정태그 → 완성 mp4
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.engine.shorts_maker import tts, sanitize_caption, make_bgm, FFMPEG
from src.engine.pro_audio import beat_sync_points

BASE = Path(__file__).resolve().parents[1]
ASSETS = BASE / "data" / "shorts_assets"
OUT_DIR = BASE / "data" / "shorts_out"
FONTS = BASE / "assets" / "fonts"


def ass_time(x):
    h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def wrap_breath(text, cpl=13):
    """호흡 단위 줄바꿈 — 쉼표 우선, 조사 단위 차선"""
    text = text.rstrip("!").strip()
    if "," in text:
        parts = [p.strip() for p in re.split(r",\s*", text) if p.strip()]
        return "\\N".join(parts[:3])
    if len(text) > cpl:
        mid = max(text.rfind(" ", 0, cpl), cpl)
        return text[:mid].strip() + "\\N" + text[mid:].strip()
    return text


def pick_stills(resource_dir: str, category: str, n: int = 6) -> list:
    """리소스 우선순위: 형 전달 폴더 > 카테고리 기본 에셋"""
    rd = Path(resource_dir) if resource_dir else None
    if rd and rd.exists():
        imgs = sorted([p for p in rd.iterdir() if p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')])
        if imgs:
            return [str(p) for p in imgs[:n]]
    # 폴백: 기존 에셋 (제품 카테고리별)
    default = {
        "fashion": ["44a1b72c9e_w0.png", "44a1b72c9e_w1.png", "24ff718a60_w0.png",
                     "f521f0f22f_w0.png", "f521f0f22f_w1.png", "44a1b72c9e_w0.png"],
    }
    names = default.get(category, default["fashion"])
    out = []
    for nm in names:
        p = ASSETS / nm
        if p.exists():
            out.append(str(p))
    # 부족분은 WAN 사전생성 클립 프레임으로
    while len(out) < min(n, 3):
        out.append(str(ASSETS / "44a1b72c9e_w0.png"))
    return out[:n]


def render(job_id: str, product: str, category: str,
           script: list, resource_dir: str = "") -> str:
    """script: [{text, emotion, rate, pitch}, ...] → 완성 mp4 경로"""
    OUT_DIR.mkdir(exist_ok=True)
    TMP = OUT_DIR / f"tmp_job_{job_id[:8]}"
    TMP.mkdir(exist_ok=True)
    OUT = OUT_DIR / f"job_{job_id[:8]}.mp4"

    # 1. 감정 보이스 — 문장별 TTS 변주
    parts = []
    for i, seg in enumerate(script):
        f = TMP / f"voice_{i}.mp3"
        tts(seg["text"], str(f), voice="female",
            rate=seg.get("rate", "+8%"), pitch=seg.get("pitch", "+8Hz"))
        parts.append(str(f))
    concat = TMP / "list.txt"
    concat.write_text("\n".join(f"file '{p}'" for p in parts), encoding="utf-8")
    full = TMP / "voice.mp3"
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(full)],
                   capture_output=True)
    r = subprocess.run([FFMPEG, "-i", str(full)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    print(f"[E2] 감정 보이스 {dur:.1f}초 ({len(script)}문장)")

    # 2. BGM + 비트싱크
    bgm = make_bgm(str(TMP / "bgm.mp3"), dur)
    stills = pick_stills(resource_dir, category, n=min(len(script) - 1, 6))
    n_stills = len(stills)
    wan_clip = BASE / "data/shorts_out/wan_v4_shoe_macro.mp4"
    # 08-27: WAN 832x480 업스케일 화질 저하 (비전검수 지적) — 기본 OFF, 명시 시만 사용
    use_wan = False
    wan_dur = 2.4 if use_wan else 0.0
    seg2 = (dur - wan_dur) / max(n_stills, 1)

    # 3. WAN 훅 전처리
    inputs = []
    if use_wan:
        wan_pre = TMP / "wan_pre.mp4"
        subprocess.run([FFMPEG, "-y", "-i", str(wan_clip),
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=saturation=1.12",
                        "-t", "2.4", "-an", "-c:v", "libx264", "-crf", "20", str(wan_pre)], capture_output=True)
        inputs = ["-i", str(wan_pre)]

    # 4. ASS 자막 — 폰트 팔레트 3종 (훅=BlackHanSans노랑/본론=NotoSansKR/포인트=Jua)
    ass = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        # 08-27 형 피드백: 첫 폰트(BlackHanSans+노랑) 스타일로 전체 통일 — 크기만 역할별
        "Style: Cap,Black Han Sans,56,&H0020E8FF,&H000000FF,&H00101010,&H96000000,0,0,7,4,2,60,60,430,1",
        "Style: CapHi,Black Han Sans,66,&H0020E8FF,&H000000FF,&H00101010,&H96000000,0,0,7,4,2,60,60,420,1",
        "Style: CapPop,Black Han Sans,60,&H0020E8FF,&H000000FF,&H00101010,&H96000000,0,0,7,4,2,60,60,425,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    t = 0.0
    bounds = ([wan_dur] if use_wan else []) + [seg2] * n_stills
    style_map = {"hook": "CapHi", "cta": "CapHi", "pop": "CapPop"}
    for seg, b in zip(script, bounds):
        cap = sanitize_caption(seg["text"])
        text = wrap_breath(cap)
        st = style_map.get(seg.get("emotion", "body"), "Cap")
        fx = ("{\\fad(150,150)\\t(0,200,\\fscx108\\fscy108)\\t(200,350,\\fscx100\\fscy100)}"
              if st == "CapHi" else "{\\fad(150,150)}")
        ass.append(f"Dialogue: 0,{ass_time(t)},{ass_time(t + b)},{st},,0,0,0,,{fx}{text}")
        t += b
    (TMP / "subs.ass").write_text("\n".join(ass) + "\n", encoding="utf-8-sig")

    # 5. 사이드체인 믹스
    mixed = TMP / "mixed.mp3"
    subprocess.run([FFMPEG, "-y", "-i", str(full), "-i", bgm,
                    "-filter_complex",
                    f"[1:a]volume=0.07,atrim=0:{dur}[bg];[0:a]asplit=2[voice][sc];"
                    f"[bg][sc]sidechaincompress=threshold=0.02:ratio=8:attack=50:release=400:makeup=1[bduck];"
                    f"[voice][bduck]amix=inputs=2:duration=first:dropout_transition=2,"
                    f"loudnorm=I=-16:TP=-1.5:LRA=11[a]",
                    "-map", "[a]", "-b:a", "192k", str(mixed)], capture_output=True)

    # 6. 조립 — 줌펀치+채도+트랜지션 다양화
    for p in stills:
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{seg2 + 0.2:.2f}", "-i", p]
    inputs += ["-i", str(mixed)]
    nA = (1 if use_wan else 0) + n_stills
    audio_idx = nA

    fc = []
    if use_wan:
        fc.append("[0:v]settb=1/15360[v0];")
    for i in range(1 if use_wan else 0, nA):
        src = i
        fc.append(
            f"[{src}:v]split=2[sA{src}][sB{src}];"
            f"[sA{src}]scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos,crop=2160:3840,gblur=sigma=45,eq=saturation=1.1[bg{src}];"
            f"[sB{src}]scale=2160:3840:force_original_aspect_ratio=decrease:flags=lanczos[fg{src}];"
            f"[bg{src}][fg{src}]overlay=(W-w)/2:(H-h)/2,"
            f"zoompan=z='if(eq(on\\,0)\\,1.06\\,min(zoom+0.0008\\,1.10))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(seg2 * 30) + 30}:s=1080x1920:fps=30,setsar=1,settb=1/15360[v{src}];"
        )
    trans = ["fade", "smoothup", "circleopen", "fade", "slideleft"]
    chain = ""
    labels = (["v0"] if use_wan else []) + [f"v{src}" for src in range(1 if use_wan else 0, nA)]
    off = (wan_dur - 0.3 if use_wan else 0)
    prev = labels[0]
    for li in range(1, len(labels)):
        outv = f"x{li}"
        chain += f"[{prev}][{labels[li]}]xfade=transition={trans[(li-1) % len(trans)]}:duration=0.3:offset={max(off, 0):.2f}[{outv}];"
        prev = outv
        off += seg2 - 0.3
    final_label = prev
    subs_esc = str(TMP / "subs.ass").replace(chr(92), "/").replace(":", chr(92) + ":")
    fonts_esc = str(FONTS).replace(chr(92), "/").replace(":", chr(92) + ":")
    fc_txt = "".join(fc) + chain.rstrip(";") + f";[{final_label}]subtitles=filename='{subs_esc}':fontsdir='{fonts_esc}'[vout]"

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", fc_txt, "-map", "[vout]", "-map", f"{audio_idx}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-shortest", str(OUT)]
    rr = subprocess.run(cmd, capture_output=True, text=True)
    if rr.returncode != 0:
        raise RuntimeError(f"ffmpeg 실패: {rr.stderr[-400:]}")
    print(f"[E2] 완성: {OUT.name} ({OUT.stat().st_size // 1024 // 1024}MB)")
    return str(OUT)
