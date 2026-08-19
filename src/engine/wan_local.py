# -*- coding: utf-8 -*-
"""WAN 2.2 로컬 비디오 생성 — RTX 4060 8GB용 (T2V-5B / I2V-5B)
diffusers WanPipeline 기반. 첫 실행 시 모델 다운로드 (~20GB).
"""
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

# 한국에서 HF 직접이 느리면 미러
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

MODEL_T2V = "Wan-AI/Wan2.2-T2V-A14B-Diffusers"  # 고성능 (14B MoE, 8GB는 offload로 가능하나 느림)
MODEL_T2V_FAST = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"  # 경량 — 8GB GPU 확실 지원
MODEL_I2V = "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"


def generate(prompt: str, out_path: str, image_path: str = None, model_id: str = None,
             num_frames: int = 81, height: int = 480, width: int = 832, steps: int = 20):
    """로컬 WAN 비디오 생성. image_path 주면 I2V."""
    import torch
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.utils import export_to_video

    model = model_id or (MODEL_I2V if image_path else MODEL_T2V_FAST)
    print(f"[WAN] 로드: {model}")
    vae = AutoencoderKLWan.from_pretrained(model, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanPipeline.from_pretrained(model, vae=vae, torch_dtype=torch.bfloat16)
    pipe.to("cuda")

    kw = dict(
        prompt=prompt,
        negative_prompt="色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走",
        guidance_scale=5.0,
        num_frames=num_frames,
        height=height,
        width=width,
        num_inference_steps=steps,
        generator=torch.Generator(device="cuda").manual_seed(42),
    )
    if image_path:
        from diffusers.utils import load_image
        kw["image"] = load_image(image_path)

    print("[WAN] 생성 시작...")
    out = pipe(**kw).frames[0]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    export_to_video(out, out_path, fps=16)
    print(f"[WAN] 완성: {out_path}")
    return out_path


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "A premium hoodie product slowly rotating in a bright modern studio, soft shadows, cinematic product commercial, high detail"
    out = str(BASE / "data/shorts_out/wan_test_01.mp4")
    generate(prompt, out, num_frames=49, steps=15)  # 빠른 테스트
    print("완성:", out)
