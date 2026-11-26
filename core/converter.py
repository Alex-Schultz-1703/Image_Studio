from pathlib import Path
from PIL import Image, ImageOps
from core.config import DEFAULT_WEBP_QUALITY, DEFAULT_WEBP_EFFORT, generate_unique_path


class ImageConverter:
    def __init__(self, quality: int = DEFAULT_WEBP_QUALITY, effort: int = DEFAULT_WEBP_EFFORT, lossless: bool = False):
        self.quality = quality
        self.effort = effort
        self.lossless = lossless

    def convert_to_webp(self, src: Path, out_dir: Path, progress_callback=None) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        dst = generate_unique_path(out_dir / f"{src.stem}.webp")

        if progress_callback:
            progress_callback(20, f"Чтение файла: {src.name}")

        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode in ("P", "LA"):
                im = im.convert("RGBA")
            elif im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")

            if progress_callback:
                progress_callback(70, f"Конвертация в WebP: {src.name}")

            im.save(
                dst,
                "WEBP",
                quality=self.quality,
                method=self.effort,
                lossless=self.lossless,
            )

        if progress_callback:
            progress_callback(100, f"Готово: {src.name}")

        return dst
