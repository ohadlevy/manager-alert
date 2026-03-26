"""Hebrew to English city name mappings and region groupings for alert reports."""

# Regions for grouping in reports
NORTH = "Northern Israel"
HAIFA = "Haifa Area"
CENTRAL = "Central Israel"
JERUSALEM = "Jerusalem Area"
SOUTH = "Southern Israel"

# (English name, region) — region is used for grouping in reports
CITY_INFO: dict[str, tuple[str, str]] = {
    # Major cities — Central
    "תל אביב": ("Tel Aviv", CENTRAL),
    "תל אביב יפו": ("Tel Aviv", CENTRAL),
    "רמת גן": ("Ramat Gan", CENTRAL),
    "פתח תקווה": ("Petah Tikva", CENTRAL),
    "בני ברק": ("Bnei Brak", CENTRAL),
    "ראשון לציון": ("Rishon LeZion", CENTRAL),
    "חולון": ("Holon", CENTRAL),
    "בת ים": ("Bat Yam", CENTRAL),
    "הרצליה": ("Herzliya", CENTRAL),
    "רחובות": ("Rehovot", CENTRAL),
    "נתניה": ("Netanya", CENTRAL),
    "כפר סבא": ("Kfar Saba", CENTRAL),
    "רעננה": ("Ra'anana", CENTRAL),
    "הוד השרון": ("Hod HaSharon", CENTRAL),
    "לוד": ("Lod", CENTRAL),
    "רמלה": ("Ramla", CENTRAL),
    "מודיעין": ("Modi'in", CENTRAL),
    "נס ציונה": ("Nes Ziona", CENTRAL),
    "גבעתיים": ("Givatayim", CENTRAL),
    "קריית אונו": ("Kiryat Ono", CENTRAL),
    "אור יהודה": ("Or Yehuda", CENTRAL),
    "יהוד": ("Yehud", CENTRAL),
    "גבעת שמואל": ("Givat Shmuel", CENTRAL),
    "רמת השרון": ("Ramat HaSharon", CENTRAL),
    "אלעד": ("Elad", CENTRAL),
    "שוהם": ("Shoham", CENTRAL),
    "באר יעקב": ("Be'er Ya'akov", CENTRAL),
    "גדרה": ("Gedera", CENTRAL),
    "יבנה": ("Yavne", CENTRAL),
    "קריית עקרון": ("Kiryat Ekron", CENTRAL),
    "אבן יהודה": ("Even Yehuda", CENTRAL),
    "אזור": ("Azor", CENTRAL),
    "אשדוד": ("Ashdod", CENTRAL),

    # Jerusalem
    "ירושלים": ("Jerusalem", JERUSALEM),
    "בית שמש": ("Beit Shemesh", JERUSALEM),
    "מעלה אדומים": ("Ma'ale Adumim", JERUSALEM),
    "אריאל": ("Ariel", JERUSALEM),
    "גבעת שמשון": ("Givat Shimshon", JERUSALEM),

    # Haifa metro
    "חיפה": ("Haifa", HAIFA),
    "קריית אתא": ("Kiryat Ata", HAIFA),
    "קריית ביאליק": ("Kiryat Bialik", HAIFA),
    "קריית מוצקין": ("Kiryat Motzkin", HAIFA),
    "קריית ים": ("Kiryat Yam", HAIFA),
    "קריית חיים": ("Kiryat Haim", HAIFA),
    "נשר": ("Nesher", HAIFA),
    "טירת כרמל": ("Tirat Carmel", HAIFA),
    "חדרה": ("Hadera", HAIFA),
    "זכרון יעקב": ("Zikhron Ya'akov", HAIFA),
    "קיסריה": ("Caesarea", HAIFA),
    "אור עקיבא": ("Or Akiva", HAIFA),

    # North
    "נהריה": ("Nahariya", NORTH),
    "עכו": ("Acre", NORTH),
    "כרמיאל": ("Karmiel", NORTH),
    "מעלות תרשיחא": ("Ma'alot-Tarshiha", NORTH),
    "שלומי": ("Shlomi", NORTH),
    "קריית שמונה": ("Kiryat Shmona", NORTH),
    "צפת": ("Safed", NORTH),
    "טבריה": ("Tiberias", NORTH),
    "עפולה": ("Afula", NORTH),
    "נצרת": ("Nazareth", NORTH),
    "נצרת עילית": ("Nof HaGalil", NORTH),
    "נוף הגליל": ("Nof HaGalil", NORTH),
    "מגדל העמק": ("Migdal HaEmek", NORTH),
    "יוקנעם": ("Yokne'am", NORTH),
    "יוקנעם עילית": ("Yokne'am", NORTH),
    "יקנעם עילית": ("Yokne'am", NORTH),
    "ראש הנקרה": ("Rosh HaNikra", NORTH),

    # South
    "אשקלון": ("Ashkelon", SOUTH),
    "באר שבע": ("Be'er Sheva", SOUTH),
    "אופקים": ("Ofakim", SOUTH),
    "שדרות": ("Sderot", SOUTH),
    "נתיבות": ("Netivot", SOUTH),
    "קריית גת": ("Kiryat Gat", SOUTH),
    "קריית מלאכי": ("Kiryat Malakhi", SOUTH),
    "דימונה": ("Dimona", SOUTH),
    "ערד": ("Arad", SOUTH),
    "אילת": ("Eilat", SOUTH),
    "מצפה רמון": ("Mitzpe Ramon", SOUTH),
    "ירוחם": ("Yeruham", SOUTH),
}

# Build legacy flat dict for backwards compat
HEBREW_TO_ENGLISH: dict[str, str] = {k: v[0] for k, v in CITY_INFO.items()}


def to_english(hebrew_name: str) -> str | None:
    """Translate a Hebrew city name to English. Returns None if unknown."""
    return HEBREW_TO_ENGLISH.get(hebrew_name)


def get_region(hebrew_name: str) -> str | None:
    """Get the region for a Hebrew city name. Returns None if unknown."""
    info = CITY_INFO.get(hebrew_name)
    return info[1] if info else None


def is_known_city(hebrew_name: str) -> bool:
    """Check if a city is in our known cities list."""
    return hebrew_name in CITY_INFO


def format_city(hebrew_name: str) -> str:
    """Format a city name for display: 'English (Hebrew)' or just Hebrew if unknown."""
    english = to_english(hebrew_name)
    if english:
        return f"{english} ({hebrew_name})"
    return hebrew_name


def format_city_short(hebrew_name: str) -> str:
    """Format a city name for compact display: just English name, or Hebrew if unknown."""
    return to_english(hebrew_name) or hebrew_name
