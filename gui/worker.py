from pathlib import Path
from PySide6.QtCore import QObject, Signal
from core.config import is_model_downloaded, save_history_entry
from core.converter import ImageConverter
from core.remover import BackgroundRemover


class ProcessingTask:
    def __init__(
        self,
        files,
        out_dir,
        mode,
        model_name,
        delete_src,
        add_suffix,
        quality,
        effort,
        lossless,
    ):
        self.files = [Path(f) for f in files]
        self.out_dir = Path(out_dir)
        self.mode = mode
        self.model_name = model_name
        self.delete_src = delete_src
        self.add_suffix = add_suffix
        self.quality = quality
        self.effort = effort
        self.lossless = lossless


class ProcessingWorker(QObject):
    file_progress = Signal(int, str)
    total_progress = Signal(int, int)
    log_message = Signal(str)
    item_finished = Signal(str, str)
    finished = Signal()

    def __init__(self, task: ProcessingTask):
        super().__init__()
        self.task = task
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.task.out_dir.mkdir(parents=True, exist_ok=True)
            converter = ImageConverter(
                quality=self.task.quality,
                effort=self.task.effort,
                lossless=self.task.lossless,
            )
            remover = None

            if self.task.mode in ("remove_bg", "both"):
                if not is_model_downloaded(self.task.model_name):
                    self.log_message.emit(f"Загрузка нейросети {self.task.model_name}...")
                
                try:
                    remover = BackgroundRemover(
                        model_name=self.task.model_name,
                        add_suffix=self.task.add_suffix,
                        quality=self.task.quality,
                        effort=self.task.effort,
                        lossless=self.task.lossless,
                    )
                except Exception as e:
                    self.log_message.emit(f"Ошибка загрузки нейросети: {e}")
                    self.finished.emit()
                    return

            total = len(self.task.files)
            success_files = []

            for idx, src in enumerate(self.task.files, 1):
                if self._is_cancelled:
                    self.log_message.emit("Процесс отменен.")
                    break

                self.total_progress.emit(idx, total)

                def on_step(sub_percent, msg):
                    self.file_progress.emit(sub_percent, msg)

                try:
                    dst = None
                    if self.task.mode == "convert_only":
                        dst = converter.convert_to_webp(src, self.task.out_dir, progress_callback=on_step)
                    elif self.task.mode == "remove_bg":
                        dst = remover.process(src, self.task.out_dir, is_raw_input=False, progress_callback=on_step)
                    elif self.task.mode == "both":
                        dst = remover.process(src, self.task.out_dir, is_raw_input=True, progress_callback=on_step)

                    success_files.append(src)
                    save_history_entry(src, dst, self.task.mode)
                    self.item_finished.emit(str(src), str(dst))
                except Exception as e:
                    self.log_message.emit(f"Ошибка {src.name}: {e}")

            if self.task.delete_src and not self._is_cancelled:
                for f in success_files:
                    try:
                        f.unlink()
                    except Exception:
                        pass
        except Exception as e:
            self.log_message.emit(f"Сбой выполнения: {e}")

        self.finished.emit()
