from __future__ import annotations

from pathlib import Path

from PIL import Image


def extract_text(image_path: str | None) -> tuple[str, str]:
    if not image_path:
        return "", "No image supplied."
    try:
        import pytesseract

        image = Image.open(Path(image_path)).convert("RGB")
        text = pytesseract.image_to_string(image, config="--psm 6").strip()
        if text:
            return text, "OCR completed with Tesseract. Verify against the packet."
        return "", "OCR found no readable text. Use a closer photo or paste the label text."
    except Exception as exc:
        return "", f"OCR unavailable: {exc}. Paste the label text to continue."

