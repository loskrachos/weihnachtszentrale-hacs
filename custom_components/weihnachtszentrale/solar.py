"""Use HA's existing Astral dependency and configured observer, with local dates."""
from zoneinfo import ZoneInfo

DEPRESSION = {"civil": 6, "nautical": 12, "astronomical": 18}


def make_solar_event(hass):
    from astral import Observer
    from astral import sun

    observer = Observer(hass.config.latitude, hass.config.longitude, hass.config.elevation)
    tz = ZoneInfo(hass.config.time_zone)

    def event_time(event, day, twilight):
        # Pass the local timezone so date means HA's calendar day worldwide.
        kwargs = {"tzinfo": tz}
        if event in ("dawn", "dusk"):
            kwargs["depression"] = DEPRESSION[twilight]
        try:
            return getattr(sun, event)(observer, date=day, **kwargs)
        except ValueError:
            return None

    return event_time
