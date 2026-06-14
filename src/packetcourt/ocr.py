from __future__ import annotations

from pathlib import Path

from PIL import Image

from .vlm import extract_with_vlm, is_enabled


def extract_text(image_path: str | None, side: str = "back", vlm_extractor=None) -> tuple[str, str]:
    if not image_path:
        return "", "No image supplied."
    if is_enabled() or vlm_extractor is not None:
        try:
            text = (vlm_extractor or extract_with_vlm)(image_path, side)
            if text:
                return text, "Read with OpenBMB MiniCPM-V-4.6 on ZeroGPU. Verify extracted evidence against the packet."
        except Exception as exc:
            vlm_error = f"MiniCPM-V extraction failed ({type(exc).__name__}); "
        else:
            vlm_error = "MiniCPM-V returned no visible label text; "
    else:
        vlm_error = ""
    try:
        import pytesseract

        image = Image.open(Path(image_path)).convert("RGB")
        text = pytesseract.image_to_string(image, config="--psm 6").strip()
        if text:
            return text, f"{vlm_error}read with local Tesseract fallback. Verify against the packet."
        return "", "OCR found no readable text. Use a closer photo or paste the label text."
    except Exception as exc:
        return "", f"{vlm_error}OCR unavailable: {exc}. Paste the label text to continue."
