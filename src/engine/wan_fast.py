# -*- coding: utf-8 -*-
"""WAN 2.1 고속 파이프라인 v2 — RTX 4060 8GB 5분 목표

전략: prompt_embeds 사전계산으로 text_encoder를 아예 파이프라인에서 분리
1. 임베딩: CPU float32로 1회 계산 → CUDA로 전달 (파이프라인 밖)
2. GPU에는 transformer(2.7GB)+VAE만 — 스와핑 0
3. CausVid LoRA로 4스텝
"""
import time
from pathlib import Path

import torch

BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "data" / "shorts_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
CAUSVID_LORA = "AlekseyCalvin/Wan1.3B_CausVid_LoRA_MisubiDiffusers_Conversion"
CAUSVID_FILE = "Wan_1.3B_CausVid_LoRA_misubi_DiffusersConversion.safetensors"

_pipe = None
_embedder = None


def _load_embedder():
    """UMT5 텍스트 인코더 — CPU float32 단독 로드 (1회)"""
    global _embedder
    if _embedder is not None:
        return _embedder
    from transformers import AutoTokenizer, UMT5EncoderModel
    tok = AutoTokenizer.from_pretrained(MODEL_ID, subfolder="tokenizer")
    enc = UMT5EncoderModel.from_pretrained(MODEL_ID, subfolder="text_encoder", torch_dtype=torch.float32)
    enc.eval()
    _embedder = (tok, enc)
    return _embedder


@torch.no_grad()
def encode_prompt(prompt: str, negative: str = "") -> dict:
    """프롬프트 → 임베딩 (CPU에서 계산, 결과만 CUDA) — 캐시로 재사용 시 0초"""
    global _emb_cache
    key = prompt + "||" + (negative or "")
    if _emb_cache and _emb_cache[0] == key:
        return _emb_cache[1]
    tok, enc = _load_embedder()
    ids = tok([prompt], return_tensors="pt", max_length=512, padding="max_length", truncation=True)
    pos = enc(ids.input_ids).last_hidden_state.to("cuda", torch.float32)
    ids2 = tok([negative or "low quality, blurry, text, watermark"], return_tensors="pt", max_length=512, padding="max_length", truncation=True)
    neg = enc(ids2.input_ids).last_hidden_state.to("cuda", torch.float32)
    _emb_cache = (key, {"pos": pos, "neg": neg})
    return _emb_cache[1]


_emb_cache = None


def _get_pipe():
    global _pipe
    if _pipe is not None:
        return _pipe
    from diffusers import AutoencoderKLWan, WanPipeline

    vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanPipeline.from_pretrained(
        MODEL_ID, vae=vae, torch_dtype=torch.bfloat16,
        text_encoder=None, tokenizer=None,  # ★ 아예 제외 — 임베딩은 직접 전달
    )
    pipe.transformer.to("cuda", torch.bfloat16)
    # VAE는 bf16 GPU — 디코딩 3배 가속 (float32 대비 품질 차이 미미)
    pipe.vae.to("cuda", torch.bfloat16)

    try:
        pipe.load_lora_weights(CAUSVID_LORA, weight_name=CAUSVID_FILE, adapter_name="causvid")
        pipe.set_adapters(["causvid"], adapter_weights=[1.0])
        print("[WAN-FAST] CausVid LoRA 적용 (4스텝)")
    except Exception as e:
        print(f"[WAN-FAST] LoRA 스킵 ({str(e)[:60]})")
    try:
        pipe.enable_vae_tiling()
        pipe.enable_vae_slicing()
    except Exception:
        pass
    _pipe = pipe
    return pipe


@torch.no_grad()
def fast_generate(
    prompt: str,
    out_path: str = None,
    num_frames: int = 33,
    steps: int = 4,
    height: int = 480,
    width: int = 832,
    seed: int = 42,
) -> str:
    pipe = _get_pipe()
    out_path = out_path or str(OUT_DIR / f"wanfast_{int(time.time())}.mp4")

    t0 = time.time()
    emb = encode_prompt(prompt)
    print(f"[WAN-FAST] 임베딩 {time.time()-t0:.0f}초 — 생성 {num_frames}f x {steps}steps")

    frames = pipe(
        prompt_embeds=emb["pos"],
        negative_prompt_embeds=emb["neg"],
        guidance_scale=1.0 if steps <= 4 else 5.0,
        num_frames=num_frames,
        height=height, width=width,
        num_inference_steps=steps,
        generator=torch.Generator(device="cpu").manual_seed(seed),
    ).frames[0]

    from diffusers.utils import export_to_video
    export_to_video(frames, out_path, fps=16)
    print(f"[WAN-FAST] 완성 {time.time()-t0:.0f}초: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys
    prompt = sys.argv[1] if len(sys.argv) > 1 else "A premium hoodie product rotating in a bright modern studio, cinematic product commercial"
    out = fast_generate(prompt, str(OUT_DIR / "wan_fast_test.mp4"))
    print("최종:", out)
