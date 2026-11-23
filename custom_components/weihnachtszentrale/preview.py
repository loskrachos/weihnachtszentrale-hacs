"""Pure, read-only time model. All interval comparisons use UTC instants."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KEYS = ("morning_on", "morning_off", "evening_on", "evening_off")
PERIODS = ("morning", "evening")
UTC = timezone.utc


def merge_windows(windows):
    """Union of overlapping or touching half-open UTC intervals."""
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def build_preview(settings, now, timezone_name, solar_event, days_count=2):
    """Preview regular windows within each of two local calendar days.

    solar_event(event, local_date, twilight) returns aware datetime or None.
    A reversed pair is invalid. Only future party logic may extend across midnight.
    Equal endpoints are invalid, rather than an implicit 24-hour schedule.
    """
    tz = ZoneInfo(timezone_name)
    now_utc = now.astimezone(UTC)
    today = now.astimezone(tz).date()
    horizon_start = datetime.combine(today, datetime.min.time(), tz).astimezone(UTC)
    horizon_end = datetime.combine(today + timedelta(days=days_count), datetime.min.time(), tz).astimezone(UTC)
    cache = {}

    def resolve(key, day):
        if (key, day) in cache:
            return cache[key, day]
        rule = settings["times"][key]
        instant, warning = None, None
        if rule["event"] == "fixed":
            hour, minute = map(int, rule["time"].split(":"))
            local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
            instant = local.astimezone(UTC)
            if instant.astimezone(tz).replace(tzinfo=None) != local.replace(tzinfo=None):
                warning = "Diese Uhrzeit existiert wegen der Zeitumstellung nicht."
                instant = None
            elif local.utcoffset() != local.replace(fold=1).utcoffset():
                warning = "Doppelte Uhrzeit bei Zeitumstellung: erstes Vorkommen verwendet."
        else:
            base = solar_event(rule["event"], day, rule.get("twilight", "civil"))
            if base is None:
                warning = "Sonnenereignis tritt an diesem Tag am HA-Standort nicht ein."
            else:
                instant = base.astimezone(UTC) + timedelta(minutes=rule["offset"])
        cache[key, day] = instant, warning
        return instant, warning

    def iso(instant):
        return instant.astimezone(tz).isoformat() if instant is not None else None

    def window(period, day):
        start, start_warning = resolve(period + "_on", day)
        end, end_warning = resolve(period + "_off", day)
        warnings = [x for x in (start_warning, end_warning) if x]
        if start is None or end is None:
            return None, warnings
        if start.astimezone(tz).date() != day or end.astimezone(tz).date() != day:
            return None, warnings + ["Reguläre Zeitfenster müssen innerhalb desselben Kalendertags liegen; Offset prüfen. Nur der Partymodus darf über Mitternacht verlängern."]
        if end <= start:
            return None, warnings + ["Ende muss nach Start am selben Tag liegen. Nur der Partymodus darf über Mitternacht verlängern."]
        if period == "evening":
            morning_end, _ = resolve("morning_off", day)
            if morning_end is None:
                return None, warnings + ["Morgen aus ist nicht berechenbar; Reihenfolge zum Abendfenster kann nicht geprüft werden."]
            if start <= morning_end:
                return None, warnings + ["Abend an muss nach Morgen aus liegen; tagsüber muss eine Pause bleiben. Abendfenster wird nicht verwendet."]
        return (start, end), warnings

    days = []
    intervals = {p: [] for p in PERIODS}
    lookback_warnings = []
    for delta in range(days_count):
        day = today + timedelta(days=delta)
        windows, warnings = [], []
        for period in PERIODS:
            pair, issues = window(period, day)
            warnings.extend(f"{period}: {issue}" for issue in issues)
            if pair is not None and pair[1] > horizon_start and pair[0] < horizon_end:
                intervals[period].append(pair)
            if pair is not None:
                windows.append({"profile": period, "start": iso(pair[0]), "end": iso(pair[1])})
        if 0 <= delta < days_count:
            rules = []
            for key in KEYS:
                instant, warning = resolve(key, day)
                rules.append({"key": key, "event": settings["times"][key]["event"],
                              "twilight": settings["times"][key].get("twilight", "civil"),
                              "at": iso(instant), "warning": warning})
            days.append({"date": day.isoformat(), "rules": rules,
                         "windows": windows, "warnings": list(dict.fromkeys(warnings))})
        elif delta < 0 and warnings:
            lookback_warnings.extend(f"{day.isoformat()} {w}" for w in warnings)

    devices = []
    for device in settings["devices"]:
        if not device["enabled"]:
            reason = "Teilnahme deaktiviert"
        elif settings["season"] == "off":
            reason = "Weihnachtsmodus aus"
        elif settings["season"] == "reduced" and device["season"] != "both":
            reason = "Nur im Vollbetrieb"
        else:
            reason = None
        periods = PERIODS if device["profile"] == "both" else (device["profile"],)
        effective = merge_windows([pair for p in periods for pair in intervals[p]]) if reason is None else []
        devices.append({"entity_id": device["entity_id"], "name": device["name"],
                        "eligible": reason is None, "reason": reason,
                        "profile": device["profile"], "cover": device["cover"],
                        "scheduled_on": any(a <= now_utc < b for a, b in effective),
                        "effective_windows": [{"start": iso(a), "end": iso(b)} for a, b in effective]})
    return {"generated_at": iso(now_utc), "timezone": timezone_name, "days": days,
            "devices": devices, "read_only": True,
            "warnings": list(dict.fromkeys(lookback_warnings)), "model_version": "0.8.0"}
