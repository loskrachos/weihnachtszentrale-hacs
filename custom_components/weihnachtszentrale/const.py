"""Constants for the Christmas controller prototype."""
DOMAIN = "weihnachtszentrale"
VERSION = "0.7.0"
SIGNAL_SETTINGS_CHANGED = DOMAIN + '_settings_changed'
STORE_VERSION = 1
STORE_KEY = "weihnachtszentrale.settings"
DEFAULT_TIMES = {
    "morning_on": {"event": "fixed", "time": "06:30", "offset": 0},
    "morning_off": {"event": "sunrise", "time": "08:30", "offset": 30},
    "evening_on": {"event": "sunset", "time": "16:30", "offset": -30},
    "evening_off": {"event": "fixed", "time": "22:30", "offset": 0},
}
DEFAULT_SETTINGS = {"season": "off", "devices": [], "times": DEFAULT_TIMES}
