# -*- coding: utf-8 -*-
"""숏츠 v3 — WAN 성공 클립 재사용 하이브리드 (08-24)
기존 make_hybrid_short는 매번 WAN을 새로 돌려서 30분+ 소요.
이 스크립트는 이미 생성 검증된 클립(wan_v4_shoe_macro 등)을 즉시 조립:
WAN AI클립(훅) + 실사 제품컷(본론) + ASS자막 + 사이드체인 BGM
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, ".")
from src.engine.shorts_maker import tts, sanitize_caption, make_bgm, FFMPEG, esc, F as FONT_DIR
from src.engine.pro_audio import beat_sync_points  # 08-25: 비트싱크 컷 (Git 리서치 기법)

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "shorts_out" / "product_v3_hybrid.mp4"
TMP = BASE / "data" / "shorts_out" / "tmp_v3"
TMP.mkdir(parents=True, exist_ok=True)


def ass_time(x):
    h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def main():
    wan_clip = str(BASE / "data" / "shorts_out" / "wan_v4_shoe_macro.mp4")
    stills = [
        str(BASE / "data" / "shorts_assets" / "592c6f2eee_w0.png"),
        str(BASE / "data" / "data_placeholder.txt"),  # placeholder replaced below
    ]
    stills = [
        str(BASE / "data" / "shorts_assets" / "592c6f2eee_w0.png"),
        str(BASE / "data" / "shorts_assets" / "592c6f2eee_w1.png"),
        str(BASE / "data" / "shorts_assets" / "_0.png"),
    ]

    script = [
        "이 신발, AI가 아니면 못 담는 화면입니다",
        "디테일 하나하나 미쳤죠",
        "이 가격에 이 퀄리티가 진짜 되나 싶었어요",
        "착용감은 말할 것도 없고요",
        "지금 놓치면 다시 없을 가격",
    ]

    # 1. TTS
    full_mp3 = TMP / "voice.mp3"
    tts(" ".join(script), str(full_mp3), voice="female", rate="+4%", pitch="+0Hz")
    import wave  # noqa
    dur_out = subprocess.run(
        [FFMPEG, "-i", str(full_mp3)], capture_output=True, text=True
    )
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", dur_out.stderr)
    dur = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    print(f"나레이션 {dur:.1f}초")

    # 2. 세그먼트 배분: WAN 1클립(2.4s) + 실사 4컷 — 08-25: 컷 시점을 BGM 비트에 동기화
    wan_dur = 2.4
    beats = beat_sync_points(bgm_path=str(TMP / "bgm.mp3"), n_cuts=4) if (TMP / "bgm.mp3").exists() else None
    if beats:
        # 비트 시점을 남은 구간(2.4s~dur)에 맞게 스케일
        usable = [b for b in beats if b > wan_dur + 0.3]
        if len(usable) >= 3:
            cuts = [wan_dur] + usable[:4]
            if cuts[-1] < dur - 0.3:
                cuts.append(dur)
            seg_bounds = cuts[:5]
            print(f"비트싱크 컷: {['%.2f' % c for c in seg_bounds]}")
    seg2 = (dur - wan_dur) / 4  # 폴백: 균등 분할
    print(f"WAN 훅 {wan_dur}s + 실사 4컷 x {seg2:.1f}s")

    # 3. ASS 자막 (14자 줄바꿈 + fad)
    ass_lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Cap,Malgun Gothic,62,&H00FFFFFF,&H00000000,&H96000000,-1,5,2,2,60,60,430,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Text",
    ]
    t = 0.0
    bounds = [wan_dur, seg2, seg2, seg2, seg2]
    for line, b in zip(script, bounds):
        cap = sanitize_caption(line)
        chunks = [cap[j:j+14] for j in range(0, len(cap), 14)]
        text = "\\N".join(chunks[:3])
        ass_lines.append(
            f"Dialogue: 0,{ass_time(t)},{ass_time(t+b)},Cap,{{\\fad(180,180)}}{text}"
        )
        t += b
    (TMP / "subs.ass").write_text("\n".join(ass_lines) + "\n", encoding="utf-8-sig")

    # 4. BGM 사이드체인
    bgm = make_bgm(str(TMP / "bgm.mp3"), float(dur))
    mixed = TMP / "mixed.mp3"
    subprocess.run([
        FFMPEG, "-y", "-i", str(full_mp3), "-i", bgm,
        "-filter_complex",
        "[1:a]volume=0.07,atrim=0:%f[bg];[0:a]asplit=2[voice][sc];[bg][sc]sidechaincompress=threshold=0.02:ratio=8:attack=50:release=400:makeup=1[bduck];[voice][bduck]amix=inputs=2:duration=first:dropout_transition=2,loudnorm=I=-16:TP=-1.5:LRA=11[a]" % dur,
        "-map", "[a]", "-b:a", "192k", str(mixed),
    ], capture_output=True)

    # 5. 조립 — WAN(사전 리사이즈 1080x1920@30fps) + 실사 4컷 + 자막
    wan_pre = TMP / "wan_pre.mp4"
    subprocess.run([
        FFMPEG, "-y", "-i", wan_clip,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
        "-t", f"{wan_dur:.2f}", "-an", "-c:v", "libx264", "-crf", "20", str(wan_pre),
    ], capture_output=True)
    wan_clip = str(wan_pre)
    inputs = ["-i", wan_clip]
    for p in stills:
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{seg2+0.2:.2f}", "-i", p]
    inputs += ["-i", str(mixed)]

    fc_parts = [
        "[0:v]fps=30,settb=1/15360[v0];",
    ]
    for i, p in enumerate(stills, start=1):
        fc_parts.append(
            f"[{i}:v]split=2[sA{i}][sB{i}];"
            f"[sA{i}]scale=2160:3840:force_original_aspect_ratio=increase:flags=lanczos,crop=2160:3840,gblur=sigma=45[bg{i}];"
            f"[sB{i}]scale=2160:3840:force_original_aspect_ratio=decrease:flags=lanczos[fg{i}];"
            f"[bg{i}][fg{i}]overlay=(W-w)/2:(H-h)/2,"
            f"zoompan=z='min(zoom+0.0008,1.10)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(seg2*30)+30}:s=1080x1920:fps=30,setsar=1,settb=1/15360[v{i}];"
        )
    # xfade 체인
    chain = "[v0][v1]xfade=transition=fade:duration=0.3:offset=%.2f[x1];" % (wan_dur - 0.3)
    chain += "[x1][v2]xfade=transition=fade:duration=0.3:offset=%.2f[x2];" % (wan_dur + seg2 - 0.45)
    chain += "[x2][v3]xfade=transition=fade:duration=0.3:offset=%.2f[x3];" % (wan_dur + seg2*2 - 0.6)
    chain += "[x3][v4]xfade=transition=fade:duration=0.3:offset=%.2f[x4]" % (wan_dur + seg2*3 - 0.75)

    subs = str(TMP / "subs.ass").replace("\\", "/").replace(":", "\\:")
    fc = "".join(fc_parts) + chain + f";[x4]subtitles=filename='{subs}'[vout]"

    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "4:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "21",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest", str(OUT),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("FFMPEG 에러:", r.stderr[-1200:])
        sys.exit(1)
    print(f"완성: {OUT} ({OUT.stat().st_size//1024//1024}MB)")


if __name__ == "__main__":
    main()
