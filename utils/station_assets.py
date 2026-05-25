"""Station photos under assets/images/{station_id}/."""
from pathlib import Path
from typing import Dict, Optional

from utils.paths import IMAGES_DIR

PHOTO_SLOTS = ("pile_left", "pile_right", "gun", "plate")
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".heic", ".heif")


def get_images_root() -> Path:
    return IMAGES_DIR


def _is_heif_or_live_photo_container(path: Path) -> bool:
    """iPhone HEIC / Live Photo (ISO BMFF). Often saved with a .png extension."""
    try:
        header = path.read_bytes()[:32]
    except OSError:
        return True
    if len(header) < 12 or header[4:8] != b"ftyp":
        return False
    brands = header[8:32].lower()
    return any(tag in brands for tag in (b"heic", b"heif", b"mif1", b"msf1", b"avif"))


def is_displayable_image(path: Path) -> bool:
    """True only for standard web images (PNG/JPEG/GIF/WEBP). Skips HEIC / Live Photo."""
    if not path.is_file() or path.stat().st_size < 32:
        return False
    if _is_heif_or_live_photo_container(path):
        return False
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.load()
        return im.format in ("PNG", "JPEG", "GIF", "WEBP")
    except Exception:
        return False


def _station_folder(station_id: str) -> Optional[Path]:
    if not station_id or str(station_id).strip() in ("—", "N/A", "nan"):
        return None
    folder = IMAGES_DIR / str(station_id).strip()
    return folder if folder.is_dir() else None


def _match_basename(folder: Path, basename: str) -> Optional[Path]:
    target = basename.lower()
    try:
        for entry in folder.iterdir():
            if not entry.is_file():
                continue
            if entry.stem.lower() == target and entry.suffix.lower() in _IMAGE_EXTENSIONS:
                return entry
    except OSError:
        return None
    return None


def get_station_photo_paths(station_id: str) -> Dict[str, Optional[Path]]:
    photos: Dict[str, Optional[Path]] = {key: None for key in PHOTO_SLOTS}
    folder = _station_folder(station_id)
    if folder is None:
        return photos

    meta_path = folder / "meta.json"
    meta_photos = {}
    if meta_path.is_file():
        try:
            import json

            with meta_path.open(encoding="utf-8") as handle:
                meta_photos = json.load(handle).get("photos") or {}
        except (json.JSONDecodeError, OSError):
            meta_photos = {}

    for slot in PHOTO_SLOTS:
        if slot in meta_photos:
            candidate = folder / meta_photos[slot]
            if candidate.is_file():
                photos[slot] = candidate
                continue
        photos[slot] = _match_basename(folder, slot)

    return photos
