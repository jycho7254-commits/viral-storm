# -*- coding: utf-8 -*-
"""
YouTube Shorts 파이프라인 — 게임 바이럴 특화
AI영상 느낌 제거 설계:
  1. edge-tts 한국어 자연 목소리 (rate/pitch 변주)
  2. 실제 게임 스크린샷 슬라이드쇼
  3. Ken Burns 줌/팬 효과
  4. 바이럴 스타일 자막 (drawtext)
구성: 1080x1920 (9:16)
"""
import asyncio
import os
import re
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
FFMPEG = r"C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"

VOICES = {
    "male": "ko-KR-InJoonNeural",
    "female": "ko-KR-SunHiNeural",
    "female2": "ko-KR-HyunsuNeural",
}

F = r"C\:/Windows/Fonts"  # ffmpeg escape용 폰트 디렉토리


def tts(text: str, out_mp3: str, voice: str = "female", rate: str = "+8%", pitch: str = "+2Hz") -> str:
    """edge-tts 한국어 — 문장별 속도/피치 변조 + 자연 쉼 (mp3 세그먼트 concat)
    기계적 균일 톤 제거용.
    """
    import edge_tts
    import asyncio
    import random as _r
    v = VOICES.get(voice, VOICES["female"])

    sentences = [s.strip() for s in text.replace("!", "!.").replace("?", "?.").split(".") if s.strip()]
    if not sentences:
        sentences = [text]

    async def _gen_one(s, r, p, path):
        c = edge_tts.Communicate(s, v, rate=r, pitch=p)
        await c.save(path)

    rng = _r.Random(hash(text) & 0xFFFF)
    tmp_dir = Path(out_mp3).parent / "tts_parts"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    async def _run():
        segs = []
        for i, s in enumerate(sentences[:8]):  # 최대 8문장
            r = rng.choice(["+4%", "+7%", "+9%", "+11%"])
            p = rng.choice(["+0Hz", "+2Hz", "+3Hz", "-1Hz"])
            seg = tmp_dir / f"part_{i}.mp3"
            await _gen_one(s, r, p, str(seg))
            segs.append(seg)
        return segs

    segs = asyncio.run(_run())

    if len(segs) == 1:
        import shutil
        shutil.copy(str(segs[0]), out_mp3)
    else:
        # 문장 사이 0.18초 정적 삽입 (자연스러운 호흡) + 음량 정규화
        # 실제 바이럴 숏츠 학습: 문장 간 호흡이 있어야 자연스러움
        list_file = tmp_dir / "list.txt"
        list_file.write_text("".join(f"file '{s}'\n" for s in segs), encoding="utf-8")
        subprocess.run(
            [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
             "-af", "silenceremove=stop_periods=-1:stop_duration=0.05:stop_threshold=-45dB,"
             "apad=pad_dur=0.18,"
             "loudnorm=I=-16:TP=-1.5:LRA=11,"
             "aformat=sample_rates=44100",
             "-c:a", "libmp3lame", "-b:a", "128k", out_mp3],
            capture_output=True,
        )
    return out_mp3


def probe_duration(f: str) -> float:
    ffprobe = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
    r = subprocess.run(
        [ffprobe, "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", f],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip())


def make_bgm(out_mp3: str, dur: float, bpm: int = 90) -> str:
    """로컬 합성 미니멀 로파이 BGM — 저작권/외부의존성 0
    느린 4분음표 파드 + 약한 킥. 나레이션 뒤 -24dB로 깔림."""
    import math
    # 진폭 패턴을 sine 합성으로 — aevalsrc
    beat = bpm / 60.0
    n_beats = int(dur * beat) + 1
    # 부드러운 코드 진행 (Am-F-C-G 느낌의 주파수)
    freqs = [220.0, 174.61, 261.63, 196.0]
    # 4비트마다 코드 변경, 각 비트 사인파 + 감쇠
    expr = []
    for i in range(min(n_beats, 200)):
        f = freqs[(i // 4) % 4]
        t0 = i / beat
        expr.append(f"0.22*sin(2*PI*{f}*t)*exp(-3*(t-{t0:.2f}))*if(between(t\,{t0:.2f}\,{t0 + 1.8/beat:.2f})\,1\,0)")
    ae = "+".join(expr[:120]) if expr else "0"
    subprocess.run(
        [FFMPEG, "-y", "-f", "lavfi", "-i", f"aevalsrc={ae}:s=44100:d={dur + 1:.1f}",
         "-af", "lowpass=f=1200,aformat=channel_layouts=stereo,volume=0.5",
         "-c:a", "libmp3lame", "-b:a", "96k", out_mp3],
        capture_output=True,
    )
    return out_mp3


def sanitize_caption(s: str) -> str:
    s = re.sub(r"[\\'\":;*#`~\[\]<>%]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def esc(s: str) -> str:
    """ffmpeg drawtext escape"""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")


def build_short(title, script_lines, image_paths, out_path, voice="female", bgm_path=None):
    """
    title: 영상 제목
    script_lines: 나레이션 문장 리스트
    image_paths: 게임 스크린샷 경로
    out_path: 출력 mp4
    """
    tmp = Path(out_path).parent / "tmp_shorts"
    tmp.mkdir(parents=True, exist_ok=True)

    # 1. TTS
    print("[1/4] TTS 생성...")
    full_mp3 = str(tmp / "narration.mp3")
    tts(" ".join(script_lines), full_mp3, voice=voice, rate="+6%", pitch="+1Hz")
    dur = probe_duration(full_mp3)
    print(f"    나레이션 {dur:.1f}초")

    # 1.5 BGM 생성 + 오디오 믹싱 (나레이션 우선, BGM -24dB) — inputs 구성 전에 실행
    if bgm_path is None:  # 외부 BGM 없으면 로컬 합성
        bgm_mp3 = str(tmp / "bgm.mp3")
        try:
            make_bgm(bgm_mp3, dur)
            bgm_path = bgm_mp3
        except Exception as e:
            print(f"    BGM 합성 스킵: {str(e)[:60]}")
    if bgm_path and os.path.exists(bgm_path):
        mixed_mp3 = str(tmp / "mixed.mp3")
        try:
            r_mix = subprocess.run(
                [FFMPEG, "-y", "-i", full_mp3, "-stream_loop", "-1", "-i", bgm_path,
                 "-filter_complex",
                 f"[1:a]volume=0.06,atrim=0:{dur + 0.5:.2f}[b];"
                 f"[0:a][b]amix=inputs=2:duration=first:dropout_transition=3[aout]",
                 "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "44100", mixed_mp3],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if r_mix.returncode == 0:
                full_mp3 = mixed_mp3
                print("    BGM 믹싱 완료")
            else:
                print(f"    BGM 믹싱 실패 — 나레이션만: {r_mix.stderr[-150:]}")
        except Exception as e:
            print(f"    BGM 스킵: {str(e)[:60]}")

    # 2. 이미지 시퀀스 계획
    n_seg = min(len(script_lines), max(len(image_paths), 1))
    seg_dur = dur / n_seg
    print(f"[2/4] {n_seg}개 세그먼트 x {seg_dur:.1f}초")

    # 3. ffmpeg 필터그래프 구성
    print("[3/4] 렌더링...")
    inputs = []
    for i in range(n_seg):
        img = image_paths[i % len(image_paths)]
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{seg_dur + 0.2:.2f}", "-i", str(img)]
    inputs += ["-i", full_mp3]

    # 세그먼트별 스케일+줌 (9:16 크롭) → concat
    parts = []
    for i in range(n_seg):
        zoom_dirs = [
            "z='min(zoom+0.0012,1.2)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
            "z='min(zoom+0.0012,1.2)':x='(iw-iw/zoom)*on/100':y='ih/2-(ih/zoom/2)'",
            "z='min(zoom+0.0012,1.2)':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*on/100'",
            "z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
        ]
        kb = zoom_dirs[i % 4]
        frames = int(seg_dur * 30) + 30  # 30fps 기준 총 프레임
        # 이미지 튀어나감 방지: 2배 업스케일 → 중앙 크롭 → 줌/팬 (줌 아웃 없음, 최소 1.0)
        # x/y를 클램프로 프레임 내 고정 — 바깥 참조 금지
        parts.append(
            f"[{i}:v]scale=2160:3840:force_original_aspect_ratio=increase,"
            f"crop=2160:3840,"
            f"zoompan=z='max(1.0\\,min(zoom+0.0008\\,1.10))':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps=30,"
            f"setsar=1[v{i}]"
        )
    xfade_parts = []
    prev = "v0"
    for i in range(1, n_seg):
        out_v = f"x{i}"
        offset = seg_dur * i - 0.15 * i
        xfade_parts.append(f"[{prev}][v{i}]xfade=transition=fade:duration=0.3:offset={max(offset - 0.3, 0):.2f}[{out_v}]")
        prev = out_v

    # 4. 자막 — ASS 자막 파일 방식 (08-24: drawtext 체인이 ffmpeg9 빌드에서 파싱 깨짐 → 표준 방식 전환)
    #    자동 줄바꿈(14자/줄, 화면폭 960px 내) + fad 200ms + 하단 중앙 정렬
    def _ass_time(x):
        h = int(x // 3600); m = int((x % 3600) // 60); sec = x % 60
        return f"{h}:{m:02d}:{sec:05.2f}"

    ass_path = tmp / "subs.ass"
    ass_lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Cap,Malgun Gothic,62,&H00FFFFFF,&H00000000,&H96000000,-1,5,2,2,60,60,430,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Text",
    ]
    t = 0.0
    for i, line in enumerate(script_lines[:n_seg]):
        cap = sanitize_caption(line)
        if not cap:
            continue
        # 14자씩 줄바꿈 (62px 폰트 × 14자 ≈ 870px < 960px 안전폭)
        cpl = 14
        chunks = [cap[j:j + cpl] for j in range(0, len(cap), cpl)]
        text = "\\N".join(chunks[:3])  # 최대 3줄
        start_t = t + 0.05
        end_t = t + seg_dur - 0.05
        if end_t <= start_t:
            continue
        ass_lines.append(
            f"Dialogue: 0,{_ass_time(start_t)},{_ass_time(end_t)},Cap,{{\\fad(200,200)}}{text}"
        )
        t += seg_dur

    ass_path.write_text("\n".join(ass_lines) + "\n", encoding="utf-8-sig")
    caption_sub = f"subtitles='{ass_path.as_posix()}'"

    # 최종 필터체인
    chain = ";".join(parts + xfade_parts)
    last_v = prev if xfade_parts else "v0"
    fc = f"{chain};[{last_v}]{caption_sub}[vout]"

    cmd = [FFMPEG, "-y"] + inputs
    n_audio = n_seg  # 오디오 인덱스 (이미지 다음)
    # 08-21 정리: BGM은 이미 사이드체인으로 mixed_mp3에 합쳐짐 → 오디오 map 1개만
    cmd += [
        "-filter_complex", fc,
        "-map", "[vout]", "-map", f"{n_audio}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-shortest",
        out_path,
    ]

    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("FFMPEG 에러:", r.stderr[-1500:])
        raise RuntimeError("ffmpeg 실패")
    print(f"[4/4] 완료: {out_path}")
    return out_path


if __name__ == "__main__":
    # 테스트: 게임 스크린샷 2장으로 15초 숏츠
    import sys

    test_dir = BASE / "data" / "test_shorts"
    test_dir.mkdir(parents=True, exist_ok=True)
    # 테스트 이미지 생성 (실제로는 게임 스크린샷)
    subprocess.run(
        [FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=0x1a1a2e:s=1080x1920:d=1",
         str(test_dir / "test_img1.png")], capture_output=True
    )
    subprocess.run(
        [FFMPEG, "-y", "-f", "lavfi", "-i", "color=c=0x16213e:s=1080x1920:d=1",
         str(test_dir / "test_img2.png")], capture_output=True
    )
    out = build_short(
        title="테스트",
        script_lines=["요즘 게임 진짜 잘 나온다.", "이 게임 안 해보면 후회한다."],
        image_paths=[str(test_dir / "test_img1.png"), str(test_dir / "test_img2.png")],
        out_path=str(test_dir / "test_short.mp4"),
    )
    d = probe_duration(out)
    print(f"테스트 완료: {out} ({d:.1f}초)")
