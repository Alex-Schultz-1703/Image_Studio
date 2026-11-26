import ctypes
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

def main():
    # Сообщаем Windows уникальный AppID, чтобы значок на панели задач был кастомным
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("studio.imagestudio.app.1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)

    # Установка иконки на всё приложение
    icon_path = Path(__file__).resolve().parent / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # ... далее твой существующий код запуска сплеша и MainWindow

class StudioSplashScreen(QSplashScreen):
    def __init__(self):
        self.progress_val = 0
        self.status_msg = "Загрузка модулей..."
        pix = self._render_pixmap()
        super().__init__(pix, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)

    def set_progress(self, val: int, msg: str):
        self.progress_val = val
        self.status_msg = msg
        self.setPixmap(self._render_pixmap())
        QApplication.processEvents()

    def _render_pixmap(self) -> QPixmap:
        pix = QPixmap(420, 260)
        pix.fill(Qt.transparent)

        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        # OLED Black
        painter.setBrush(QColor(10, 10, 10))
        painter.setPen(QColor(34, 34, 34))
        painter.drawRoundedRect(0, 0, 419, 259, 20, 20)

        # Заголовок
        font_title = QFont("Segoe UI", 20, QFont.Bold)
        painter.setFont(font_title)
        painter.setPen(QColor(250, 250, 250))
        painter.drawText(0, 80, 420, 36, Qt.AlignCenter, "IMAGE STUDIO")

        # Статус
        font_sub = QFont("Segoe UI", 11)
        painter.setFont(font_sub)
        painter.setPen(QColor(140, 140, 140))
        painter.drawText(0, 126, 420, 24, Qt.AlignCenter, self.status_msg)

        # Дорожка
        bar_x = 55
        bar_y = 175
        bar_w = 310
        bar_h = 6

        painter.setBrush(QColor(24, 24, 24))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 3, 3)

        # Заполнение
        fill_w = max(6, int(bar_w * (self.progress_val / 100.0)))
        painter.setBrush(QColor(220, 220, 220))
        painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 3, 3)

        painter.end()
        return pix


def main():
    app = QApplication(sys.argv)

    splash = StudioSplashScreen()
    splash.show()
    app.processEvents()

    # Постепенный плавный таймер загрузки
    splash.set_progress(10, "Подготовка окружения...")
    from core.config import load_app_theme
    _ = load_app_theme()

    splash.set_progress(35, "Загрузка интерфейса...")
    from gui.main_window import MainWindow

    splash.set_progress(70, "Проверка каталогов...")
    window = MainWindow()

    # Таймер постепенного доведения до 100%
    curr_prog = 70
    messages = [
        (80, "Инициализация компонентов..."),
        (90, "Подготовка рабочей области..."),
        (100, "Готово к работе"),
    ]

    def step_advance(idx=0):
        if idx < len(messages):
            p, msg = messages[idx]
            splash.set_progress(p, msg)
            QTimer.singleShot(60, lambda: step_advance(idx + 1))
        else:
            splash.finish(window)
            window.show()

    QTimer.singleShot(50, lambda: step_advance(0))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
