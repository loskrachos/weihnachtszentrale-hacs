"""Backend light control. No hard-coded entities and no cover service calls."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import asyncio
import json
import logging

from .preview import build_preview

_LOGGER = logging.getLogger(__name__)
UTC = timezone.utc


def targets(settings, now, timezone_name, solar_event):
    """Identify a phase by its boundaries, not by current reported light state.

    Including yesterday keeps an inactive phase stable across local midnight.
    Manual changes therefore remain in place until a relevant schedule boundary.
    """
    previous = build_preview(settings, now - timedelta(days=1), timezone_name, solar_event, days_count=3)
    instant = now.astimezone(UTC)
    result = {}
    for device in previous['devices']:
        config = next(d for d in settings['devices'] if d['entity_id'] == device['entity_id'])
        if not config['enabled']:
            continue
        windows = [(datetime.fromisoformat(w['start']).astimezone(UTC),
                    datetime.fromisoformat(w['end']).astimezone(UTC))
                   for w in device['effective_windows']]
        active = next(((a, b) for a, b in windows if a <= instant < b), None)
        # Next start / preceding end keeps the inactive phase stable at midnight.
        before = max((b for a, b in windows if b <= instant), default=None)
        after = min((a for a, b in windows if a > instant), default=None)
        boundary = active or (before, after)
        token = json.dumps([device['reason'], config['profile'],
                            [v.isoformat() if v else None for v in boundary]], sort_keys=True)
        result[device['entity_id']] = {'on': active is not None, 'token': token}
    return result


class LightEngine:
    """Serialize timer, saves and explicit activation; persist completed phases."""

    def __init__(self, hass, settings, store, solar_event, now):
        self.hass, self.settings, self.store = hass, settings, store
        self.solar_event, self.now = solar_event, now
        self.state = {'enabled': False, 'phases': {}}
        self.errors = {}
        self.history = []
        self.lock = asyncio.Lock()
        self.stopped = False
        self.last_checked = None
        self.covers = None

    async def load(self):
        saved = await self.store.async_load()
        if isinstance(saved, dict) and type(saved.get('enabled')) is bool and isinstance(saved.get('phases'), dict):
            self.state = saved

    def status(self):
        return {'enabled': self.state['enabled'], 'errors': deepcopy(self.errors),
                'history': deepcopy(self.history), 'last_checked': self.last_checked,
                'model_version': '0.7.0', 'covers': self.covers.status() if self.covers else {}}

    async def enable(self, enabled):
        async with self.lock:
            new_state = deepcopy(self.state)
            if enabled and not new_state['enabled']:
                # Explicitly enabling applies the current plan to participating lights.
                new_state['phases'] = {}
            new_state['enabled'] = enabled
            await self.store.async_save(new_state)
            self.state = new_state
            if enabled:
                await self._tick()

    async def tick(self, _now=None):
        if self.lock.locked():
            return  # Do not queue timer jobs while a device action/save is running.
        async with self.lock:
            await self._tick()

    async def stop(self):
        self.stopped = True
        async with self.lock:
            pass

    async def _tick(self):
        if self.stopped or not self.state['enabled']:
            return
        now = self.now()
        self.last_checked = now.isoformat()
        try:
            plan = targets(self.settings(), now, self.hass.config.time_zone, self.solar_event)
        except Exception as exc:
            self.errors['_schedule'] = str(exc)
            _LOGGER.exception('Weihnachtszentrale: Zeitplan konnte nicht berechnet werden')
            return
        self.errors.pop('_schedule', None)
        changed = False
        # Disabled/removed devices are released, never switched behind the user's back.
        for entity_id in set(self.state['phases']) | (set(self.errors) - {'_schedule'}):
            if entity_id not in plan:
                self.state['phases'].pop(entity_id, None)
                self.errors.pop(entity_id, None)
                changed = True
        for entity_id, target in plan.items():
            if self.stopped:
                break
            if self.state['phases'].get(entity_id) == target['token']:
                continue
            actual = self.hass.states.get(entity_id)
            if actual is None or actual.state in ('unknown', 'unavailable'):
                self.errors[entity_id] = 'Nicht erreichbar; erneuter Versuch alle 15 Sekunden.'
                continue
            desired = 'on' if target['on'] else 'off'
            try:
                if actual.state != desired:
                    await asyncio.wait_for(self.hass.services.async_call(
                        entity_id.split('.')[0], 'turn_' + desired,
                        {'entity_id': entity_id}, blocking=True), timeout=20)
                    self.history.append({'at': now.isoformat(), 'entity_id': entity_id,
                                         'action': desired, 'result': 'Befehl übergeben (keine Zustandsbestätigung)'})
                    self.history = self.history[-20:]
            except Exception as exc:
                if desired == 'off':
                    self.state.setdefault('off_releases', {})[entity_id] = now.isoformat()
                    changed = True
                self.errors[entity_id] = 'Schaltfehler: ' + str(exc)
                _LOGGER.warning('Weihnachtszentrale %s: %s', entity_id, exc)
                continue
            if desired == 'off':
                self.state.setdefault('off_releases', {})[entity_id] = now.isoformat()
            else:
                self.state.setdefault('off_releases', {}).pop(entity_id, None)
            # A successful call is not proof of physical switching. Do not repeatedly
            # override a manual change or an actuator without reliable feedback.
            self.state['phases'][entity_id] = target['token']
            self.errors.pop(entity_id, None)
            changed = True
        if changed:
            await self.store.async_save(self.state)
        if self.covers:
            await self.covers.process()
