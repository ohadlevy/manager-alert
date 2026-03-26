"""Hebrew to English city name mappings for alert reports."""

# Major cities and common areas. Unknown cities stay in Hebrew.
HEBREW_TO_ENGLISH: dict[str, str] = {
    # Major cities
    "תל אביב": "Tel Aviv",
    "תל אביב יפו": "Tel Aviv",
    "ירושלים": "Jerusalem",
    "חיפה": "Haifa",
    "באר שבע": "Be'er Sheva",
    "אשדוד": "Ashdod",
    "אשקלון": "Ashkelon",
    "נתניה": "Netanya",
    "חולון": "Holon",
    "בת ים": "Bat Yam",
    "רמת גן": "Ramat Gan",
    "פתח תקווה": "Petah Tikva",
    "בני ברק": "Bnei Brak",
    "ראשון לציון": "Rishon LeZion",
    "רחובות": "Rehovot",
    "הרצליה": "Herzliya",
    "כפר סבא": "Kfar Saba",
    "רעננה": "Ra'anana",
    "הוד השרון": "Hod HaSharon",
    "לוד": "Lod",
    "רמלה": "Ramla",
    "מודיעין": "Modi'in",
    "נס ציונה": "Nes Ziona",
    "גבעתיים": "Givatayim",
    "קריית אונו": "Kiryat Ono",
    "אור יהודה": "Or Yehuda",
    "יהוד": "Yehud",
    "גבעת שמואל": "Givat Shmuel",

    # North
    "נהריה": "Nahariya",
    "עכו": "Acre",
    "כרמיאל": "Karmiel",
    "מעלות תרשיחא": "Ma'alot-Tarshiha",
    "שלומי": "Shlomi",
    "קריית שמונה": "Kiryat Shmona",
    "צפת": "Safed",
    "טבריה": "Tiberias",
    "עפולה": "Afula",
    "נצרת": "Nazareth",
    "נצרת עילית": "Nof HaGalil",
    "נוף הגליל": "Nof HaGalil",
    "מגדל העמק": "Migdal HaEmek",
    "יוקנעם": "Yokne'am",
    "יוקנעם עילית": "Yokne'am",
    "יקנעם עילית": "Yokne'am",
    "טירת כרמל": "Tirat Carmel",
    "חדרה": "Hadera",
    "זכרון יעקב": "Zikhron Ya'akov",
    "קיסריה": "Caesarea",
    "אור עקיבא": "Or Akiva",
    "ראש הנקרה": "Rosh HaNikra",

    # Haifa metro
    "קריית אתא": "Kiryat Ata",
    "קריית ביאליק": "Kiryat Bialik",
    "קריית מוצקין": "Kiryat Motzkin",
    "קריית ים": "Kiryat Yam",
    "קריית חיים": "Kiryat Haim",
    "נשר": "Nesher",

    # South
    "אופקים": "Ofakim",
    "שדרות": "Sderot",
    "נתיבות": "Netivot",
    "קריית גת": "Kiryat Gat",
    "קריית מלאכי": "Kiryat Malakhi",
    "דימונה": "Dimona",
    "ערד": "Arad",
    "אילת": "Eilat",
    "מצפה רמון": "Mitzpe Ramon",
    "ירוחם": "Yeruham",

    # Central
    "רמת השרון": "Ramat HaSharon",
    "גבעת שמשון": "Givat Shimshon",
    "אלעד": "Elad",
    "שוהם": "Shoham",
    "באר יעקב": "Be'er Ya'akov",
    "גדרה": "Gedera",
    "יבנה": "Yavne",
    "קריית עקרון": "Kiryat Ekron",
    "אבן יהודה": "Even Yehuda",
    "אריאל": "Ariel",

    # Common compound areas (industrial zones etc.)
    "אזור": "Azor",
    "אזור תעשייה": "Industrial Zone",
}


def to_english(hebrew_name: str) -> str | None:
    """Translate a Hebrew city name to English. Returns None if unknown."""
    return HEBREW_TO_ENGLISH.get(hebrew_name)


def format_city(hebrew_name: str) -> str:
    """Format a city name for display: 'English (Hebrew)' or just Hebrew if unknown."""
    english = to_english(hebrew_name)
    if english:
        return f"{english} ({hebrew_name})"
    return hebrew_name
