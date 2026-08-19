# -*- coding: utf-8 -*-
"""WAN 2.1 고속 파이프라인 (최종) — RTX 4060 8GB
측정: 임베딩 포함 8스텝 289초 (~5분) / 파이프라인 캐시 시 ~250초

작동 구조 (v3 확정):
- 텍스트 인코더: group offloading (leaf_level) — 필요시에만 잠깐 GPU, 평소 CPU
- transformer: GPU bf16 상주 (2.7GB)
- VAE: GPU bf16 + tiling/slicing — 디코딩 고속
- 이 구조가 아니면(인코더 상주 or 임베딩 직접전달) 8GB 초과 스와핑 or 단색 실패
"""
import time
from pathlib import Path

import torch

BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "data" / "shorts_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"

_pipe = None


def _get_pipe():
    global _pipe
    if _pipe is not None:
        return _pipe
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.hooks import apply_group_offloading

    vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanPipeline.from_pretrained(MODEL_ID, vae=vae, torch_dtype=torch.bfloat16)

    # ★ 핵심: 텍스트 인코더 리프단위 오프로드 (직접 임베딩 전달 방식은 단색 버그 발생 — 폐기)
    apply_group_offloading(
        pipe.text_encoder,
        onload_device=torch.device("cuda"),
        offload_device=torch.device("cpu"),
        offload_type="leaf_level",
        use_stream=True,
    )
    pipe.transformer.to("cuda", torch.bfloat16)
    pipe.vae.to("cuda", torch.bfloat16)
    try:
        pipe.enable_vae_tiling()
    except Exception:
        pass
    _pipe = pipe
    return pipe


@torch.no_grad()
def fast_generate(
    prompt: str,
    out_path: str = None,
    num_frames: int = 33,     # ~2초
    steps: int = 8,           # 품질/속도 균형 (4=뭉개짐, 8=양호, 20=고품질)
    height: int = 480,
    width: int = 832,
    seed: int = 42,
) -> str:
    pipe = _get_pipe()
    out_path = out_path or str(OUT_DIR / f"wan_{int(time.time())}.mp4")

    t0 = time.time()
    frames = pipe(
        prompt=prompt,
        negative_prompt="low quality, blurry, text, watermark, distorted",
        guidance_scale=5.0,
        num_frames=num_frames,
        height=height, width=width,
        num_inference_steps=steps,
        generator=torch.Generator(device="cpu").manual_seed(seed),
    ).frames[0]

    from diffusers.utils import export_to_video
    export_to_video(frames, out_path, fps=16)
    print(f"[WAN] 완성 {time.time()-t0:.0f}초: {out_path}")
    return out_path


def generate_viral_clip(product_name: str, scene_hint: str = None, out_path: str = None) -> str:
    """바이럴용 제품 클립 — 카테고리별 프롬프트 자동 구성"""
    scenes = {
        "fashion": "worn by an invisible mannequin, fabric flowing naturally, rotating slowly, bright studio lighting",
        "game": "colorful game characters celebrating with particle effects, dynamic camera, vibrant fantasy world",
        "product": "floating product rotating on clean pedestal, dramatic lighting, premium commercial style",
        "platform": "modern interface elements floating in 3D space, clean tech aesthetic, blue glow",
        "place": "cozy interior ambience with warm lighting, camera slowly panning, inviting atmosphere",
    }
    from src.engine.product_research import detect_category
    cat = detect_category(product_name)
    scene = scene_hint or scenes.get(cat, scenes["product"])
    prompt = f"{product_name} {scene}, cinematic, high detail, 4k quality"
    return fast_generate(prompt, out_path=out_path)


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else "A premium gray hoodie"
    out = fast_generate(p, str(OUT_DIR / "wan_final_test.mp4"))
    print("최종:", out)
