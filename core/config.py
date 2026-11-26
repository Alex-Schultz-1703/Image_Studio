import datetime
import json
import os
from pathlib import Path


def get_windows_known_folder(folder_name: str) -> Path:
    home = Path.home()
    if folder_name == "Pictures":
        candidates = [home / "Pictures", home / "Изображения"]
    elif folder_name == "Documents":
        candidates = [home / "Documents", home / "Документы"]
    else:
        candidates = [home / folder_name]

    for p in candidates:
        if p.exists():
            return p
    return home / folder_name


PICTURES_DIR = get_windows_known_folder("Pictures")
DOCUMENTS_DIR = get_windows_known_folder("Documents")

APP_PICTURES_DIR = PICTURES_DIR / "Image_Studio"
DEFAULT_IN_DIR = APP_PICTURES_DIR / "in"
DEFAULT_OUT_DIR = APP_PICTURES_DIR / "out"
MODELS_DIR = DOCUMENTS_DIR / "Image_Studio" / "Models"
APP_DATA_DIR = DOCUMENTS_DIR / "Image_Studio" / "Data"

os.environ["U2NET_HOME"] = str(MODELS_DIR)

DEFAULT_WEBP_QUALITY = 75
DEFAULT_WEBP_EFFORT = 4

MODELS_META = [
    ("bria-rmbg", "чистый край (non-commercial)", "~1.02 ГБ", "model.onnx"),
    ("isnet-general-use", "быстрая, хорошая", "~170 МБ", "isnet-general-use.onnx"),
    ("birefnet-general", "очень точная, для сложных краев", "~268 МБ", "birefnet-general.onnx"),
    ("birefnet-massive", "самая точная из общих", "~320 МБ", "birefnet-massive.onnx"),
    ("birefnet-general-lite", "облегченная birefnet", "~140 МБ", "birefnet-general-lite.onnx"),
    ("birefnet-hrsod", "упор на тонкие контуры", "~228 МБ", "birefnet-hrsod.onnx"),
    ("birefnet-dis", "для сложной формы", "~980 МБ", "birefnet-dis.onnx"),
    ("u2net", "универсальная, классическая", "~176 МБ", "u2net.onnx"),
]

DEFAULT_MODEL_ID = "bria-rmbg"

THEMES = {
    "dark": {
        "name": "Синяя (Dark Slate)",
        "bg": "#0b0f17",
        "card": "#111827",
        "card_border": "#1e293b",
        "dock": "#0f172a",
        "dock_border": "#1e293b",
        "dock_btn_active": "#1e293b",
        "accent": "#38bdf8",
        "accent_hover": "#0284c7",
        "text": "#f1f5f9",
        "subtext": "#94a3b8",
        "input_bg": "#1e293b",
        "input_border": "#334155",
        "table_header_bg": "#1e293b",
        "table_header_text": "#38bdf8",
        "table_selected": "#1e3a8a",
        "drop_bg": "#0f172a",
        "drop_border": "#334155",
        "toggle_track_on": "#38bdf8",
        "toggle_track_off": "#334155",
        "toggle_thumb": "#ffffff",
    },
    "black": {
        "name": "Черная (OLED Black)",
        "bg": "#000000",
        "card": "#0d0d0d",
        "card_border": "#222222",
        "dock": "#0a0a0a",
        "dock_border": "#262626",
        "dock_btn_active": "#1a1a1a",
        "accent": "#ffffff",
        "accent_hover": "#cccccc",
        "text": "#ffffff",
        "subtext": "#888888",
        "input_bg": "#141414",
        "input_border": "#282828",
        "table_header_bg": "#141414",
        "table_header_text": "#ffffff",
        "table_selected": "#262626",
        "drop_bg": "#080808",
        "drop_border": "#222222",
        "toggle_track_on": "#9ca3af",
        "toggle_track_off": "#262626",
        "toggle_thumb": "#000000",
    },
    "light": {
        "name": "Белая (Clean Light)",
        "bg": "#f8fafc",
        "card": "#ffffff",
        "card_border": "#e2e8f0",
        "dock": "#ffffff",
        "dock_border": "#cbd5e1",
        "dock_btn_active": "#f1f5f9",
        "accent": "#0284c7",
        "accent_hover": "#0369a1",
        "text": "#0f172a",
        "subtext": "#64748b",
        "input_bg": "#f8fafc",
        "input_border": "#cbd5e1",
        "table_header_bg": "#f1f5f9",
        "table_header_text": "#0369a1",
        "table_selected": "#e0f2fe",
        "drop_bg": "#ffffff",
        "drop_border": "#cbd5e1",
        "toggle_track_on": "#0284c7",
        "toggle_track_off": "#cbd5e1",
        "toggle_thumb": "#ffffff",
    },
}

TRANSLATIONS = {
    "ru": {
        "app_title": "Image Studio",
        "drop_title": "DROP ME",
        "drop_sub": "Перетащите файлы сюда или кликните для выбора",
        "btn_convert": "Конвертировать",
        "btn_remove_bg": "Убрать фон",
        "btn_squoosh": "Редактор качества",
        "queue_title": "Очередь файлов",
        "load_in": "Загрузить из in",
        "open_in": "Открыть папку in",
        "clear_queue": "Очистить очередь",
        "ready_title": "Готовые файлы",
        "load_out": "Загрузить из out",
        "open_out": "Открыть папку out",
        "clear_out": "Очистить список",
        "status_ready": "Готов к работе",
        "status_done": "Готово.",
        "nav_home": "Главная",
        "nav_history": "История",
        "nav_settings": "Настройки",
        "history_title": "История последних обработок",
        "delete_selected": "Удалить выбранные",
        "clear_history": "Очистить всю историю",
        "open_in_squoosh": "Открыть выбранный в редакторе",
        "settings_title": "Настройки",
        "theme_section": "Тема оформления",
        "theme_select": "Выберите тему:",
        "main_settings": "Основные настройки",
        "model_label": "Нейросеть для фона:",
        "save_dir_label": "Сохранять в:",
        "browse": "Обзор...",
        "suffix_label": "Добавлять имя модели в название файла:",
        "delete_src_label": "Удалять исходники из in после успешной обработки:",
        "lang_section": "Язык интерфейса",
        "lang_select": "Выберите язык:",
        "col_date": "Дата",
        "col_src": "Исходник",
        "col_dst": "Результат",
        "col_mode": "Режим",
        "col_size": "Размер",
        "fullscreen": "На весь экран",
        "no_file": "Нет файла",
        "select_file": "Выберите файл",
        "reset_scale": "Сброс масштаба",
        "zoom_hint": "Колесико: зум | Зажатая ЛКМ: перемещение",
        "resize_title": "Изменить размер",
        "method_label": "Метод:",
        "preset_label": "Пресеты:",
        "w_label": "Ш:",
        "h_label": "В:",
        "aspect_label": "Сохранить соотношение",
        "compress_title": "Сжатие (WebP)",
        "lossless_label": "Без потерь (больше размер):",
        "effort_label": "Глубина сжатия:",
        "quality_label": "Качество:",
        "save_btn": "Сохранить",
        "save_overwrite": "Перезаписать файл (по умолчанию)",
        "save_as": "Сохранить как новый файл...",
    },
    "en": {
        "app_title": "Image Studio",
        "drop_title": "DROP ME",
        "drop_sub": "Drop files here or click to select",
        "btn_convert": "Convert to WebP",
        "btn_remove_bg": "Remove Background",
        "btn_squoosh": "Quality Editor",
        "queue_title": "File Queue",
        "load_in": "Load from in",
        "open_in": "Open in folder",
        "clear_queue": "Clear queue",
        "ready_title": "Finished Files",
        "load_out": "Load from out",
        "open_out": "Open out folder",
        "clear_out": "Clear list",
        "status_ready": "Ready to work",
        "status_done": "Done.",
        "nav_home": "Home",
        "nav_history": "History",
        "nav_settings": "Settings",
        "history_title": "Recent Processing History",
        "delete_selected": "Delete Selected",
        "clear_history": "Clear All History",
        "open_in_squoosh": "Open selected in Squoosh",
        "settings_title": "Settings",
        "theme_section": "Theme Appearance",
        "theme_select": "Select theme:",
        "main_settings": "General Settings",
        "model_label": "Background AI Model:",
        "save_dir_label": "Save destination:",
        "browse": "Browse...",
        "suffix_label": "Append model name to output filename:",
        "delete_src_label": "Delete source files from in after processing:",
        "lang_section": "Interface Language",
        "lang_select": "Select language:",
        "col_date": "Date",
        "col_src": "Source",
        "col_dst": "Result",
        "col_mode": "Mode",
        "col_size": "Size",
        "fullscreen": "Full Screen",
        "no_file": "No file",
        "select_file": "Select a file",
        "reset_scale": "Reset Zoom",
        "zoom_hint": "Wheel: zoom | Hold LMB: pan",
        "resize_title": "Resize",
        "method_label": "Method:",
        "preset_label": "Presets:",
        "w_label": "W:",
        "h_label": "H:",
        "aspect_label": "Maintain aspect ratio",
        "compress_title": "Compress (WebP)",
        "lossless_label": "Lossless (larger file):",
        "effort_label": "Effort level:",
        "quality_label": "Quality:",
        "save_btn": "Save",
        "save_overwrite": "Overwrite file (default)",
        "save_as": "Save as new file...",
    }
}


def tr(key: str, lang: str = "ru") -> str:
    return TRANSLATIONS.get(lang, TRANSLATIONS["ru"]).get(key, key)


def build_qss(theme_key: str) -> str:
    t = THEMES.get(theme_key, THEMES["dark"])
    return f"""
        QWidget {{
            background-color: {t["bg"]};
            color: {t["text"]};
            font-family: system-ui, 'Segoe UI Variable', 'Segoe UI', Inter, sans-serif;
            font-size: 13px;
        }}
        QGroupBox {{
            border: 1px solid {t["card_border"]};
            border-radius: 14px;
            margin-top: 12px;
            font-weight: 700;
            font-size: 14px;
            padding: 16px;
            background-color: {t["card"]};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 6px;
            color: {t["accent"]};
        }}
        QListWidget {{
            background-color: {t["input_bg"]};
            border: 1px solid {t["input_border"]};
            border-radius: 10px;
            color: {t["text"]};
            padding: 6px;
        }}
        QTableWidget {{
            background-color: {t["card"]};
            border: 1px solid {t["card_border"]};
            border-radius: 10px;
            color: {t["text"]};
            gridline-color: transparent;
            selection-background-color: {t["table_selected"]};
            selection-color: {t["text"]};
        }}
        QHeaderView::section {{
            background-color: {t["table_header_bg"]};
            color: {t["table_header_text"]};
            border: none;
            border-bottom: 2px solid {t["card_border"]};
            padding: 8px 10px;
            font-weight: 700;
            font-size: 12px;
            letter-spacing: 0.5px;
        }}
        QTableCornerButton::section {{
            background-color: transparent;
            border: none;
        }}
        QLineEdit {{
            background-color: {t["input_bg"]};
            border: 1px solid {t["input_border"]};
            border-radius: 8px;
            padding: 7px 12px;
            color: {t["text"]};
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border-color: {t["accent"]};
        }}
        QPushButton {{
            background-color: {t["input_bg"]};
            border: 1px solid {t["input_border"]};
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
            color: {t["text"]};
        }}
        QPushButton:hover {{
            border-color: {t["accent"]};
            background-color: {t["table_selected"]};
        }}
        QProgressBar {{
            background-color: {t["input_bg"]};
            border-radius: 5px;
            height: 8px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background: {t["accent"]};
            border-radius: 5px;
        }}
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
    """


def is_model_downloaded(model_name: str) -> bool:
    for m_id, _, _, onnx_file in MODELS_META:
        if m_id == model_name:
            direct_file = MODELS_DIR / onnx_file
            sub_file = MODELS_DIR / m_id / onnx_file
            return direct_file.exists() or sub_file.exists()
    return False


def generate_unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    i = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def format_file_size(bytes_size: int) -> str:
    kb = bytes_size / 1024
    if kb < 1024:
        return f"{kb:.1f} КБ"
    mb = kb / 1024
    return f"{mb:.2f} МБ"


def save_history_entry(src_path: Path, dst_path: Path, mode: str):
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        h_file = APP_DATA_DIR / "history.json"
        history = []
        if h_file.exists():
            try:
                history = json.loads(h_file.read_text(encoding="utf-8"))
            except Exception:
                history = []

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "date": now_str,
            "src": str(src_path),
            "dst": str(dst_path),
            "mode": mode,
            "src_size": format_file_size(src_path.stat().st_size) if src_path.exists() else "-",
            "dst_size": format_file_size(dst_path.stat().st_size) if dst_path.exists() else "-",
        }
        history.insert(0, entry)
        history = history[:150]
        h_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def delete_history_entries(indices: list):
    try:
        h_file = APP_DATA_DIR / "history.json"
        if h_file.exists():
            history = json.loads(h_file.read_text(encoding="utf-8"))
            history = [entry for i, entry in enumerate(history) if i not in indices]
            h_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def clear_all_history():
    try:
        h_file = APP_DATA_DIR / "history.json"
        if h_file.exists():
            h_file.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_history() -> list:
    try:
        h_file = APP_DATA_DIR / "history.json"
        if h_file.exists():
            return json.loads(h_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def save_app_theme(theme_name: str):
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        t_file = APP_DATA_DIR / "theme.json"
        t_file.write_text(json.dumps({"theme": theme_name}), encoding="utf-8")
    except Exception:
        pass


def load_app_theme() -> str:
    try:
        t_file = APP_DATA_DIR / "theme.json"
        if t_file.exists():
            return json.loads(t_file.read_text(encoding="utf-8")).get("theme", "black")
    except Exception:
        pass
    return "black"


def save_app_lang(lang_code: str):
    try:
        APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
        l_file = APP_DATA_DIR / "lang.json"
        l_file.write_text(json.dumps({"lang": lang_code}), encoding="utf-8")
    except Exception:
        pass


def load_app_lang() -> str:
    try:
        l_file = APP_DATA_DIR / "lang.json"
        if l_file.exists():
            return json.loads(l_file.read_text(encoding="utf-8")).get("lang", "ru")
    except Exception:
        pass
    return "ru"
