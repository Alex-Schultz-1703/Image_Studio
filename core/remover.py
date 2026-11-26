import sys
from pathlib import Path
from PIL import Image, ImageOps
from core.config import (
    DEFAULT_WEBP_QUALITY,
    DEFAULT_WEBP_EFFORT,
    MODELS_DIR,
    generate_unique_path,
)


class BackgroundRemover:
    def __init__(
        self,
        model_name: str,
        add_suffix: bool = True,
        quality: int = DEFAULT_WEBP_QUALITY,
        effort: int = DEFAULT_WEBP_EFFORT,
        lossless: bool = False,
    ):
        self.model_name = model_name
        self.add_suffix = add_suffix
        self.quality = quality
        self.effort = effort
        self.lossless = lossless

        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            import rembg
            self.session = rembg.new_session(model_name)
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить модель {model_name}: {e}")

    def process(
        self,
        src: Path,
        out_dir: Path,
        is_raw_input: bool = False,
        progress_callback=None,
    ) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = f"_{self.model_name}" if self.add_suffix else ""
        dst = generate_unique_path(out_dir / f"{src.stem}{suffix}.webp")

        if progress_callback:
            progress_callback(15, f"Открытие: {src.name}")

        with Image.open(src) as im:
            if is_raw_input:
                im = ImageOps.exif_transpose(im)
            im_rgba = im.convert("RGBA")

            if progress_callback:
                progress_callback(40, f"Инференс ({self.model_name}): {src.name}")

            import rembg
            result = rembg.remove(im_rgba, session=self.session)

            if progress_callback:
                progress_callback(85, f"Сжатие WebP: {src.name}")

            result.save(
                dst,
                "WEBP",
                quality=self.quality,
                method=self.effort,
                lossless=self.lossless,
            )

        if progress_callback:
            progress_callback(100, f"Готово: {src.name}")

        return dst
