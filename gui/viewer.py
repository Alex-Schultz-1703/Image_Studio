import io
from pathlib import Path
from PIL import Image, ImageOps
from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QThread,
    QTimer,
    Qt,
    Property,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from core.config import THEMES, format_file_size

RESIZE_FILTERS = {
    "Lanczos3": Image.Resampling.LANCZOS,
    "Mitchell / Bicubic": Image.Resampling.BICUBIC,
    "Bilinear": Image.Resampling.BILINEAR,
    "Nearest": Image.Resampling.NEAREST,
}


def create_checker_brush(dark_mode: bool = True):
    size = 18
    pix = QPixmap(size, size)
    painter = QPainter(pix)
    if dark_mode:
        c1, c2 = QColor(38, 38, 42), QColor(24, 24, 28)
    else:
        c1, c2 = QColor(235, 235, 238), QColor(255, 255, 255)
    painter.fillRect(0, 0, size // 2, size // 2, c1)
    painter.fillRect(size // 2, 0, size // 2, size // 2, c2)
    painter.fillRect(0, size // 2, size // 2, size // 2, c2)
    painter.fillRect(size // 2, size // 2, size // 2, size // 2, c1)
    painter.end()
    return QBrush(pix)


def is_image_has_alpha(pil_im: Image.Image) -> bool:
    if pil_im.mode in ("RGBA", "LA") or (pil_im.mode == "P" and "transparency" in pil_im.info):
        try:
            alpha = pil_im.convert("RGBA").split()[-1]
            extrema = alpha.getextrema()
            return extrema[0] < 255
        except Exception:
            return True
    return False


class ModernComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_data = THEMES["dark"]
        self.is_opened = False

        view = self.view()
        view.window().setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        view.window().setAttribute(Qt.WA_TranslucentBackground)

    def showPopup(self):
        self.is_opened = True
        self.apply_theme(self.theme_data)
        super().showPopup()

    def hidePopup(self):
        self.is_opened = False
        self.apply_theme(self.theme_data)
        super().hidePopup()

    def apply_theme(self, theme_data):
        self.theme_data = theme_data
        t = theme_data

        # Единая обводка в цвет акцента (или белая) при открытии
        border_col = t["accent"] if self.is_opened else t["input_border"]
        bottom_rad = "0px" if self.is_opened else "8px"
        bottom_border = "none" if self.is_opened else f"1px solid {border_col}"

        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {t["input_bg"]};
                border: 1px solid {border_col};
                border-bottom: {bottom_border};
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom-left-radius: {bottom_rad};
                border-bottom-right-radius: {bottom_rad};
                padding: 6px 36px 6px 12px;
                color: {t["text"]};
                font-size: 13px;
                font-weight: 600;
            }}
            QComboBox:hover {{
                border-color: {t["accent"]};
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 28px;
                border: none;
                background: transparent;
            }}
            QComboBox::down-arrow {{
                image: none;
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {t["input_bg"]};
                border: 1px solid {border_col};
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                selection-background-color: {t["table_selected"]};
                selection-color: {t["text"]};
                color: {t["text"]};
                padding: 4px;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 12px;
                border-radius: 4px;
                color: {t["text"]};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {t["table_selected"]};
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(QColor(self.theme_data["subtext"]), 1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        rx = self.width() - 18
        ry = self.height() / 2 - 2
        painter.drawLine(int(rx - 4), int(ry), int(rx), int(ry + 4))
        painter.drawLine(int(rx), int(ry + 4), int(rx + 4), int(ry))


class SmoothToggle(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, theme_data=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 26)
        self.setCursor(Qt.PointingHandCursor)

        self._checked = checked
        self._thumb_position = 1.0 if checked else 0.0
        self.theme_data = theme_data or THEMES["dark"]

        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._anim.stop()
            self._anim.setStartValue(self._thumb_position)
            self._anim.setEndValue(1.0 if checked else 0.0)
            self._anim.start()
            self.toggled.emit(checked)

    def get_thumb_position(self) -> float:
        return self._thumb_position

    def set_thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update()

    thumb_position = Property(float, get_thumb_position, set_thumb_position)

    def set_theme(self, theme_data):
        self.theme_data = theme_data
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2.0

        off_col = QColor(self.theme_data["toggle_track_off"])
        on_col = QColor(self.theme_data.get("toggle_track_on", self.theme_data["accent"]))

        r = off_col.red() + (on_col.red() - off_col.red()) * self._thumb_position
        g = off_col.green() + (on_col.green() - off_col.green()) * self._thumb_position
        b = off_col.blue() + (on_col.blue() - off_col.blue()) * self._thumb_position
        track_color = QColor(int(r), int(g), int(b))

        painter.setBrush(track_color)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, radius, radius)

        thumb_diameter = h - 6
        x_min = 3.0
        x_max = w - thumb_diameter - 3.0
        thumb_x = x_min + (x_max - x_min) * self._thumb_position

        painter.setBrush(QColor(self.theme_data["toggle_thumb"]))
        painter.drawEllipse(QRectF(thumb_x, 3.0, thumb_diameter, thumb_diameter))


class CompressWorker(QObject):
    finished = Signal(bytes, int)

    def __init__(self, pil_image, resize_data, quality, effort, lossless):
        super().__init__()
        self.pil_image = pil_image
        self.resize_data = resize_data
        self.quality = quality
        self.effort = effort
        self.lossless = lossless

    def run(self):
        im = self.pil_image.copy()

        do_resize, w, h, resample_method = self.resize_data
        if do_resize and w > 0 and h > 0:
            try:
                im = im.resize((w, h), resample=resample_method)
            except Exception:
                pass

        buf = io.BytesIO()
        im.save(
            buf,
            format="WEBP",
            quality=self.quality,
            method=self.effort,
            lossless=self.lossless,
        )
        data = buf.getvalue()
        self.finished.emit(data, len(data))


class InteractiveCompareCanvas(QWidget):
    def __init__(self, before_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap_before = before_pixmap
        self.pixmap_after = before_pixmap
        self.split_pos = 0.5

        self.zoom = 1.0
        self.pan_offset = QPointF(0, 0)
        self.is_dragging_canvas = False
        self.is_dragging_handle = False
        self.last_mouse_pos = QPointF(0, 0)

        self.is_processing = False
        self.spinner_angle = 0
        self.bg_color = QColor(15, 17, 23)

        self.spinner_timer = QTimer(self)
        self.spinner_timer.timeout.connect(self._rotate_spinner)

        self.checker_brush = create_checker_brush(dark_mode=True)
        self.setMouseTracking(True)

    def set_canvas_bg(self, color_hex: str, dark_mode: bool = True):
        self.bg_color = QColor(color_hex)
        self.checker_brush = create_checker_brush(dark_mode=dark_mode)
        self.update()

    def set_processing(self, state: bool):
        self.is_processing = state
        if state:
            if not self.spinner_timer.isActive():
                self.spinner_timer.start(25)
        else:
            self.spinner_timer.stop()
        self.update()

    def _rotate_spinner(self):
        self.spinner_angle = (self.spinner_angle + 12) % 360
        self.update()

    def set_after_pixmap(self, pixmap: QPixmap):
        self.pixmap_after = pixmap
        self.set_processing(False)
        self.update()

    def reset_view(self):
        self.zoom = 1.0
        self.pan_offset = QPointF(0, 0)
        self.split_pos = 0.5
        self.update()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        self.zoom = max(0.2, min(8.0, self.zoom * factor))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            line_x = self._get_split_screen_x()
            if abs(event.position().x() - line_x) <= 24:
                self.is_dragging_handle = True
            else:
                self.is_dragging_canvas = True
            self.last_mouse_pos = event.position()

    def mouseMoveEvent(self, event):
        if self.is_dragging_handle:
            rect = self._get_image_rect()
            if rect.width() > 0:
                rel = (event.position().x() - rect.left()) / rect.width()
                self.split_pos = max(0.0, min(1.0, rel))
                self.update()
        elif self.is_dragging_canvas:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.position()
            self.update()
        else:
            line_x = self._get_split_screen_x()
            if abs(event.position().x() - line_x) <= 24:
                self.setCursor(Qt.SplitHCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def mouseReleaseEvent(self, event):
        self.is_dragging_handle = False
        self.is_dragging_canvas = False

    def _get_image_rect(self) -> QRectF:
        if self.pixmap_before.isNull():
            return QRectF()
        w, h = self.width(), self.height()
        base_scale = min(w / self.pixmap_before.width(), h / self.pixmap_before.height()) * 0.95
        scale = base_scale * self.zoom

        img_w = self.pixmap_before.width() * scale
        img_h = self.pixmap_before.height() * scale

        ox = (w - img_w) / 2 + self.pan_offset.x()
        oy = (h - img_h) / 2 + self.pan_offset.y()
        return QRectF(ox, oy, img_w, img_h)

    def _get_split_screen_x(self) -> float:
        rect = self._get_image_rect()
        return rect.left() + (rect.width() * self.split_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.fillRect(self.rect(), self.checker_brush)

        rect = self._get_image_rect()
        if rect.width() <= 0 or rect.height() <= 0:
            return

        split_x = self._get_split_screen_x()

        # Правая половина
        painter.save()
        right_clip = QRectF(split_x, rect.top(), max(0.0, rect.right() - split_x), rect.height())
        painter.setClipRect(right_clip)
        painter.drawPixmap(rect.toRect(), self.pixmap_after)
        painter.restore()

        # Левая половина
        painter.save()
        left_clip = QRectF(rect.left(), rect.top(), max(0.0, split_x - rect.left()), rect.height())
        painter.setClipRect(left_clip)
        painter.drawPixmap(rect.toRect(), self.pixmap_before)
        painter.restore()

        # Линия-разделитель
        painter.setPen(QPen(QColor(10, 10, 12, 190), 2.5))
        painter.drawLine(int(split_x), int(rect.top()), int(split_x), int(rect.bottom()))
        painter.setPen(QPen(QColor(255, 255, 255, 230), 1.2))
        painter.drawLine(int(split_x), int(rect.top()), int(split_x), int(rect.bottom()))

        # Центральная ручка
        center_y = rect.top() + rect.height() / 2
        painter.setBrush(QColor(18, 20, 26, 245))
        painter.setPen(QPen(QColor(255, 255, 255, 210), 1.5))
        painter.drawEllipse(QPointF(split_x, center_y), 16, 16)

        painter.setBrush(QColor(244, 63, 94))
        painter.setPen(Qt.NoPen)
        tri_left = QPolygonF([
            QPointF(split_x - 3, center_y - 5),
            QPointF(split_x - 9, center_y),
            QPointF(split_x - 3, center_y + 5)
        ])
        painter.drawPolygon(tri_left)

        painter.setBrush(QColor(56, 189, 248))
        tri_right = QPolygonF([
            QPointF(split_x + 3, center_y - 5),
            QPointF(split_x + 9, center_y),
            QPointF(split_x + 3, center_y + 5)
        ])
        painter.drawPolygon(tri_right)

        if self.is_processing:
            painter.setBrush(QColor(0, 0, 0, 160))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(self.width() // 2 - 40, self.height() // 2 - 40, 80, 80, 12, 12)

            pen = QPen(QColor(56, 189, 248), 4)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            spinner_rect = QRectF(self.width() // 2 - 22, self.height() // 2 - 22, 44, 44)
            painter.drawArc(spinner_rect, int(-self.spinner_angle * 16), int(260 * 16))


class MacTitleBar(QWidget):
    def __init__(self, title: str, on_close, on_min, on_max, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self._parent = parent
        self._is_moving = False
        self._start_pos = QPointF(0, 0)

        # Компоновка заголовка: центрированный текст и увеличенные кнопки справа
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 14, 0)
        layout.setSpacing(10)

        # Пустой балансировочный блок слева для идеального центрирования заголовка
        self.left_spacer = QWidget()
        self.left_spacer.setFixedWidth(70)
        layout.addWidget(self.left_spacer)

        self.lbl_title = QLabel(title)
        self.lbl_title.setAlignment(Qt.AlignCenter)
        self.lbl_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #888888; background: transparent;")
        layout.addWidget(self.lbl_title, stretch=1)

        # Увеличенные кнопки справа (16x16)
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_min = QPushButton()
        self.btn_min.setFixedSize(16, 16)
        self.btn_min.setCursor(Qt.PointingHandCursor)
        self.btn_min.setToolTip("Свернуть")
        self.btn_min.clicked.connect(on_min)

        self.btn_max = QPushButton()
        self.btn_max.setFixedSize(16, 16)
        self.btn_max.setCursor(Qt.PointingHandCursor)
        self.btn_max.setToolTip("Развернуть")
        self.btn_max.clicked.connect(on_max)

        self.btn_close = QPushButton()
        self.btn_close.setFixedSize(16, 16)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("Закрыть")
        self.btn_close.clicked.connect(on_close)

        self._style_window_btn(self.btn_min, bg_color="#737373", icon_type="min")
        self._style_window_btn(self.btn_max, bg_color="#b3b3b3", icon_type="max")
        self._style_window_btn(self.btn_close, bg_color="#ffffff", icon_type="close")

        btn_box.addWidget(self.btn_min)
        btn_box.addWidget(self.btn_max)
        btn_box.addWidget(self.btn_close)

        layout.addLayout(btn_box)

    def _style_window_btn(self, btn: QPushButton, bg_color: str, icon_type: str):
        pix = QPixmap(18, 18)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor(bg_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 18, 18)

        icon_pen = QPen(QColor("#171717"), 1.8)
        icon_pen.setCapStyle(Qt.RoundCap)
        icon_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(icon_pen)

        if icon_type == "min":
            painter.drawLine(5, 9, 13, 9)
        elif icon_type == "max":
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(QRectF(5.5, 5.5, 7.0, 7.0), 1.0, 1.0)
        elif icon_type == "close":
            painter.drawLine(QPointF(5.5, 5.5), QPointF(12.5, 12.5))
            painter.drawLine(QPointF(12.5, 5.5), QPointF(5.5, 12.5))
        painter.end()

        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 9px;
            }
            QPushButton:hover {
                opacity: 0.88;
            }
        """)
        btn.setIcon(pix)
        btn.setIconSize(pix.size())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_moving = True
            self._start_pos = event.globalPosition() - self.window().frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._is_moving:
            self.window().move((event.globalPosition() - self._start_pos).toPoint())

    def mouseReleaseEvent(self, event):
        self._is_moving = False


class SquooshStudioDialog(QDialog):
    def __init__(self, src_path: Path, processed_path: Path = None, theme_key: str = "dark", lang: str = "ru", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1200, 800)

        self.theme_key = theme_key
        self.lang = lang
        self.t = THEMES.get(theme_key, THEMES["dark"])

        self.src_path = Path(src_path)
        self.target_path = Path(processed_path) if processed_path else self.src_path

        with Image.open(self.target_path) as im:
            im = ImageOps.exif_transpose(im)
            self.base_pil_image = im.convert("RGBA")

        with Image.open(self.src_path) as orig_im:
            orig_im = ImageOps.exif_transpose(orig_im)
            self.orig_pil_image = orig_im.convert("RGBA")

        self.orig_w, self.orig_h = self.base_pil_image.size
        self.src_bytes_size = self.src_path.stat().st_size

        self.latest_compressed_bytes = b""
        self.compress_thread = None
        self.compress_worker = None

        self.render_timer = QTimer(self)
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._run_async_compression)

        self._init_ui()
        self._apply_dialog_theme()
        self._trigger_recalculate()

    def _init_ui(self):
        container = QFrame(self)
        container.setObjectName("dialogContainer")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)

        dialog_layout = QVBoxLayout(container)
        dialog_layout.setContentsMargins(10, 10, 10, 10)
        dialog_layout.setSpacing(6)

        titlebar = MacTitleBar("Image Studio", self.close, self.showMinimized, self._toggle_max, self)
        dialog_layout.addWidget(titlebar)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)

        left_box = QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(8)

        buf = io.BytesIO()
        self.orig_pil_image.save(buf, format="PNG")
        buf.seek(0)
        orig_pixmap = QPixmap()
        orig_pixmap.loadFromData(buf.getvalue())

        self.canvas = InteractiveCompareCanvas(orig_pixmap)
        left_box.addWidget(self.canvas, stretch=1)

        bottom_bar = QHBoxLayout()
        self.hint = QLabel("Колесико: зум | Зажатая ЛКМ: панорама | Ползунок: сравнение")
        self.btn_reset = QPushButton("Сброс вида")
        self.btn_reset.clicked.connect(self.canvas.reset_view)
        bottom_bar.addWidget(self.hint)
        bottom_bar.addStretch()
        bottom_bar.addWidget(self.btn_reset)
        left_box.addLayout(bottom_bar)

        content_layout.addLayout(left_box, stretch=1)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(360)
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(20, 20, 20, 20)
        sb_layout.setSpacing(14)

        row_resize_head = QHBoxLayout()
        self.sec_edit = QLabel("Изменить размер")
        self.sec_edit.setStyleSheet("font-weight: 700; font-size: 15px;")
        self.toggle_resize = SmoothToggle(checked=False, theme_data=self.t)
        self.toggle_resize.toggled.connect(self._toggle_resize)
        row_resize_head.addWidget(self.sec_edit)
        row_resize_head.addStretch()
        row_resize_head.addWidget(self.toggle_resize)
        sb_layout.addLayout(row_resize_head)

        row_filter = QHBoxLayout()
        row_filter.addWidget(QLabel("Метод:"))
        self.combo_method = ModernComboBox()
        for name in RESIZE_FILTERS:
            self.combo_method.addItem(name)
        self.combo_method.currentIndexChanged.connect(self._trigger_recalculate)
        row_filter.addWidget(self.combo_method)
        sb_layout.addLayout(row_filter)

        row_preset = QHBoxLayout()
        row_preset.addWidget(QLabel("Пресеты:"))
        self.combo_preset = ModernComboBox()
        self.combo_preset.addItems(["Custom", "100%", "75%", "50%", "25%"])
        self.combo_preset.currentTextChanged.connect(self._on_preset_change)
        row_preset.addWidget(self.combo_preset)
        sb_layout.addLayout(row_preset)

        row_wh = QHBoxLayout()
        row_wh.addWidget(QLabel("Ш:"))
        self.edit_w = QLineEdit(str(self.orig_w))
        self.edit_w.textEdited.connect(self._on_width_edited)
        row_wh.addWidget(self.edit_w)

        row_wh.addWidget(QLabel("В:"))
        self.edit_h = QLineEdit(str(self.orig_h))
        self.edit_h.textEdited.connect(self._on_height_edited)
        row_wh.addWidget(self.edit_h)
        sb_layout.addLayout(row_wh)

        row_aspect = QHBoxLayout()
        row_aspect.addWidget(QLabel("Сохранить соотношение"))
        row_aspect.addStretch()
        self.toggle_aspect = SmoothToggle(checked=True, theme_data=self.t)
        row_aspect.addWidget(self.toggle_aspect)
        sb_layout.addLayout(row_aspect)

        self.sep = QFrame()
        self.sep.setFrameShape(QFrame.HLine)
        sb_layout.addWidget(self.sep)

        self.sec_comp = QLabel("Сжатие (WebP)")
        self.sec_comp.setStyleSheet("font-weight: 700; font-size: 15px;")
        sb_layout.addWidget(self.sec_comp)

        row_lossless = QHBoxLayout()
        row_lossless.addWidget(QLabel("Без потерь (больше размер):"))
        row_lossless.addStretch()
        self.toggle_lossless = SmoothToggle(checked=False, theme_data=self.t)
        self.toggle_lossless.toggled.connect(self._on_lossless_toggled)
        row_lossless.addWidget(self.toggle_lossless)
        sb_layout.addLayout(row_lossless)

        self.lbl_effort = QLabel("Глубина сжатия: 4")
        sb_layout.addWidget(self.lbl_effort)
        self.slider_effort = QSlider(Qt.Horizontal)
        self.slider_effort.setRange(0, 6)
        self.slider_effort.setValue(4)
        self.slider_effort.valueChanged.connect(self._on_effort_slide)
        sb_layout.addWidget(self.slider_effort)

        self.lbl_quality = QLabel("Качество: 75")
        sb_layout.addWidget(self.lbl_quality)
        self.slider_quality = QSlider(Qt.Horizontal)
        self.slider_quality.setRange(1, 100)
        self.slider_quality.setValue(75)
        self.slider_quality.valueChanged.connect(self._on_quality_slide)
        sb_layout.addWidget(self.slider_quality)

        sb_layout.addStretch()

        self.info_badge = QLabel("Сжатие...")
        self.info_badge.setAlignment(Qt.AlignCenter)
        sb_layout.addWidget(self.info_badge)

        self.btn_save = QPushButton("Сохранить  ↓")
        self.btn_save.setFixedHeight(46)
        self.btn_save.clicked.connect(self._on_save_clicked)
        sb_layout.addWidget(self.btn_save)

        content_layout.addWidget(self.sidebar)
        dialog_layout.addLayout(content_layout)

        self._toggle_resize(False)

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _apply_dialog_theme(self):
        t = self.t
        is_dark = self.theme_key != "light"
        self.canvas.set_canvas_bg(t["bg"], dark_mode=is_dark)

        self.setStyleSheet(f"""
            QFrame#dialogContainer {{
                background-color: {t["bg"]};
                border: 1px solid {t["card_border"]};
                border-radius: 18px;
            }}
            QLabel {{ color: {t["text"]}; font-size: 13px; background: transparent; }}
            QFrame#sidebar {{
                background-color: {t["card"]};
                border: 1px solid {t["card_border"]};
                border-radius: 16px;
            }}
            QLineEdit {{
                background-color: {t["input_bg"]};
                color: {t["text"]};
                border: 1px solid {t["input_border"]};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit:focus {{ border-color: {t["accent"]}; }}
            QSlider {{
                background: transparent;
            }}
            QSlider::groove:horizontal {{
                height: 5px;
                background: {t["input_border"]};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {t["accent"]};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {t["accent"]};
                border: 2px solid {t["card"]};
                width: 14px;
                height: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }}
        """)

        self.combo_method.apply_theme(t)
        self.combo_preset.apply_theme(t)

        self.sec_edit.setStyleSheet(f"font-weight: 700; font-size: 15px; color: {t['accent']}; background: transparent;")
        self.sec_comp.setStyleSheet(f"font-weight: 700; font-size: 15px; color: {t['accent']}; background: transparent;")
        self.hint.setStyleSheet(f"color: {t['subtext']}; font-size: 12px; background: transparent;")
        self.sep.setStyleSheet(f"background-color: {t['card_border']};")

        self.toggle_resize.set_theme(t)
        self.toggle_aspect.set_theme(t)
        self.toggle_lossless.set_theme(t)

        self.btn_reset.setStyleSheet(f"""
            QPushButton {{
                background-color: {t["input_bg"]};
                color: {t["text"]};
                border: 1px solid {t["input_border"]};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{ border-color: {t["accent"]}; }}
        """)

        self.info_badge.setStyleSheet(f"""
            background-color: {t["input_bg"]};
            color: {t["accent"]};
            border: 1px solid {t["card_border"]};
            border-radius: 8px;
            padding: 10px;
            font-size: 13px;
            font-weight: 700;
        """)

        btn_text_color = "#000000" if (self.theme_key == "light" or self.theme_key == "black") else "#ffffff"
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {t["accent"]};
                color: {btn_text_color};
                font-size: 14px;
                font-weight: 700;
                border: none;
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background-color: {t["accent_hover"]};
            }}
        """)

    def _toggle_resize(self, active: bool):
        self.combo_method.setEnabled(active)
        self.combo_preset.setEnabled(active)
        self.edit_w.setEnabled(active)
        self.edit_h.setEnabled(active)
        self.toggle_aspect.setEnabled(active)
        self._trigger_recalculate()

    def _on_lossless_toggled(self, checked: bool):
        self.slider_quality.setEnabled(not checked)
        self.lbl_quality.setEnabled(not checked)
        self._trigger_recalculate()

    def _on_effort_slide(self, val):
        self.lbl_effort.setText(f"Effort: {val}")
        self._trigger_recalculate()

    def _on_quality_slide(self, val):
        self.lbl_quality.setText(f"Quality: {val}")
        self._trigger_recalculate()

    def _on_preset_change(self, text):
        if text == "100%":
            self.edit_w.setText(str(self.orig_w))
            self.edit_h.setText(str(self.orig_h))
        elif text == "75%":
            self.edit_w.setText(str(int(self.orig_w * 0.75)))
            self.edit_h.setText(str(int(self.orig_h * 0.75)))
        elif text == "50%":
            self.edit_w.setText(str(int(self.orig_w * 0.50)))
            self.edit_h.setText(str(int(self.orig_h * 0.50)))
        elif text == "25%":
            self.edit_w.setText(str(int(self.orig_w * 0.25)))
            self.edit_h.setText(str(int(self.orig_h * 0.25)))
        self._trigger_recalculate()

    def _on_width_edited(self, text):
        if self.toggle_aspect.isChecked() and text.isdigit() and int(text) > 0:
            w = int(text)
            ratio = self.orig_h / self.orig_w
            self.edit_h.setText(str(max(1, int(w * ratio))))
        self.combo_preset.setCurrentText("Custom")
        self._trigger_recalculate()

    def _on_height_edited(self, text):
        if self.toggle_aspect.isChecked() and text.isdigit() and int(text) > 0:
            h = int(text)
            ratio = self.orig_w / self.orig_h
            self.edit_w.setText(str(max(1, int(h * ratio))))
        self.combo_preset.setCurrentText("Custom")
        self._trigger_recalculate()

    def _trigger_recalculate(self):
        self.canvas.set_processing(True)
        self.render_timer.start(90)

    def _run_async_compression(self):
        target_w = self.orig_w
        target_h = self.orig_h
        if self.toggle_resize.isChecked():
            try:
                target_w = max(1, int(self.edit_w.text()))
                target_h = max(1, int(self.edit_h.text()))
            except Exception:
                pass

        resample_filter = RESIZE_FILTERS.get(self.combo_method.currentText(), Image.Resampling.LANCZOS)
        resize_data = (self.toggle_resize.isChecked(), target_w, target_h, resample_filter)

        if self.compress_thread and self.compress_thread.isRunning():
            self.compress_thread.quit()
            self.compress_thread.wait()

        self.compress_thread = QThread()
        self.compress_worker = CompressWorker(
            pil_image=self.base_pil_image,
            resize_data=resize_data,
            quality=self.slider_quality.value(),
            effort=self.slider_effort.value(),
            lossless=self.toggle_lossless.isChecked(),
        )
        self.compress_worker.moveToThread(self.compress_thread)

        self.compress_thread.started.connect(self.compress_worker.run)
        self.compress_worker.finished.connect(self._on_compression_finished)

        self.compress_thread.start()

    def _on_compression_finished(self, data: bytes, size_bytes: int):
        self.latest_compressed_bytes = data
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        self.canvas.set_after_pixmap(pixmap)

        diff_percent = ((size_bytes - self.src_bytes_size) / self.src_bytes_size) * 100
        sign = "+" if diff_percent > 0 else ""
        badge_text = f"↓ {sign}{diff_percent:.0f}%  |  {format_file_size(size_bytes)}"
        self.info_badge.setText(badge_text)

        self.compress_thread.quit()
        self.compress_thread.wait()

    def _on_save_clicked(self):
        t = self.t
        menu = QMenu(self)
        menu.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t["card"]};
                color: {t["text"]};
                border: 1px solid {t["card_border"]};
                border-radius: 8px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 8px 24px;
                border-radius: 6px;
                font-weight: 600;
                background-color: transparent;
                color: {t["text"]};
            }}
            QMenu::item:selected {{
                background-color: {t["accent"]};
                color: #ffffff;
            }}
        """)
        action_overwrite = menu.addAction("Перезаписать файл (по умолчанию)")
        action_save_as = menu.addAction("Сохранить как новый файл...")

        action = menu.exec(self.btn_save.mapToGlobal(QPointF(0, self.btn_save.height()).toPoint()))
        if action == action_save_as:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить как...",
                str(self.target_path.with_name(f"{self.target_path.stem}_squoosh.webp")),
                "WebP (*.webp)",
            )
            if path:
                Path(path).write_bytes(self.latest_compressed_bytes)
                self.accept()
        else:
            self.target_path.write_bytes(self.latest_compressed_bytes)
            self.accept()
