import os
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image
from PySide6.QtCore import Qt, QThread, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from core.config import (
    DEFAULT_IN_DIR,
    DEFAULT_OUT_DIR,
    DEFAULT_MODEL_ID,
    DEFAULT_WEBP_QUALITY,
    DEFAULT_WEBP_EFFORT,
    MODELS_META,
    THEMES,
    build_qss,
    clear_all_history,
    delete_history_entries,
    load_app_lang,
    load_app_theme,
    load_history,
    save_app_lang,
    save_app_theme,
    tr,
)
from gui.viewer import (
    ModernComboBox,
    SmoothToggle,
    SquooshStudioDialog,
    MacTitleBar,
    create_checker_brush,
    is_image_has_alpha,
)
from gui.worker import ProcessingTask, ProcessingWorker


def open_folder_in_os(path: Path):
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class ModernCheckbox(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked: bool = False, theme_data=None, parent=None):
        super().__init__(parent)
        self.setFixedSize(22, 22)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self.theme_data = theme_data or THEMES["dark"]

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self.update()
            self.toggled.emit(checked)

    def set_theme(self, theme_data):
        self.theme_data = theme_data
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(2, 2, 18, 18)
        if self._checked:
            painter.setBrush(QColor(self.theme_data["accent"]))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 5, 5)

            check_pen = QPen(QColor("#000000" if self.theme_data.get("name") == "Белая (Clean Light)" else "#ffffff"), 2)
            check_pen.setCapStyle(Qt.RoundCap)
            check_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(check_pen)

            p1 = QPointF(6, 11)
            p2 = QPointF(9.5, 14.5)
            p3 = QPointF(15.5, 7.5)
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)
        else:
            painter.setBrush(QColor(self.theme_data["input_bg"]))
            painter.setPen(QPen(QColor(self.theme_data["input_border"]), 1.5))
            painter.drawRoundedRect(rect, 5, 5)


class FullscreenInteractiveCanvas(QWidget):
    def __init__(self, pixmap: QPixmap, has_alpha: bool = False, dark_mode: bool = True, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.has_alpha = has_alpha
        self.dark_mode = dark_mode
        self.zoom = 1.0
        self.pan_offset = QPointF(0, 0)
        self.is_dragging = False
        self.last_mouse_pos = QPointF(0, 0)
        self.checker_brush = create_checker_brush(dark_mode=dark_mode)
        self.setMouseTracking(True)

    def reset_view(self):
        self.zoom = 1.0
        self.pan_offset = QPointF(0, 0)
        self.update()

    def wheelEvent(self, event):
        factor = 1.15 if event.angleDelta().y() > 0 else 0.85
        self.zoom = max(0.1, min(10.0, self.zoom * factor))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.position() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.setCursor(Qt.ArrowCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self.has_alpha:
            painter.fillRect(self.rect(), self.checker_brush)
        else:
            bg_col = QColor(10, 10, 12) if self.dark_mode else QColor(245, 245, 248)
            painter.fillRect(self.rect(), bg_col)

        if self.pixmap.isNull():
            return

        w, h = self.width(), self.height()
        base_scale = min(w / self.pixmap.width(), h / self.pixmap.height()) * 0.95
        scale = base_scale * self.zoom

        img_w = self.pixmap.width() * scale
        img_h = self.pixmap.height() * scale

        ox = (w - img_w) / 2 + self.pan_offset.x()
        oy = (h - img_h) / 2 + self.pan_offset.y()

        painter.drawPixmap(int(ox), int(oy), int(img_w), int(img_h), self.pixmap)


class FullscreenImageViewer(QDialog):
    def __init__(self, image_path: Path, theme_data, lang: str = "ru", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1100, 800)

        is_dark = theme_data.get("name") != "Белая (Clean Light)"

        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_data['bg']};
                border: 1px solid {theme_data['card_border']};
                border-radius: 18px;
            }}
        """)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        titlebar = MacTitleBar(f"{tr('app_title', lang)}: {image_path.name}", self.close, self.showMinimized, self._toggle_max, self)
        layout.addWidget(titlebar)

        has_alpha = False
        try:
            with Image.open(image_path) as im:
                has_alpha = is_image_has_alpha(im)
        except Exception:
            pass

        pix = QPixmap(str(image_path))
        self.canvas = FullscreenInteractiveCanvas(pix, has_alpha=has_alpha, dark_mode=is_dark)
        layout.addWidget(self.canvas, stretch=1)

        bottom = QHBoxLayout()
        hint = QLabel(tr("zoom_hint", lang))
        hint.setStyleSheet(f"color: {theme_data['subtext']}; font-size: 12px; background: transparent;")
        btn_reset = QPushButton(tr("reset_scale", lang))
        btn_reset.clicked.connect(self.canvas.reset_view)
        bottom.addWidget(hint)
        bottom.addStretch()
        bottom.addWidget(btn_reset)
        layout.addLayout(bottom)

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()


class DropArea(QFrame):
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")

        layout = QVBoxLayout(self)
        self.lbl_main = QLabel("DROP ME")
        self.lbl_main.setAlignment(Qt.AlignCenter)

        self.lbl_sub = QLabel("Перетащите файлы сюда или кликните для выбора")
        self.lbl_sub.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(self.lbl_main)
        layout.addWidget(self.lbl_sub)
        layout.addStretch()

    def update_texts(self, lang: str):
        self.lbl_main.setText(tr("drop_title", lang))
        self.lbl_sub.setText(tr("drop_sub", lang))

    def apply_style(self, theme_data):
        self.setStyleSheet(f"""
            QFrame#dropArea {{
                border: 2px dashed {theme_data["drop_border"]};
                border-radius: 16px;
                background-color: {theme_data["drop_bg"]};
            }}
            QFrame#dropArea:hover {{
                border-color: {theme_data["accent"]};
            }}
        """)
        self.lbl_main.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {theme_data['accent']}; background: transparent; border: none; letter-spacing: 1px;")
        self.lbl_sub.setStyleSheet(f"font-size: 13px; color: {theme_data['subtext']}; background: transparent; border: none;")

    def mousePressEvent(self, event):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выбор файлов",
            "",
            "Изображения (*.jpg *.jpeg *.png *.webp);;Все файлы (*.*)",
        )
        if paths:
            self.files_dropped.emit(paths)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                paths.append(str(p))
        if paths:
            self.files_dropped.emit(paths)


class ImagePreviewWidget(QFrame):
    def __init__(self, show_center_btn: bool = False, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 320)
        self.current_path = None
        self.show_center_btn = show_center_btn
        self.theme_data = THEMES["dark"]
        self.lang = "ru"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        self.image_container = QWidget()
        c_layout = QVBoxLayout(self.image_container)
        c_layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignCenter)
        self.canvas.setStyleSheet("background: transparent;")
        c_layout.addWidget(self.canvas)

        layout.addWidget(self.image_container, stretch=1)

        self.lbl_name = QLabel(tr("no_file", self.lang))
        self.lbl_name.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_name)

        self.btn_center_expand = QPushButton(self.image_container)
        self.btn_center_expand.setText(tr("fullscreen", self.lang))
        self.btn_center_expand.setFixedSize(140, 36)
        self.btn_center_expand.setCursor(Qt.PointingHandCursor)
        self.btn_center_expand.clicked.connect(self._open_fullscreen)
        self.btn_center_expand.setVisible(False)

    def set_lang(self, lang: str):
        self.lang = lang
        self.btn_center_expand.setText(tr("fullscreen", lang))
        if not self.current_path:
            self.lbl_name.setText(tr("no_file", lang))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cx = (self.image_container.width() - self.btn_center_expand.width()) // 2
        cy = (self.image_container.height() - self.btn_center_expand.height()) // 2
        self.btn_center_expand.move(cx, cy)

    def apply_style(self, theme_data):
        self.theme_data = theme_data
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme_data["card"]};
                border: 1px solid {theme_data["card_border"]};
                border-radius: 14px;
            }}
        """)
        self.lbl_name.setStyleSheet(f"color: {theme_data['subtext']}; font-size: 12px; font-weight: 700; background: transparent; border: none;")

        self.btn_center_expand.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(15, 23, 42, 210);
                color: {theme_data["accent"]};
                border: 1px solid {theme_data["accent"]};
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {theme_data["accent"]};
                color: #000000;
            }}
        """)

    def set_image(self, file_path: str):
        p = Path(file_path)
        if p.exists():
            self.current_path = p
            self.lbl_name.setText(p.name)

            has_alpha = False
            try:
                with Image.open(p) as im:
                    has_alpha = is_image_has_alpha(im)
            except Exception:
                pass

            pix = QPixmap(str(p))
            if not pix.isNull():
                scaled_pix = pix.scaled(280, 240, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                if has_alpha:
                    base = QPixmap(scaled_pix.size())
                    painter = QPainter(base)
                    is_dark = self.theme_data.get("name") != "Белая (Clean Light)"
                    painter.fillRect(base.rect(), create_checker_brush(dark_mode=is_dark))
                    painter.drawPixmap(0, 0, scaled_pix)
                    painter.end()
                    self.canvas.setPixmap(base)
                else:
                    self.canvas.setPixmap(scaled_pix)

            self.btn_center_expand.show()
            self.btn_center_expand.raise_()
        else:
            self.clear()

    def clear(self):
        self.current_path = None
        self.canvas.clear()
        self.lbl_name.setText(tr("select_file", self.lang))
        self.btn_center_expand.hide()

    def _open_fullscreen(self):
        if self.current_path and self.current_path.exists():
            dlg = FullscreenImageViewer(self.current_path, self.theme_data, self.lang, self)
            dlg.exec()


class ReferenceDockButton(QPushButton):
    def __init__(self, icon_type: str, text: str, parent=None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.label_text = text
        self.is_active = False
        self.theme_data = THEMES["dark"]
        self.setFixedSize(68, 56)
        self.setCursor(Qt.PointingHandCursor)

    def set_active(self, active: bool):
        self.is_active = active
        self.update()

    def set_text_label(self, text: str):
        self.label_text = text
        self.update()

    def set_theme(self, theme_data):
        self.theme_data = theme_data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(self.theme_data["accent"]) if self.is_active else QColor(self.theme_data["subtext"])

        cx = self.width() / 2.0
        cy = 18.0

        if self.icon_type == "home":
            pen = QPen(color, 2)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            path = QPainterPath()
            path.moveTo(cx - 10, cy + 8)
            path.lineTo(cx - 10, cy - 1)
            path.lineTo(cx, cy - 10)
            path.lineTo(cx + 10, cy - 1)
            path.lineTo(cx + 10, cy + 8)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawLine(int(cx - 4), int(cy + 4), int(cx + 4), int(cy + 4))

        elif self.icon_type == "folder":
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)

            path = QPainterPath()
            path.addRoundedRect(QRectF(cx - 11, cy - 10, 10, 6), 2, 2)
            path.addRoundedRect(QRectF(cx - 11, cy - 6, 22, 16), 4, 4)
            painter.drawPath(path)

            cut_color = QColor(self.theme_data["dock_btn_active"]) if self.is_active else QColor(self.theme_data["dock"])
            painter.setBrush(cut_color)
            painter.drawRoundedRect(QRectF(cx - 8, cy - 4, 16, 3), 1.5, 1.5)

        elif self.icon_type == "settings":
            pen = QPen(color, 2)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            poly = QPolygonF([
                QPointF(cx - 4, cy - 10),
                QPointF(cx + 4, cy - 10),
                QPointF(cx + 10, cy - 4),
                QPointF(cx + 10, cy + 4),
                QPointF(cx + 4, cy + 10),
                QPointF(cx - 4, cy + 10),
                QPointF(cx - 10, cy + 4),
                QPointF(cx - 10, cy - 4),
            ])
            painter.drawPolygon(poly)
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(cx, cy), 3, 3)

        painter.setPen(color)
        font = QFont("Segoe UI", 8)
        font.setBold(self.is_active)
        painter.setFont(font)
        painter.drawText(QRectF(0, 34, self.width(), 16), Qt.AlignCenter, self.label_text)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.current_theme = load_app_theme()
        self.current_lang = load_app_lang()

        self.setWindowTitle(tr("app_title", self.current_lang))

        icon_path = Path(__file__).resolve().parent.parent / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1040, 890)

        self.worker_thread = None
        self.worker = None
        self.results_map = {}
        self.history_checkboxes = []

        DEFAULT_IN_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)

        self._init_ui()
        self.apply_theme(self.current_theme)
        self.apply_lang(self.current_lang)

    def _init_ui(self):
        self.container = QFrame(self)
        self.container.setObjectName("windowContainer")

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.container)

        root_layout = QVBoxLayout(self.container)
        root_layout.setContentsMargins(16, 12, 16, 14)
        root_layout.setSpacing(10)

        # macOS заголовок
        self.titlebar = MacTitleBar("Image Studio", self.close, self.showMinimized, self._toggle_max, self)
        root_layout.addWidget(self.titlebar)

        self.stack = QStackedWidget()
        self.page_home = self._create_home_page()
        self.page_history = self._create_history_page()
        self.page_settings = self._create_settings_page()

        self.stack.addWidget(self.page_home)
        self.stack.addWidget(self.page_history)
        self.stack.addWidget(self.page_settings)
        root_layout.addWidget(self.stack, stretch=1)

        # Центрированный плавающий бар
        dock_container = QHBoxLayout()
        dock_container.setContentsMargins(0, 0, 0, 0)

        self.dock_frame = QFrame()
        self.dock_frame.setFixedSize(320, 68)
        dock_inner = QHBoxLayout(self.dock_frame)
        dock_inner.setContentsMargins(12, 6, 12, 6)
        dock_inner.setSpacing(14)

        self.btn_nav_home = ReferenceDockButton("home", tr("nav_home", self.current_lang))
        self.btn_nav_home.set_active(True)
        self.btn_nav_home.clicked.connect(lambda: self._switch_page(0, self.btn_nav_home))

        self.btn_nav_history = ReferenceDockButton("folder", tr("nav_history", self.current_lang))
        self.btn_nav_history.clicked.connect(lambda: self._switch_page(1, self.btn_nav_history))

        self.btn_nav_settings = ReferenceDockButton("settings", tr("nav_settings", self.current_lang))
        self.btn_nav_settings.clicked.connect(lambda: self._switch_page(2, self.btn_nav_settings))

        dock_inner.addWidget(self.btn_nav_home)
        dock_inner.addWidget(self.btn_nav_history)
        dock_inner.addWidget(self.btn_nav_settings)

        dock_container.addStretch()
        dock_container.addWidget(self.dock_frame)
        dock_container.addStretch()

        root_layout.addLayout(dock_container)

    def _toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def apply_lang(self, lang: str):
        self.current_lang = lang
        save_app_lang(lang)

        self.drop_area.update_texts(lang)
        self.home_preview.set_lang(lang)
        self.history_preview.set_lang(lang)

        self.btn_mode_converter.setText(tr("btn_convert", lang))
        self.btn_mode_remover.setText(tr("btn_remove_bg", lang))
        self.btn_mode_squoosh.setText(tr("btn_squoosh", lang))

        self.box_queue.setTitle(tr("queue_title", lang))
        self.btn_load_in.setText(tr("load_in", lang))
        self.btn_open_in.setText(tr("open_in", lang))
        self.btn_clear_queue.setText(tr("clear_queue", lang))

        self.box_ready.setTitle(tr("ready_title", lang))
        self.btn_load_out.setText(tr("load_out", lang))
        self.btn_open_out.setText(tr("open_out", lang))
        self.btn_clear_out.setText(tr("clear_out", lang))

        self.status_label.setText(tr("status_ready", lang))

        self.btn_nav_home.set_text_label(tr("nav_home", lang))
        self.btn_nav_history.set_text_label(tr("nav_history", lang))
        self.btn_nav_settings.set_text_label(tr("nav_settings", lang))

        self.lbl_hist_title.setText(tr("history_title", lang))
        self.btn_delete_selected.setText(tr("delete_selected", lang))
        self.btn_clear_history.setText(tr("clear_history", lang))
        self.btn_open_hist_squoosh.setText(tr("open_in_squoosh", lang))

        self.history_table.setHorizontalHeaderLabels([
            "",
            tr("col_date", lang),
            tr("col_src", lang),
            tr("col_dst", lang),
            tr("col_mode", lang),
            tr("col_size", lang),
        ])

        self.lbl_settings_head.setText(tr("settings_title", lang))
        self.box_theme.setTitle(tr("theme_section", lang))
        self.lbl_th.setText(tr("theme_select", lang))

        self.box_lang.setTitle(tr("lang_section", lang))
        self.lbl_lang.setText(tr("lang_select", lang))

        self.box_params.setTitle(tr("main_settings", lang))
        self.lbl_m.setText(tr("model_label", lang))
        self.lbl_o.setText(tr("save_dir_label", lang))
        self.btn_browse_dir.setText(tr("browse", lang))
        self.lbl_t1.setText(tr("suffix_label", lang))
        self.lbl_t2.setText(tr("delete_src_label", lang))

    def apply_theme(self, theme_key: str):
        self.current_theme = theme_key
        save_app_theme(theme_key)
        t = THEMES.get(theme_key, THEMES["dark"])

        self.container.setStyleSheet(f"""
            QFrame#windowContainer {{
                background-color: {t["bg"]};
                border: 1px solid {t["card_border"]};
                border-radius: 20px;
            }}
        """)

        self.setStyleSheet(f"""
            {build_qss(theme_key)}
            QLabel {{ background: transparent; }}
        """)

        self.drop_area.apply_style(t)
        self.home_preview.apply_style(t)
        self.history_preview.apply_style(t)

        self.combo_theme.apply_theme(t)
        self.combo_lang.apply_theme(t)
        self.combo_model.apply_theme(t)

        self.toggle_suffix.set_theme(t)
        self.toggle_delete.set_theme(t)

        for cb in self.history_checkboxes:
            cb.set_theme(t)

        self.dock_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {t["dock"]};
                border: 1px solid {t["dock_border"]};
                border-radius: 18px;
            }}
        """)

        for b in [self.btn_nav_home, self.btn_nav_history, self.btn_nav_settings]:
            b.set_theme(t)

        self._refresh_history_table()

    def _switch_page(self, index: int, btn_target: ReferenceDockButton):
        self.stack.setCurrentIndex(index)
        for b in [self.btn_nav_home, self.btn_nav_history, self.btn_nav_settings]:
            b.set_active(False)
        btn_target.set_active(True)

        if index == 1:
            self._refresh_history_table()

    def _create_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        top_split = QHBoxLayout()
        top_split.setSpacing(14)

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self._add_files_to_list)
        top_split.addWidget(self.drop_area, stretch=1)

        self.home_preview = ImagePreviewWidget(show_center_btn=True)
        top_split.addWidget(self.home_preview)
        layout.addLayout(top_split)

        # Кнопки режимов
        mode_box = QHBoxLayout()
        self.btn_mode_converter = QPushButton("Конвертировать")
        self.btn_mode_converter.setFixedHeight(40)
        self.btn_mode_converter.clicked.connect(lambda: self._set_mode_and_run("convert_only"))

        self.btn_mode_remover = QPushButton("Убрать фон")
        self.btn_mode_remover.setFixedHeight(40)
        self.btn_mode_remover.clicked.connect(lambda: self._set_mode_and_run("remove_bg"))

        self.btn_mode_squoosh = QPushButton("Редактор качества")
        self.btn_mode_squoosh.setFixedHeight(40)
        self.btn_mode_squoosh.clicked.connect(self._open_squoosh_direct)

        mode_box.addWidget(self.btn_mode_converter)
        mode_box.addWidget(self.btn_mode_remover)
        mode_box.addWidget(self.btn_mode_squoosh)
        layout.addLayout(mode_box)

        # Две колонки списков: 1. Очередь (in), 2. Готовые (out)
        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)

        # 1. Колонка "Очередь файлов"
        self.box_queue = QGroupBox("Очередь файлов")
        qb_layout = QVBoxLayout(self.box_queue)
        qb_layout.setSpacing(8)

        self.file_list = QListWidget()
        self.file_list.setFixedHeight(160)
        self.file_list.itemClicked.connect(self._on_queue_item_clicked)
        qb_layout.addWidget(self.file_list)

        q_actions = QHBoxLayout()
        self.btn_load_in = QPushButton("Загрузить из in")
        self.btn_load_in.clicked.connect(self._load_from_in_folder)
        self.btn_open_in = QPushButton("Открыть папку in")
        self.btn_open_in.clicked.connect(lambda: open_folder_in_os(DEFAULT_IN_DIR))
        self.btn_clear_queue = QPushButton("Очистить очередь")
        self.btn_clear_queue.clicked.connect(self._clear_files)

        q_actions.addWidget(self.btn_load_in)
        q_actions.addWidget(self.btn_open_in)
        q_actions.addWidget(self.btn_clear_queue)
        qb_layout.addLayout(q_actions)
        lists_row.addWidget(self.box_queue)

        # 2. Колонка "Готовые файлы" (out)
        self.box_ready = QGroupBox("Готовые файлы")
        rb_layout = QVBoxLayout(self.box_ready)
        rb_layout.setSpacing(8)

        self.ready_list = QListWidget()
        self.ready_list.setFixedHeight(160)
        self.ready_list.itemClicked.connect(self._on_ready_item_clicked)
        rb_layout.addWidget(self.ready_list)

        r_actions = QHBoxLayout()
        self.btn_load_out = QPushButton("Загрузить из out")
        self.btn_load_out.clicked.connect(self._load_from_out_folder)
        self.btn_open_out = QPushButton("Открыть папку out")
        self.btn_open_out.clicked.connect(lambda: open_folder_in_os(Path(self.edit_out.text().strip())))
        self.btn_clear_out = QPushButton("Очистить список")
        self.btn_clear_out.clicked.connect(self._clear_ready_files)

        r_actions.addWidget(self.btn_load_out)
        r_actions.addWidget(self.btn_open_out)
        r_actions.addWidget(self.btn_clear_out)
        rb_layout.addLayout(r_actions)
        lists_row.addWidget(self.box_ready)

        layout.addLayout(lists_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: 600;")
        layout.addWidget(self.status_label)

        return page

    def _on_queue_item_clicked(self, item):
        if item:
            path_str = item.data(Qt.UserRole)
            if path_str:
                self.home_preview.set_image(path_str)

    def _on_ready_item_clicked(self, item):
        if item:
            path_str = item.data(Qt.UserRole)
            if path_str:
                self.home_preview.set_image(path_str)

    def _create_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        head_layout = QHBoxLayout()
        self.lbl_hist_title = QLabel("История последних обработок")
        self.lbl_hist_title.setStyleSheet("font-size: 18px; font-weight: 800;")
        head_layout.addWidget(self.lbl_hist_title)
        head_layout.addStretch()

        self.btn_delete_selected = QPushButton("Удалить выбранные")
        self.btn_delete_selected.setFixedHeight(34)
        self.btn_delete_selected.clicked.connect(self._delete_selected_history)
        head_layout.addWidget(self.btn_delete_selected)

        self.btn_clear_history = QPushButton("Очистить всю историю")
        self.btn_clear_history.setFixedHeight(34)
        self.btn_clear_history.clicked.connect(self._clear_entire_history)
        head_layout.addWidget(self.btn_clear_history)

        layout.addLayout(head_layout)

        split_layout = QHBoxLayout()
        split_layout.setSpacing(14)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["", "Дата", "Исходник", "Результат", "Режим", "Размер"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.history_table.setColumnWidth(0, 38)
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setShowGrid(False)
        self.history_table.itemSelectionChanged.connect(self._on_history_selection_changed)
        split_layout.addWidget(self.history_table, stretch=1)

        self.history_preview = ImagePreviewWidget(show_center_btn=True)
        split_layout.addWidget(self.history_preview)
        layout.addLayout(split_layout)

        self.btn_open_hist_squoosh = QPushButton("Открыть выбранный в редакторе")
        self.btn_open_hist_squoosh.setFixedHeight(42)
        self.btn_open_hist_squoosh.clicked.connect(self._open_history_item_in_squoosh)
        layout.addWidget(self.btn_open_hist_squoosh)

        return page

    def _on_history_selection_changed(self):
        row = self.history_table.currentRow()
        items = load_history()
        if 0 <= row < len(items):
            target = items[row].get("dst") or items[row].get("src")
            if target:
                self.history_preview.set_image(target)

    def _create_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.lbl_settings_head = QLabel("Настройки")
        self.lbl_settings_head.setStyleSheet("font-size: 18px; font-weight: 800;")
        layout.addWidget(self.lbl_settings_head)

        # Выбор языка
        self.box_lang = QGroupBox("Язык интерфейса")
        bl_layout = QHBoxLayout(self.box_lang)
        self.lbl_lang = QLabel("Выберите язык:")
        self.lbl_lang.setStyleSheet("font-size: 14px; font-weight: 600;")
        bl_layout.addWidget(self.lbl_lang)

        self.combo_lang = ModernComboBox()
        self.combo_lang.addItem("Русский (RU)", "ru")
        self.combo_lang.addItem("English (EN)", "en")
        l_idx = self.combo_lang.findData(self.current_lang)
        if l_idx >= 0:
            self.combo_lang.setCurrentIndex(l_idx)
        self.combo_lang.currentIndexChanged.connect(
            lambda: self.apply_lang(self.combo_lang.currentData())
        )
        bl_layout.addWidget(self.combo_lang)
        layout.addWidget(self.box_lang)

        # Выбор темы
        self.box_theme = QGroupBox("Тема оформления")
        bt_layout = QHBoxLayout(self.box_theme)
        self.lbl_th = QLabel("Выберите тему:")
        self.lbl_th.setStyleSheet("font-size: 14px; font-weight: 600;")
        bt_layout.addWidget(self.lbl_th)

        self.combo_theme = ModernComboBox()
        self.combo_theme.addItem("Синяя (Dark Slate)", "dark")
        self.combo_theme.addItem("Черная (OLED Black)", "black")
        self.combo_theme.addItem("Белая (Clean Light)", "light")

        idx = self.combo_theme.findData(self.current_theme)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)
        self.combo_theme.currentIndexChanged.connect(
            lambda: self.apply_theme(self.combo_theme.currentData())
        )
        bt_layout.addWidget(self.combo_theme)
        layout.addWidget(self.box_theme)

        # Основные параметры
        self.box_params = QGroupBox("Основные настройки")
        bp_layout = QVBoxLayout(self.box_params)
        bp_layout.setSpacing(14)

        row_m = QHBoxLayout()
        self.lbl_m = QLabel("Нейросеть для фона:")
        self.lbl_m.setStyleSheet("font-size: 14px; font-weight: 600;")
        row_m.addWidget(self.lbl_m)

        self.combo_model = ModernComboBox()
        default_idx = 0
        for i, (m_id, note, size_str, _) in enumerate(MODELS_META):
            self.combo_model.addItem(f"{m_id} [{size_str}] - {note}", m_id)
            if m_id == DEFAULT_MODEL_ID:
                default_idx = i
        self.combo_model.setCurrentIndex(default_idx)
        row_m.addWidget(self.combo_model)
        bp_layout.addLayout(row_m)

        row_out = QHBoxLayout()
        self.lbl_o = QLabel("Сохранять в:")
        self.lbl_o.setStyleSheet("font-size: 14px; font-weight: 600;")
        row_out.addWidget(self.lbl_o)

        self.edit_out = QLineEdit(str(DEFAULT_OUT_DIR))
        row_out.addWidget(self.edit_out)
        self.btn_browse_dir = QPushButton("Обзор...")
        self.btn_browse_dir.clicked.connect(self._select_out_dir)
        row_out.addWidget(self.btn_browse_dir)
        bp_layout.addLayout(row_out)

        row_t1 = QHBoxLayout()
        self.lbl_t1 = QLabel("Добавлять имя модели в название файла:")
        self.lbl_t1.setStyleSheet("font-size: 13px; font-weight: 600;")
        row_t1.addWidget(self.lbl_t1)
        row_t1.addStretch()
        self.toggle_suffix = SmoothToggle(checked=True, theme_data=THEMES["dark"])
        row_t1.addWidget(self.toggle_suffix)
        bp_layout.addLayout(row_t1)

        row_t2 = QHBoxLayout()
        self.lbl_t2 = QLabel("Удалять исходники из in после успешной обработки:")
        self.lbl_t2.setStyleSheet("font-size: 13px; font-weight: 600;")
        row_t2.addWidget(self.lbl_t2)
        row_t2.addStretch()
        self.toggle_delete = SmoothToggle(checked=False, theme_data=THEMES["dark"])
        row_t2.addWidget(self.toggle_delete)
        bp_layout.addLayout(row_t2)

        layout.addWidget(self.box_params)
        layout.addStretch()
        return page

    def _refresh_history_table(self):
        items = load_history()
        self.history_table.setRowCount(len(items))
        self.history_checkboxes.clear()
        t = THEMES.get(self.current_theme, THEMES["dark"])

        for row, it in enumerate(items):
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.setContentsMargins(6, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb = ModernCheckbox(theme_data=t)
            cb_layout.addWidget(cb)
            self.history_table.setCellWidget(row, 0, cb_container)
            self.history_checkboxes.append(cb)

            self.history_table.setItem(row, 1, QTableWidgetItem(it.get("date", "-")))
            self.history_table.setItem(row, 2, QTableWidgetItem(Path(it.get("src", "")).name))
            self.history_table.setItem(row, 3, QTableWidgetItem(Path(it.get("dst", "")).name))
            self.history_table.setItem(row, 4, QTableWidgetItem(it.get("mode", "")))
            self.history_table.setItem(row, 5, QTableWidgetItem(f"{it.get('src_size')} -> {it.get('dst_size')}"))

    def _delete_selected_history(self):
        indices_to_delete = [
            i for i, cb in enumerate(self.history_checkboxes) if cb.isChecked()
        ]
        if indices_to_delete:
            delete_history_entries(indices_to_delete)
            self.history_preview.clear()
            self._refresh_history_table()

    def _clear_entire_history(self):
        clear_all_history()
        self.history_preview.clear()
        self._refresh_history_table()

    def _open_history_item_in_squoosh(self):
        row = self.history_table.currentRow()
        items = load_history()
        if 0 <= row < len(items):
            src = Path(items[row]["src"])
            dst = Path(items[row]["dst"])
            if dst.exists():
                dlg = SquooshStudioDialog(src, dst, theme_key=self.current_theme, lang=self.current_lang, parent=self)
                dlg.exec()

    def _add_files_to_list(self, paths):
        for p in paths:
            src = Path(p)
            target = DEFAULT_IN_DIR / src.name
            if src.parent != DEFAULT_IN_DIR:
                try:
                    shutil.copy2(src, target)
                    src = target
                except Exception:
                    pass
            full_path_str = str(src)
            existing_paths = [self.file_list.item(i).data(Qt.UserRole) for i in range(self.file_list.count())]
            if full_path_str not in existing_paths:
                item = QListWidgetItem(src.name)
                item.setData(Qt.UserRole, full_path_str)
                self.file_list.addItem(item)

        if self.file_list.count() > 0:
            first_path = self.file_list.item(0).data(Qt.UserRole)
            self.home_preview.set_image(first_path)

        self.status_label.setText(f"{tr('queue_title', self.current_lang)}: {self.file_list.count()}")

    def _load_from_in_folder(self):
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = [p for p in DEFAULT_IN_DIR.iterdir() if p.is_file() and p.suffix.lower() in exts]
        for f in files:
            full_path_str = str(f)
            existing_paths = [self.file_list.item(i).data(Qt.UserRole) for i in range(self.file_list.count())]
            if full_path_str not in existing_paths:
                item = QListWidgetItem(f.name)
                item.setData(Qt.UserRole, full_path_str)
                self.file_list.addItem(item)
        if files:
            self.home_preview.set_image(str(files[0]))

    def _load_from_out_folder(self):
        out_dir = Path(self.edit_out.text().strip())
        out_dir.mkdir(parents=True, exist_ok=True)
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        files = [p for p in out_dir.iterdir() if p.is_file() and p.suffix.lower() in exts]
        for f in files:
            full_path_str = str(f)
            existing_paths = [self.ready_list.item(i).data(Qt.UserRole) for i in range(self.ready_list.count())]
            if full_path_str not in existing_paths:
                item = QListWidgetItem(f.name)
                item.setData(Qt.UserRole, full_path_str)
                self.ready_list.addItem(item)
        if files:
            self.home_preview.set_image(str(files[0]))

    def _clear_files(self):
        self.file_list.clear()
        self.results_map.clear()
        self.home_preview.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText(tr("status_ready", self.current_lang))

    def _clear_ready_files(self):
        self.ready_list.clear()

    def _select_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Папка сохранения", self.edit_out.text())
        if d:
            self.edit_out.setText(d)

    def _open_squoosh_direct(self):
        current_item = self.file_list.currentItem() or self.ready_list.currentItem()
        target_path = Path(current_item.data(Qt.UserRole)) if current_item and current_item.data(Qt.UserRole) else None

        if not target_path or not target_path.exists():
            if self.file_list.count() > 0 and self.file_list.item(0).data(Qt.UserRole):
                target_path = Path(self.file_list.item(0).data(Qt.UserRole))
            elif self.ready_list.count() > 0 and self.ready_list.item(0).data(Qt.UserRole):
                target_path = Path(self.ready_list.item(0).data(Qt.UserRole))
            else:
                p, _ = QFileDialog.getOpenFileName(
                    self,
                    "Выберите изображение",
                    "",
                    "Изображения (*.jpg *.jpeg *.png *.webp)",
                )
                if not p:
                    return
                target_path = Path(p)

        dlg = SquooshStudioDialog(target_path, theme_key=self.current_theme, lang=self.current_lang, parent=self)
        dlg.exec()

    def _set_mode_and_run(self, mode: str):
        files = [self.file_list.item(i).data(Qt.UserRole) for i in range(self.file_list.count()) if self.file_list.item(i).data(Qt.UserRole)]
        if not files:
            self.status_label.setText("Сначала добавьте файлы в DROP ME!")
            return

        task = ProcessingTask(
            files=files,
            out_dir=self.edit_out.text().strip(),
            mode=mode,
            model_name=self.combo_model.currentData(),
            delete_src=self.toggle_delete.isChecked(),
            add_suffix=self.toggle_suffix.isChecked(),
            quality=DEFAULT_WEBP_QUALITY,
            effort=DEFAULT_WEBP_EFFORT,
            lossless=False,
        )

        self.btn_mode_converter.setEnabled(False)
        self.btn_mode_remover.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker_thread = QThread()
        self.worker = ProcessingWorker(task)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.file_progress.connect(self._on_file_progress)
        self.worker.item_finished.connect(self._on_item_finished)
        self.worker.log_message.connect(self.status_label.setText)
        self.worker.finished.connect(self._on_finished)

        self.worker_thread.start()

    def _on_file_progress(self, percent: int, msg: str):
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"[{percent}%] {msg}")

    def _on_item_finished(self, src: str, dst: str):
        self.results_map[src] = dst
        existing_paths = [self.ready_list.item(i).data(Qt.UserRole) for i in range(self.ready_list.count())]
        if dst not in existing_paths:
            dst_p = Path(dst)
            item = QListWidgetItem(dst_p.name)
            item.setData(Qt.UserRole, dst)
            self.ready_list.addItem(item)
        self.home_preview.set_image(dst)

    def _on_finished(self):
        self.progress_bar.setValue(100)
        self.status_label.setText(tr("status_done", self.current_lang))
        self.btn_mode_converter.setEnabled(True)
        self.btn_mode_remover.setEnabled(True)
        self.worker_thread.quit()
        self.worker_thread.wait()
