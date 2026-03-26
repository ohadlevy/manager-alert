"""City region mappings for alert reports.

The oref API returns English city names directly (lang=en).
This module maps those names to regions for report grouping.
"""

# Regions for grouping in reports
NORTH = "Northern Israel"
HAIFA = "Haifa Area"
CENTRAL = "Central Israel"
JERUSALEM = "Jerusalem Area"
SOUTH = "Southern Israel"

# English city name → region
CITY_REGIONS: dict[str, str] = {
    # Central
    "Tel Aviv": CENTRAL,
    "Ramat Gan": CENTRAL,
    "Petah Tikva": CENTRAL,
    "Bnei Brak": CENTRAL,
    "Rishon LeZion": CENTRAL,
    "Holon": CENTRAL,
    "Bat Yam": CENTRAL,
    "Herzliya": CENTRAL,
    "Rehovot": CENTRAL,
    "Netanya": CENTRAL,
    "Kfar Saba": CENTRAL,
    "Ra'anana": CENTRAL,
    "Hod HaSharon": CENTRAL,
    "Lod": CENTRAL,
    "Ramla": CENTRAL,
    "Modi'in": CENTRAL,
    "Nes Ziona": CENTRAL,
    "Givatayim": CENTRAL,
    "Kiryat Ono": CENTRAL,
    "Or Yehuda": CENTRAL,
    "Yehud": CENTRAL,
    "Givat Shmuel": CENTRAL,
    "Ramat HaSharon": CENTRAL,
    "Elad": CENTRAL,
    "Shoham": CENTRAL,
    "Be'er Ya'akov": CENTRAL,
    "Gedera": CENTRAL,
    "Yavne": CENTRAL,
    "Kiryat Ekron": CENTRAL,
    "Even Yehuda": CENTRAL,
    "Azor": CENTRAL,
    "Ashdod": CENTRAL,

    # Jerusalem
    "Jerusalem": JERUSALEM,
    "Beit Shemesh": JERUSALEM,
    "Ma'ale Adumim": JERUSALEM,
    "Ariel": JERUSALEM,

    # Haifa metro
    "Haifa": HAIFA,
    "Hadera": HAIFA,
    "Kiryat Ata": HAIFA,
    "Kiryat Bialik": HAIFA,
    "Kiryat Motzkin": HAIFA,
    "Kiryat Yam": HAIFA,
    "Nesher": HAIFA,
    "Tirat Carmel": HAIFA,
    "Zikhron Ya'akov": HAIFA,
    "Caesarea": HAIFA,
    "Or Akiva": HAIFA,

    # North
    "Nahariya": NORTH,
    "Acre": NORTH,
    "Karmiel": NORTH,
    "Ma'alot-Tarshiha": NORTH,
    "Shlomi": NORTH,
    "Kiryat Shmona": NORTH,
    "Safed": NORTH,
    "Tiberias": NORTH,
    "Afula": NORTH,
    "Nazareth": NORTH,
    "Nof HaGalil": NORTH,
    "Migdal HaEmek": NORTH,
    "Yokne'am": NORTH,
    "Rosh HaNikra": NORTH,

    # South
    "Ashkelon": SOUTH,
    "Be'er Sheva": SOUTH,
    "Ofakim": SOUTH,
    "Sderot": SOUTH,
    "Netivot": SOUTH,
    "Kiryat Gat": SOUTH,
    "Kiryat Malakhi": SOUTH,
    "Dimona": SOUTH,
    "Arad": SOUTH,
    "Eilat": SOUTH,
    "Mitzpe Ramon": SOUTH,
    "Yeruham": SOUTH,
}

# Cities whose presence triggers "major cities" in severity
MAJOR_CITIES = {
    "Tel Aviv", "Jerusalem", "Haifa", "Be'er Sheva", "Ashdod", "Ashkelon",
    "Ramat Gan", "Petah Tikva", "Rishon LeZion", "Netanya", "Herzliya",
    "Ra'anana", "Kfar Saba", "Hod HaSharon",
}


def get_region(city_name: str) -> str | None:
    """Get the region for a city name. Returns None if unknown."""
    return CITY_REGIONS.get(city_name)


def is_known_city(city_name: str) -> bool:
    """Check if a city is in our known cities list."""
    return city_name in CITY_REGIONS
