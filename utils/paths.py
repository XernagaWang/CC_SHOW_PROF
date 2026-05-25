"""Canonical paths for the SHOW dashboard module."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
LOGBOOKS_DIR = DATA_DIR / "logbooks"
REFERENCE_DIR = DATA_DIR / "reference"
GEOCODED_DIR = DATA_DIR / "geocoded"

LOGBOOK_APP_CSV = DATA_DIR / "logbook_app_data.csv"
STATION_ID_MAP_CSV = DATA_DIR / "station_id_map.csv"
ENRICHED_CSV = REFERENCE_DIR / "master_logbook_enriched.csv"
CPO_ALIASES_CSV = REFERENCE_DIR / "cpo_brand_aliases_with_pinyin.csv"

ASSETS_DIR = PROJECT_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"

ARCHIVE_DIR = PROJECT_ROOT / "archive"
CHARGING_LIST_DEMO_ARCHIVE = ARCHIVE_DIR / "charging_list_demo"
