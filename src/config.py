"""Configuration helpers for the embedded telemetry toolkit."""

DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FORMAT = "%Y-%m-%d %H:%M:%S"


# Onceden tanimli baslangic konumlari (saha denemelerinde sik kullanilan noktalar)
# (lat, lon) - WGS84
LOCATIONS = {
    "istanbul_kilyos": {
        "label": "Istanbul - Kilyos sahili",
        "lat": 41.2486,
        "lon": 29.0420,
        # Acik kiyi alani; UAV deneme ucuslari icin uygun
    },
    "istanbul_ataturk": {
        "label": "Istanbul - eski Ataturk Havalimani cevresi",
        "lat": 40.9769,
        "lon": 28.8146,
        # TEKNOFEST etkinlik sahasi olarak biliniyor
    },
    "istanbul_sabiha": {
        "label": "Istanbul - Sabiha Gokcen perimetresi",
        "lat": 40.8986,
        "lon": 29.3092,
    },
    "ankara_etimesgut": {
        "label": "Ankara - Etimesgut civari",
        "lat": 39.9505,
        "lon": 32.6868,
    },
    "san_francisco": {
        "label": "San Francisco - SFO civari (eski varsayilan)",
        "lat": 37.6188,
        "lon": -122.3754,
    },
}

DEFAULT_LOCATION_KEY = "istanbul_kilyos"


def get_default_config():
    """Return a placeholder default configuration mapping."""
    return {
        "log_dir": DEFAULT_LOG_DIR,
        "log_format": DEFAULT_LOG_FORMAT,
        "location": DEFAULT_LOCATION_KEY,
    }


def get_location(key: str = DEFAULT_LOCATION_KEY) -> dict:
    """Bilinmeyen anahtar gelirse sessizce varsayilana dus."""
    return LOCATIONS.get(key, LOCATIONS[DEFAULT_LOCATION_KEY])
