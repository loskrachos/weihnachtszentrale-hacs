"""Opt-in evening close requests; never intercept or prevent manual movement."""
from copy import deepcopy
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
import asyncio
import re

UTC = timezone.utc


class CoverCoordinator:
    def __init__(self, hass, engine, store, now):
        self.hass, self.engine, self.store, self.now = hass, engine, store, now
        self.pending = {}
        self.history = []
        self.options = {'enabled': False, 'expiry': '06:00'}

    async def load(self):
        saved = await self.store.async_load()
        if isinstance(saved, dict):
            self.pending = saved.get('pending', {})
            self.options = self.validate_options(saved.get('options', self.options))
            for item in self.pending.values():
                if item['status'] == 'dispatching':
                    item['status'] = 'review'
                    item['message'] = 'Neustart während Befehlsübergabe; bitte prüfen, nicht automatisch wiederholt.'

    async def save(self):
        await self.store.async_save({'pending': self.pending, 'options': self.options})

    @staticmethod
    def validate_options(value):
        if (not isinstance(value, dict) or set(value) != {'enabled', 'expiry'}
            or type(value['enabled']) is not bool or not isinstance(value['expiry'], str)
            or not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value['expiry'])):
            raise ValueError('Rollladenoptionen benötigen Aktivierung und gültige Ablaufzeit HH:MM')
        return dict(value)

    async def update_options(self, value):
        previous = self.options
        self.options = self.validate_options(value)
        try:
            await self.save()
        except Exception:
            self.options = previous
            raise
        if not self.options['enabled']:
            for cover in list(self.pending):
                await self.cancel(cover, 'Rollladenkoordination deaktiviert; keine Fahrt')

    def status(self):
        return {'enabled': self.options['enabled'], 'pending': deepcopy(list(self.pending.values())), 'history': deepcopy(self.history[-10:])}

    def blockers(self, cover):
        if not self.options['enabled']:
            return []
        settings = self.engine.settings()
        if settings['season'] == 'off':
            return []
        result = []
        for d in settings['devices']:
            if (d['cover'] != cover or not d['enabled']
                or (settings['season'] == 'reduced' and d['season'] != 'both')):
                continue
            state = self.hass.states.get(d['entity_id'])
            if state is not None and state.state == 'off':
                continue
            # A sent OFF command releases a stale ON report. A later manual ON
            # overrides that release, using HA's state-change timestamp.
            released = self.engine.state.get('off_releases', {}).get(d['entity_id'])
            changed = getattr(state, 'last_changed', None)
            if released and (changed is None or changed <= datetime.fromisoformat(released)):
                continue
            result.append(d['entity_id'])
        return result

    async def request(self, cover, position=0, safety_script='', source='Automation'):
        """Caller and periodic engine share one lock; save before any movement."""
        now = self.now()
        tz = ZoneInfo(self.hass.config.time_zone)
        local = now.astimezone(tz)
        # Only the evening automation is routed here. Opening is never automated
        # by this integration. Expire at the next 06:00 to avoid a stale day close.
        hour, minute = map(int, self.options['expiry'].split(':'))
        expires = datetime.combine(local.date(), time(hour, minute), tz)
        if expires <= local:
            expires = datetime.combine(local.date() + timedelta(days=1), time(hour, minute), tz)
        actual = self.hass.states.get(cover)
        item = {'cover': cover, 'position': position, 'safety_script': safety_script,
                'source': source, 'created_at': now.isoformat(), 'expires_at': expires.isoformat(),
                'initial_position': getattr(actual, 'attributes', {}).get('current_position'),
                'status': 'waiting', 'message': '', 'blocked_by': []}
        self.pending[cover] = item
        await self.save()
        await self.process(only=cover, immediate=True)

    async def cancel(self, cover, reason='Anforderung verworfen'):
        if cover not in self.pending:
            return
        item = self.pending.pop(cover)
        self.history.append({'cover': cover, 'result': reason, 'at': self.now().isoformat()})
        self.history = self.history[-10:]
        await self.save()

    async def process(self, only=None, immediate=False):
        now = self.now()
        for cover in list(self.pending):
            if only is not None and cover != only:
                continue
            if self.engine.stopped:
                return
            if not self.options['enabled'] and not immediate:
                await self.cancel(cover, 'Rollladenkoordination deaktiviert; keine Fahrt')
                continue
            item = self.pending[cover]
            if now.astimezone(UTC) >= datetime.fromisoformat(item['expires_at']).astimezone(UTC):
                await self.cancel(cover, 'Abgelaufen; keine spätere Fahrt')
                continue
            if item['status'] != 'waiting':
                continue
            actual = self.hass.states.get(cover)
            current = getattr(actual, 'attributes', {}).get('current_position')
            # Only routed closes are held; opening is untouched. Pausing
            # suppresses queue replay; a NEW automatic request passes through.
            item['blocked_by'] = self.blockers(cover) if self.engine.state['enabled'] else []
            if item['blocked_by']:
                item['message'] = 'Wartet auf Licht-Aus'
                continue
            if not self.engine.state['enabled'] and not immediate:
                continue
            if actual is None or actual.state in ('unknown', 'unavailable'):
                item['message'] = 'Rollladen nicht erreichbar; wartet bis zur Gültigkeitsgrenze'
                continue
            # A close request must never open a more-closed cover to position 70.
            if actual.state == 'closed' or (current is not None and current <= item['position']):
                await self.cancel(cover, 'Ziel bereits erreicht oder weiter geschlossen; keine Fahrt')
                continue
            if item['position'] and current is None:
                item['status'] = 'review'
                item['message'] = 'Position unbekannt; Teilfahrt nicht sicher als Schließung bewertbar'
                await self.save()
                continue
            item['status'] = 'dispatching'
            item['message'] = 'Befehl wird übergeben'
            await self.save()
            try:
                if item['safety_script']:
                    response = await asyncio.wait_for(self.hass.services.async_call(
                        'script', item['safety_script'].split('.')[1], {},
                        blocking=True, return_response=True), timeout=100)
                    outcome = (response or {}).get('rollladen_ergebnis', response or {})
                    if outcome.get('status') != 'success':
                        item['status'] = 'review'
                        item['message'] = 'Sicherheitsskript: ' + str(outcome.get('status', 'Rückgabe unbekannt'))
                        await self.save()
                        continue
                else:
                    action = 'close_cover' if item['position'] == 0 else 'set_cover_position'
                    data = {'entity_id': cover}
                    if item['position']:
                        data['position'] = item['position']
                    await asyncio.wait_for(self.hass.services.async_call('cover', action, data, blocking=True), timeout=20)
            except Exception as exc:
                item['status'] = 'review'
                item['message'] = 'Fehler; vor erneutem Versuch prüfen: ' + str(exc)
                await self.save()
                continue
            await self.cancel(cover, 'Befehl übergeben; keine physische Zustandsbestätigung')
