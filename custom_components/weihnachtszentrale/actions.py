"""Single read-only source for overview and rolling 24-hour action page."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from .preview import build_preview

UTC = timezone.utc


def build_actions(settings, now, timezone_name, solar_event):
    now_utc = now.astimezone(UTC)
    until = now_utc + timedelta(hours=24)
    tz = ZoneInfo(timezone_name)
    # A true 24h horizon may reach a third local date on spring DST transition.
    count = (until.astimezone(tz).date() - now.astimezone(tz).date()).days + 1
    preview = build_preview(settings, now, timezone_name, solar_event, days_count=max(2, count))
    groups = {}
    for device in preview['devices']:
        for window in device['effective_windows']:
            for key, action in (('start', 'on'), ('end', 'off')):
                instant = datetime.fromisoformat(window[key]).astimezone(UTC)
                if not now_utc <= instant < until:
                    continue
                group = groups.setdefault(instant, {'at': instant.astimezone(tz).isoformat(), 'on': [], 'off': []})
                group[action].append({'entity_id': device['entity_id'], 'name': device['name'], 'cover': device['cover']})
    actions = []
    for instant in sorted(groups):
        group = groups[instant]
        for key in ('on', 'off'):
            group[key].sort(key=lambda d: d['entity_id'])
        actions.append(group)
    warnings = []
    for day in preview['days']:
        warnings.extend(f"{day['date']}: {w}" for w in day['warnings'])
    return {'model_version': '0.7.2', 'read_only': True, 'generated_at': now.astimezone(tz).isoformat(),
            'until': until.astimezone(tz).isoformat(), 'actions': actions,
            'warnings': list(dict.fromkeys(warnings)), 'devices': preview['devices']}
