from __future__ import annotations

import traceback
from functools import lru_cache

import gradio as gr
import spaces
import torch
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL_ID = "openbmb/MiniCPM-V-4.6"

PROMPTS = {
    "front": (
        "Transcribe only visibly printed marketing claims from this food packet front. "
        "Preserve exact claims and do not explain or infer."
    ),
    "back": (
        "Transcribe only visibly printed food-label evidence. Focus on ingredients, nutrition values "
        "and basis, net weight, FSSAI license, dates, and after-opening instructions. For nutrition "
        "tables, preserve every visible row as 'nutrient name | unit | value', include the declared "
        "basis, and do not omit zero values. Do not summarize or infer."
    ),
}


@lru_cache(maxsize=1)
def load_model():
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = AutoModelForImageTextToText.from_pretrained(
        MODEL_ID,
        torch_dtype="auto",
        device_map="auto",
    )
    model.eval()
    return processor, model


@spaces.GPU(duration=180)
def extract_label(image_path: str | None, side: str) -> str:
    if image_path is None:
        return "No image supplied."
    try:
        processor, model = load_model()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": image_path},
                    {"type": "text", "text": PROMPTS[side]},
                ],
            }
        ]
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
            downsample_mode="4x",
            max_slice_nums=36,
        ).to(model.device)
        generated = model.generate(**inputs, downsample_mode="4x", max_new_tokens=512, do_sample=False)
        trimmed = [output[len(source) :] for source, output in zip(inputs.input_ids, generated)]
        return processor.batch_decode(trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0].strip()
    except Exception as exc:
        return f"PACKETCOURT_VISION_ERROR: {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=4)}"


demo = gr.Interface(
    fn=extract_label,
    inputs=[
        gr.Image(type="filepath", label="Packet label photo"),
        gr.Radio(["front", "back"], value="back", label="Packet side"),
    ],
    outputs=gr.Textbox(label="Visible label evidence"),
    title="PacketCourt Vision",
    description="OpenBMB MiniCPM-V-4.6 evidence transcription service for PacketCourt.",
    flagging_mode="never",
)

if __name__ == "__main__":
    demo.launch()
