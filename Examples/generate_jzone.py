from __future__ import annotations

import configparser
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import win32com.client  # type: ignore
except ImportError:
    win32com = None


BASE_PATH = Path(r"C:\techbar")
OUTPUT_FILE = BASE_PATH / "jzone.json"
CONFIG_FILE_NAME = ".zebar.json"
ITEMS_CONFIG_FILE_NAME = ".items.json"
FOLDER_ITEMS_CONFIG_FILE_NAME = ".folders.json"
WHATTYPES_CONFIG_FILE_NAME = ".whattypes.json"
SHORTCUT_FOLDER_PREFIX = "$_"

ALLOWED_EXTENSIONS = {".exe", ".lnk", ".url", ".rdp", ".ps1", ".bat"}
EXCLUDE_PREFIXES = ("_", ".")
EXCLUDE_FOLDER_NAMES = {"_hidden", ".git", "__pycache__"}

DEFAULT_MAIN_SECTION = "left"
DEFAULT_VIEW_SECTION = "left"
DEFAULT_ORDER = 9999
VALID_SECTIONS = {"left", "center", "right"}


FOLDER_ICON_MAP = {
    "outils": "🧰",
    "rdp": "🖥️",
    "services": "🌐",
    "clients": "👥",
    "reseau": "📡",
    "réseau": "📡",
    "scripts": "⚙️",
    "apps": "📦",
    "infra": "🖧",
    "temp": "🗂️",
}

EXTENSION_ICON_MAP = {
    ".url": "🔗",
    ".rdp": "🖥️",
    ".exe": "📦",
    ".lnk": "↗️",
    ".ps1": "⚙️",
    ".bat": "⚙️",
}

NAME_ICON_HINTS = {
    "glpi": "🎫",
    "portainer": "🐳",
    "docker": "🐳",
    "home assistant": "🏠",
    "meshcentral": "🖧",
    "n8n": "🔄",
    "omv": "💾",
    "homarr": "📊",
    "sharp": "🖨️",
    "nas": "💽",
}


def is_excluded_name(name: str, allow_special_files: bool = False) -> bool:
    if allow_special_files and name in {CONFIG_FILE_NAME, ITEMS_CONFIG_FILE_NAME, FOLDER_ITEMS_CONFIG_FILE_NAME}:
        return False
    return name.startswith(EXCLUDE_PREFIXES)


def normalize_section(value: Optional[str], default: str = DEFAULT_MAIN_SECTION) -> str:
    if not value:
        return default
    normalized = value.strip().lower()
    if normalized in VALID_SECTIONS:
        return normalized
    return default


def normalize_order(value: Any, default: int = DEFAULT_ORDER) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def normalize_color_value(data: Dict[str, Any]) -> str:
    color = data.get("backgroundColor")
    if color is None or str(color).strip() == "":
        color = data.get("bgColor")
    return str(color or "").strip()


def safe_id(text: str) -> str:
    value = text.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "item"


def is_shortcut_folder(folder_path: Path) -> bool:
    return folder_path.name.startswith(SHORTCUT_FOLDER_PREFIX)


def get_folder_alias_name(folder_path: Path) -> str:
    if is_shortcut_folder(folder_path):
        alias_name = folder_path.name[len(SHORTCUT_FOLDER_PREFIX):].strip()
        if alias_name:
            return alias_name
    return folder_path.name


def get_folder_target(folder_path: Path) -> Path:
    return folder_path


def read_whattypes_config(base_path: Path) -> Dict[str, Dict[str, Any]]:
    config_path = base_path / WHATTYPES_CONFIG_FILE_NAME

    if not config_path.exists():
        return {}

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {
                str(key): value
                for key, value in raw.items()
                if isinstance(value, dict)
            }
        print(f"{config_path} doit contenir un objet JSON.")
        return {}
    except Exception:
        print(f"Config types invalide dans {config_path}, ignoree.")
        return {}


def get_folder_override(
    overrides: Dict[str, Dict[str, Any]],
    folder_path: Path,
) -> Dict[str, Any]:
    return overrides.get(folder_path.name) or overrides.get(get_folder_alias_name(folder_path)) or {}


def apply_folder_override(
    folder_config: Dict[str, Any],
    folder_override: Dict[str, Any],
) -> Dict[str, Any]:
    if not folder_override:
        return folder_config

    merged = dict(folder_config)

    if folder_override.get("label") not in (None, ""):
        merged["label"] = str(folder_override["label"])
    if folder_override.get("icon") not in (None, ""):
        merged["icon"] = str(folder_override["icon"])
    if folder_override.get("mainSection") not in (None, ""):
        merged["mainSection"] = normalize_section(folder_override.get("mainSection"), merged["mainSection"])
    if folder_override.get("viewSection") not in (None, ""):
        merged["viewSection"] = normalize_section(folder_override.get("viewSection"), merged["viewSection"])
    if "order" in folder_override:
        merged["order"] = normalize_order(folder_override.get("order"), merged["order"])
    if "hidden" in folder_override:
        merged["hidden"] = bool(folder_override.get("hidden"))

    background_color = normalize_color_value(folder_override)
    if background_color:
        merged["backgroundColor"] = background_color

    return merged


def resolve_folder_entry_type(folder_path: Path, folder_override: Dict[str, Any]) -> str:
    override_type = str(folder_override.get("type") or "").strip().lower()
    if override_type in {"view", "folder"}:
        return override_type
    if is_shortcut_folder(folder_path):
        return "folder"
    return "view"


def static_right_section(view_name: str) -> List[Dict[str, Any]]:
    return [
        {
            "id": f"sysinfo-{view_name}",
            "type": "sysinfo",
            "label": "Sysinfo",
            "icon": "",
            "visible": True,
            "order": 0,
        },
        {
            "id": f"clock-{view_name}",
            "type": "clock",
            "label": "Heure",
            "icon": "",
            "visible": True,
            "order": 1,
        },
    ]


def resolve_shortcut_target(shortcut_path: Path) -> Optional[str]:
    if win32com is None:
        return None

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        target = shortcut.Targetpath
        return str(target).strip() if target else None
    except Exception:
        return None


def get_url_target(file_path: Path) -> str:
    parser = configparser.ConfigParser()
    parser.optionxform = str

    try:
        parser.read(file_path, encoding="utf-8")
        if parser.has_section("InternetShortcut") and parser.has_option("InternetShortcut", "URL"):
            return parser.get("InternetShortcut", "URL")
    except Exception:
        pass

    try:
        for line in file_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("URL="):
                return line[4:].strip()
    except Exception:
        pass

    return str(file_path)


def get_item_type(file_path: Path, shortcut_target: Optional[str] = None) -> str:
    ext = file_path.suffix.lower()

    if ext == ".url":
        return "url"
    if ext == ".rdp":
        return "file"
    if ext == ".exe":
        return "app"
    if ext in {".ps1", ".bat"}:
        return "command"
    if ext == ".lnk":
        if shortcut_target:
            target_ext = Path(shortcut_target).suffix.lower()
            if target_ext == ".exe":
                return "app"
            if target_ext in {".ps1", ".bat"}:
                return "command"
        return "file"

    return "file"


def get_target(file_path: Path, shortcut_target: Optional[str] = None) -> str:
    ext = file_path.suffix.lower()

    if ext == ".url":
        return get_url_target(file_path)
    if ext == ".lnk" and shortcut_target:
        return shortcut_target

    return str(file_path)


def detect_icon(label: str, extension: str, folder_name: Optional[str] = None) -> str:
    label_lower = label.lower()

    for hint, icon in NAME_ICON_HINTS.items():
        if hint in label_lower:
            return icon

    if folder_name:
        folder_lower = folder_name.lower()
        if folder_lower in FOLDER_ICON_MAP:
            return FOLDER_ICON_MAP[folder_lower]

    return EXTENSION_ICON_MAP.get(extension.lower(), "")


def read_folder_config(folder_path: Path) -> Dict[str, Any]:
    folder_alias_name = get_folder_alias_name(folder_path)
    config_path = folder_path / CONFIG_FILE_NAME
    default_config = {
        "label": folder_alias_name,
        "icon": detect_icon(folder_alias_name, "", folder_alias_name),
        "mainSection": DEFAULT_MAIN_SECTION,
        "viewSection": DEFAULT_VIEW_SECTION,
        "order": DEFAULT_ORDER,
        "hidden": False,
        "openFolderLabel": "Ouvrir dossier",
        "backLabel": "Retour",
        "backgroundColor": "",
    }

    if not config_path.exists():
        return default_config

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return {
            "label": str(data.get("label") or folder_alias_name),
            "icon": str(data.get("icon") or default_config["icon"]),
            "mainSection": normalize_section(data.get("mainSection"), DEFAULT_MAIN_SECTION),
            "viewSection": normalize_section(data.get("viewSection"), DEFAULT_VIEW_SECTION),
            "order": normalize_order(data.get("order"), DEFAULT_ORDER),
            "hidden": bool(data.get("hidden", False)),
            "openFolderLabel": str(data.get("openFolderLabel") or "Ouvrir dossier"),
            "backLabel": str(data.get("backLabel") or "Retour"),
            "backgroundColor": normalize_color_value(data),
        }
    except Exception:
        print(f"Config invalide dans {config_path}, configuration par defaut utilisee.")
        return default_config


def read_items_config(folder_path: Path) -> Dict[str, Dict[str, Any]]:
    items_config_path = folder_path / ITEMS_CONFIG_FILE_NAME

    if not items_config_path.exists():
        return {}

    try:
        raw = json.loads(items_config_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
        print(f"{items_config_path} doit contenir un objet JSON.")
        return {}
    except Exception:
        print(f"Config items invalide dans {items_config_path}, ignoree.")
        return {}


def read_folder_items_config(folder_path: Path) -> Dict[str, Dict[str, Any]]:
    folder_items_config_path = folder_path / FOLDER_ITEMS_CONFIG_FILE_NAME

    if not folder_items_config_path.exists():
        return {}

    try:
        raw = json.loads(folder_items_config_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {
                str(key): value
                for key, value in raw.items()
                if isinstance(value, dict)
            }
        print(f"{folder_items_config_path} doit contenir un objet JSON.")
        return {}
    except Exception:
        print(f"Config dossiers invalide dans {folder_items_config_path}, ignoree.")
        return {}


def read_root_folder_items_config(base_path: Path) -> Dict[str, Dict[str, Any]]:
    folder_items_config_path = base_path / FOLDER_ITEMS_CONFIG_FILE_NAME

    if not folder_items_config_path.exists():
        return {}

    try:
        raw = json.loads(folder_items_config_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return {
                str(key): value
                for key, value in raw.items()
                if isinstance(value, dict)
            }
        print(f"{folder_items_config_path} doit contenir un objet JSON.")
        return {}
    except Exception:
        print(f"Config dossiers invalide dans {folder_items_config_path}, ignoree.")
        return {}


def is_valid_file(file_path: Path) -> bool:
    if not file_path.is_file():
        return False
    if file_path.name in {CONFIG_FILE_NAME, ITEMS_CONFIG_FILE_NAME, FOLDER_ITEMS_CONFIG_FILE_NAME}:
        return False
    if is_excluded_name(file_path.name):
        return False
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    return True


def build_item(
    file_path: Path,
    view_name: str,
    item_config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    item_config = item_config or {}

    if bool(item_config.get("hidden", False)):
        return None

    shortcut_target = resolve_shortcut_target(file_path) if file_path.suffix.lower() == ".lnk" else None
    item_type = get_item_type(file_path, shortcut_target)
    target = get_target(file_path, shortcut_target)

    default_label = file_path.stem
    label = str(item_config.get("label") or default_label)
    item_id = safe_id(f"{view_name}-{label}")
    icon = str(item_config.get("icon") or detect_icon(label, file_path.suffix))
    order = normalize_order(item_config.get("order"), DEFAULT_ORDER)
    background_color = normalize_color_value(item_config)

    item: Dict[str, Any] = {
        "id": item_id,
        "type": item_type,
        "label": label,
        "icon": icon,
        "visible": True,
        "order": order,
    }

    if target:
        item["target"] = target

    if background_color:
        item["backgroundColor"] = background_color

    return item


def item_sort_key(item: Dict[str, Any]) -> Tuple[int, str]:
    return normalize_order(item.get("order"), DEFAULT_ORDER), str(item.get("label", "")).lower()


def build_folder_shortcut_item(
    item_name: str,
    view_name: str,
    item_config: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    item_config = item_config or {}

    if bool(item_config.get("hidden", False)):
        return None

    target = str(item_config.get("target") or "").strip()
    if not target:
        return None

    label = str(item_config.get("label") or item_name)
    icon = str(item_config.get("icon") or "📁")
    order = normalize_order(item_config.get("order"), DEFAULT_ORDER)
    background_color = normalize_color_value(item_config)

    item: Dict[str, Any] = {
        "id": safe_id(f"{view_name}-{label}"),
        "type": "folder",
        "label": label,
        "icon": icon,
        "visible": True,
        "order": order,
        "target": target,
    }

    if background_color:
        item["backgroundColor"] = background_color

    return item


def build_view(folder_path: Path, folder_config: Dict[str, Any], view_name: str) -> Dict[str, Any]:
    left_items: List[Dict[str, Any]] = []
    center_items: List[Dict[str, Any]] = []
    right_items: List[Dict[str, Any]] = static_right_section(view_name)

    items_config = read_items_config(folder_path)
    folder_items_config = read_folder_items_config(folder_path)

    base_items = [
        {
            "id": f"back-{view_name}",
            "type": "back",
            "label": folder_config["backLabel"],
            "icon": "↩️",
            "visible": True,
            "order": 0,
        },
        {
            "id": f"open-{view_name}",
            "type": "folder",
            "label": folder_config["openFolderLabel"],
            "icon": "📂",
            "target": str(get_folder_target(folder_path)),
            "visible": True,
            "order": 1,
        },
    ]

    generated_items: List[Dict[str, Any]] = []

    for child in folder_path.iterdir():
        if not is_valid_file(child):
            continue

        item_config = items_config.get(child.name, {})
        item = build_item(child, view_name, item_config=item_config)
        if item is None:
            continue

        generated_items.append(item)

    generated_items.sort(key=item_sort_key)

    target_section = center_items if folder_config["viewSection"] == "center" else left_items
    target_section.extend(base_items)
    target_section.extend(generated_items)

    extra_folder_items: Dict[str, List[Dict[str, Any]]] = {
        "left": [],
        "center": [],
        "right": [],
    }

    for item_name, item_config in folder_items_config.items():
        item = build_folder_shortcut_item(item_name, view_name, item_config=item_config)
        if item is None:
            continue

        section = normalize_section(str(item_config.get("section") or item_config.get("viewSection") or ""), "left")
        extra_folder_items[section].append(item)

    for section_name in ("left", "center", "right"):
        extra_folder_items[section_name].sort(key=item_sort_key)

    left_items.extend(extra_folder_items["left"])
    center_items.extend(extra_folder_items["center"])
    right_items.extend(extra_folder_items["right"])
    right_items.sort(key=item_sort_key)

    return {
        "left": left_items,
        "center": center_items,
        "right": right_items,
    }


def build_virtual_file_view(
    folder_items_config: Dict[str, Dict[str, Any]],
    folder_config: Dict[str, Any],
    view_name: str = "file",
) -> Dict[str, Any]:
    center_items: List[Dict[str, Any]] = [
        {
            "id": f"back-{view_name}",
            "type": "back",
            "label": folder_config["backLabel"],
            "icon": "↩️",
            "visible": True,
            "order": 0,
        }
    ]

    for item_name, item_config in folder_items_config.items():
        item = build_folder_shortcut_item(item_name, view_name, item_config=item_config)
        if item is None:
            continue

        center_items.append(item)

    center_items.sort(key=item_sort_key)

    view_data = {
        "left": [],
        "center": center_items,
        "right": [],
    }

    if folder_config.get("backgroundColor", "").strip():
        view_data["backgroundColor"] = folder_config["backgroundColor"].strip()

    return view_data


def folder_sort_key(folder_entry: Tuple[Path, Dict[str, Any]]) -> Tuple[int, str]:
    folder_path, folder_config = folder_entry
    return folder_config["order"], str(folder_config["label"] or folder_path.name).lower()


def apply_folder_style(item: Dict[str, Any], folder_config: Dict[str, Any]) -> Dict[str, Any]:
    background_color = folder_config.get("backgroundColor", "").strip()
    if background_color:
        item["backgroundColor"] = background_color
    return item


def generate_jzone(base_path: Path = BASE_PATH, output_file: Path = OUTPUT_FILE) -> Dict[str, Any]:
    views: Dict[str, Any] = {
        "main": {
            "left": [],
            "center": [],
            "right": static_right_section("main"),
        }
    }
    whattypes_config = read_whattypes_config(base_path)
    root_folder_items_config = read_root_folder_items_config(base_path)

    raw_folders = [
        p for p in base_path.iterdir()
        if p.is_dir()
        and p.name not in EXCLUDE_FOLDER_NAMES
        and not is_excluded_name(p.name)
    ]

    folder_entries: List[Tuple[Path, Dict[str, Any]]] = []
    for folder in raw_folders:
        folder_override = get_folder_override(whattypes_config, folder)
        folder_config = apply_folder_override(read_folder_config(folder), folder_override)
        if folder_config["hidden"]:
            continue
        folder_entries.append((folder, folder_config))

    folder_entries.sort(key=folder_sort_key)

    for folder, folder_config in folder_entries:
        folder_override = get_folder_override(whattypes_config, folder)
        entry_type = resolve_folder_entry_type(folder, folder_override)
        view_name = safe_id(get_folder_alias_name(folder))

        if entry_type == "folder":
            view_button: Dict[str, Any] = {
                "id": f"folder-{view_name}",
                "type": "folder",
                "label": folder_config["label"],
                "icon": folder_config["icon"],
                "target": str(folder_override.get("target") or get_folder_target(folder)),
                "visible": True,
                "order": folder_config["order"],
            }
        else:
            view_button = {
                "id": f"view-{view_name}",
                "type": "view",
                "label": folder_config["label"],
                "icon": folder_config["icon"],
                "targetView": view_name,
                "visible": True,
                "order": folder_config["order"],
            }

        view_button = apply_folder_style(view_button, folder_config)

        main_section = folder_config["mainSection"]
        views["main"][main_section].append(view_button)

        if entry_type == "folder":
            continue

        view_data = build_view(folder, folder_config, view_name)

        if folder_config.get("backgroundColor", "").strip():
            view_data["backgroundColor"] = folder_config["backgroundColor"].strip()

        views[view_name] = view_data

    if root_folder_items_config:
        file_override = whattypes_config.get("File") or whattypes_config.get("file") or {}
        file_folder_config = apply_folder_override(
            {
                "label": "File",
                "icon": "📁",
                "mainSection": "right",
                "viewSection": "center",
                "order": 100,
                "hidden": False,
                "openFolderLabel": "",
                "backLabel": "Retour",
                "backgroundColor": "#1f72cd",
            },
            file_override,
        )

        if not file_folder_config["hidden"]:
            view_button = apply_folder_style(
                {
                    "id": "view-file",
                    "type": "view",
                    "label": file_folder_config["label"],
                    "icon": file_folder_config["icon"],
                    "targetView": "file",
                    "visible": True,
                    "order": file_folder_config["order"],
                },
                file_folder_config,
            )
            views["main"][file_folder_config["mainSection"]].append(view_button)
            views["file"] = build_virtual_file_view(root_folder_items_config, file_folder_config, "file")

    for section_name in ("left", "center", "right"):
        views["main"][section_name].sort(key=item_sort_key)

    result = {
        "defaultView": "main",
        "views": views,
    }

    output_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return result


if __name__ == "__main__":
    generate_jzone()
    print(f"jzone.json genere avec succes : {OUTPUT_FILE}")
