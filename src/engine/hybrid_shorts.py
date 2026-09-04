# -*- coding: utf-8 -*-
"""하이브리드 숏츠 파이프라인 — WAN AI 클립 × FFmpeg 후처리
흐름:
  1. WAN 로컬(wan_fast)로 제품 AI 클립 생성 (2초 x N개 — 씬 다양화)
  2. AI 대본(shorts_script) 생성
  3. TTS(문장별 변주) + BGM
  4. FFmpeg: 클립 연결 + 나레이션 mux + 자막 → 완성 숏츠
"""
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

FFMPEG = r"C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe")
OUT_DIR = BASE / "data" / "shorts_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def probe_dur(path):
    r = subprocess.run([FFPROBE, "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())


def make_hybrid_short(
    product_name: str,
    script_lines: list,
    scene_prompts: list = None,
    out_path: str = None,
    clips_per_scene: int = 1,
    wan_steps: int = 8,
) -> str:
    """AI 클립 기반 숏츠 — 각 문장에 WAN 클립 매칭"""
    from src.engine.wan_fast import fast_generate
    from src.engine.shorts_maker import tts, sanitize_caption, esc, make_bgm, F as FONT_DIR
    from src.engine.product_images import collect_images
    from src.engine.product_research import detect_category

    category = detect_category(product_name)
    n = len(script_lines)

    # 1. 씬 프롬프트 구성 (기본 템플릿 + 문장 수만큼)
    if not scene_prompts:
        templates = {
            "fashion": ["person wearing sneakers walking toward camera, low angle 3/4 view, feet fill the frame, natural daylight, real-life street",
                        "extreme close-up on laces being tied by hands, top-down view, shallow depth of field",
                        "person's feet in sneakers stepping confidently, tracking shot at ground level, cinematic motion"],
            "game": ["colorful game characters celebrating with particle effects, vibrant fantasy world",
                     "epic battle scene with magic effects, dynamic camera",
                     "cute characters dancing together in colorful garden"],
            "product": ["product rotating on clean pedestal, dramatic studio lighting",
                        "product close-up with floating particles, premium commercial",
                        "product in lifestyle scene, warm lighting"],
            "platform": ["modern UI elements floating in 3D space, clean tech aesthetic, blue glow",
                         "data streams flowing elegantly, futuristic interface",
                         "abstract geometric shapes morphing, minimal design"],
            "place": ["cozy interior ambience, warm lighting, camera panning",
                      "sunlight streaming through windows, inviting atmosphere",
                      "people enjoying the space, candid moments"],
        }
        base = templates.get(category, templates["product"])
        scene_prompts = [f"{product_name} {base[i % len(base)]}, cinematic, high quality" for i in range(n)]

    # 2. WAN 클립 생성 (문장 수만큼 — 캐시된 파이프라인으로 순차 생성)
    tmp = OUT_DIR / "tmp_hybrid"
    tmp.mkdir(exist_ok=True)
    clips = []
    t0 = time.time()
    for i in range(min(n, 4)):  # 시간 절약: 최대 4클립 (나머지는 반복 사용)
        cp = str(tmp / f"clip_{i}.mp4")
        fast_generate(scene_prompts[i], out_path=cp, steps=wan_steps)
        clips.append(cp)
        print(f"[하이브리드] 클립 {i+1}/4 완료 ({time.time()-t0:.0f}초 경과)")

    # 3. TTS (문장별 변주)
    voice_mp3 = str(tmp / "voice.mp3")
    tts(" ".join(script_lines), voice_mp3, voice="female")
    adur = probe_dur(voice_mp3)

    # 4. BGM 믹싱
    try:
        bgm_mp3 = str(tmp / "bgm.mp3")
        make_bgm(bgm_mp3, adur)
        mixed = str(tmp / "mixed.mp3")
        r = subprocess.run(
            [FFMPEG, "-y", "-i", voice_mp3, "-stream_loop", "-1", "-i", bgm_mp3,
             "-filter_complex",
             f"[1:a]volume=0.05,atrim=0:{adur:.2f}[b];[0:a][b]amix=inputs=2:duration=first[aout]",
             "-map", "[aout]", "-c:a", "libmp3lame", "-b:a", "128k", mixed],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode == 0:
            voice_mp3 = mixed
    except Exception:
        pass

    # 5. 클립 연결 + 세로 포맷 + 자막
    seg_dur = adur / n
    inputs = []
    for i in range(n):
        c = clips[i % len(clips)]
        inputs += ["-stream_loop", "-1", "-t", f"{seg_dur + 0.3:.2f}", "-i", c]
    inputs += ["-i", voice_mp3]

    filters = []
    for i in range(n):
        filters.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop=1080:1920,"
            f"unsharp=5:5:0.8:5:5:0.0,"  # 업스케일 후 선명도 보정
            f"setsar=1,fps=30[v{i}]"
        )
    # concat
    concat_in = "".join(f"[v{i}]" for i in range(n))
    concat = f"{concat_in}concat=n={n}:v=1:a=0[vc]"
    # 자막
    # 자막 — 실제 바이럴 숏츠 스타일 (08-20 학습반영)
    # · 상단 1/3 위치 (h*0.28) — 실제 꿀템 숏츠들은 상단 텍스트가 많음
    # · 크기 확대 72px + 2줄 분할 + 반투명 박스 배경 + 강조색(노랑) 지원
    caps = []
    for i, line in enumerate(script_lines):
        full = sanitize_caption(line)
        # 18자씩 2줄 분할 (실제 숏츠는 짧은 2줄)
        chunks = [full[j:j+18] for j in range(0, len(full), 18)][:2]
        start, end = i * seg_dur, (i + 1) * seg_dur
        for k, chunk in enumerate(chunks):
            y_base = int(1920 * 0.24) + k * 110
            caps.append(
                f"drawtext=fontfile='{FONT_DIR}/malgunbd.ttf':text='{esc(chunk)}':"
                f"fontcolor=white:fontsize=76:borderw=6:bordercolor=black@"
                f"0.9:box=1:boxcolor=black@0.45:boxborderw=18:"
                f"x=(w-text_w)/2:y={y_base}:enable='between(t\\,{start:.2f}\\,{end:.2f})'"
            )
    fc = ";".join(filters + [concat] + [f"[vc]{','.join(caps)}[vout]"])

    if not out_path:
        out_path = str(OUT_DIR / f"hybrid_{product_name[:10]}_{int(time.time())}.mp4")
    cmd = [FFMPEG, "-y"] + inputs + [
        "-filter_complex", fc,
        "-map", "[vout]", "-map", f"{n}:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "22",
        "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-shortest", out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"렌더 실패: {r.stderr[-400:]}")
    # ── 품질 후처리 (v5-enhance, 2026-09-02) — 노이즈제거+컬러그레이딩+샤프닝+비네트 ──
    # 검증: 3/10 → 7/10 (E3 비전검수). crf 22→16으로 인코딩 품질도 상향.
    try:
        enh = out_path.replace(".mp4", "_enh.mp4")
        vf = ("hqdn3d=1.5:1.5:6:6,"
              "eq=contrast=1.08:brightness=0.015:saturation=1.12,"
              "unsharp=5:5:0.9:5:5:0.0,"
              "vignette=PI/7")
        rc = subprocess.run(
            [FFMPEG, "-y", "-i", out_path, "-vf", vf,
             "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
             "-c:a", "copy", enh],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
        if rc.returncode == 0:
            import os as _os
            _os.replace(enh, out_path)  # 원본 교체 — 이후 파이프라인은 향상본 사용
            print("[품질] 후처리 적용 완료 (hqdn3d+grade+sharpen+vignette, crf16)")
        else:
            print(f"[품질] 후처리 스킵 (ffmpeg 오류, 원본 유지): {rc.stderr[-120:]}")
    except Exception as e:
        print(f"[품질] 후처리 스킵: {e}")
    d = probe_dur(out_path)
    print(f"[하이브리드] 완성: {out_path} ({d:.1f}초, 총 {time.time()-t0:.0f}초 소요)")
    return out_path


def generate_full_short(product_name: str, description: str = "", category: str = None) -> str:
    """제품명 하나로 완성 숏츠까지 — 대본 자동 생성 포함"""
    from src.engine.product_research import research
    from src.engine.shorts_script import generate_shorts_script
    from src.engine.content_generator import load_personas
    import random

    r = research(product_name, category)
    personas = load_personas()
    p = random.choice(personas)
    info = {"name": product_name, "description": description, "research": r}
    s = generate_shorts_script(info, p)
    if not s["lines"]:
        raise RuntimeError("대본 생성 실패")
    print("[하이브리드] 대본:")
    for i, l in enumerate(s["lines"], 1):
        print(f"  {i}. {l}")
    return make_hybrid_short(product_name, s["lines"])


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "트릭컬 리바이브"
    out = generate_full_short(name)
    print("최종:", out)
