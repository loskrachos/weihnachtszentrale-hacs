"""Configuration and explicitly enabled backend light control."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import re
import uuid

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.helpers.dispatcher import async_dispatcher_send
from datetime import timedelta

from .preview import build_preview
from .actions import build_actions
from .solar import make_solar_event
from .engine import LightEngine
from .covers import CoverCoordinator
from .services import async_setup_services
from .frontend import async_setup_frontend
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STORE_VERSION, STORE_KEY, DEFAULT_SETTINGS, SIGNAL_SETTINGS_CHANGED

_ENTITY = re.compile(r"^(switch|light)\.[a-z0-9_]+$")
_COVER = re.compile(r"^cover\.[a-z0-9_]+$")
_TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_EVENTS = ("fixed", "sunrise", "sunset", "dawn", "dusk")
_KEYS = ("morning_on", "morning_off", "evening_on", "evening_off")
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def validate_settings(value: dict) -> dict:
    """Accept only the planned schema; reject invalid/duplicate entity references."""
    if not isinstance(value, dict) or set(value) != {"season", "devices", "times"}:
        raise vol.Invalid("Invalid settings structure")
    if value["season"] not in ("off", "reduced", "full"):
        raise vol.Invalid("Invalid season")
    devices = value["devices"]
    if not isinstance(devices, list) or len(devices) > 30:
        raise vol.Invalid("Expected up to 30 devices")
    seen = set()
    clean = []
    for d in devices:
        if not isinstance(d, dict) or (not {"id", "entity_id", "name", "enabled", "season", "profile", "cover"} <= set(d) or set(d) - {"id", "entity_id", "name", "enabled", "season", "profile", "cover", "no_feedback"}):
            raise vol.Invalid("Invalid device entry")
        entity_id = d["entity_id"]
        if not isinstance(entity_id, str) or not _ENTITY.fullmatch(entity_id) or entity_id in seen:
            raise vol.Invalid("Invalid or duplicate switch/light entity")
        seen.add(entity_id)
        cover = d["cover"]
        if not isinstance(cover, str) or (cover and not _COVER.fullmatch(cover)):
            raise vol.Invalid("Invalid cover entity")
        if (not isinstance(d["id"], str) or len(d["id"]) > 100
            or not isinstance(d["name"], str) or len(d["name"]) > 100
            or type(d["enabled"]) is not bool
            or type(d.get("no_feedback", False)) is not bool
            or d["season"] not in ("full", "both")
            or d["profile"] not in ("morning", "evening", "both")):
            raise vol.Invalid("Invalid device fields")
        clean.append(dict(d))
    times = value["times"]
    if not isinstance(times, dict) or set(times) != set(_KEYS):
        raise vol.Invalid("Invalid time keys")
    normalized = {}
    for key in _KEYS:
        t = times[key]
        if not isinstance(t, dict) or (not {"event", "time", "offset"} <= set(t) or set(t) - {"event", "time", "offset", "twilight"}):
            raise vol.Invalid("Invalid time rule")
        if t["event"] not in _EVENTS or not isinstance(t["time"], str) or not _TIME.fullmatch(t["time"]):
            raise vol.Invalid("Invalid time/event")
        if type(t["offset"]) is not int or not -180 <= t["offset"] <= 180:
            raise vol.Invalid("Invalid offset")
        if t.get("twilight", "civil") not in ("civil", "nautical", "astronomical"):
            raise vol.Invalid("Invalid twilight type")
        normalized[key] = {**t, "twilight": t.get("twilight", "civil")}
    return {"season": value["season"], "devices": clean, "times": normalized}


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register commands once; actual config entry loads settings."""
    await async_setup_frontend(hass)
    websocket_api.async_register_command(hass, ws_get)
    websocket_api.async_register_command(hass, ws_save)
    websocket_api.async_register_command(hass, ws_preview)
    websocket_api.async_register_command(hass, ws_actions)
    websocket_api.async_register_command(hass, ws_engine)
    websocket_api.async_register_command(hass, ws_enable)
    websocket_api.async_register_command(hass, ws_cover_options)
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store(hass, STORE_VERSION, STORE_KEY)
    saved = await store.async_load()
    settings = validate_settings(deepcopy(DEFAULT_SETTINGS))
    if saved is not None:
        settings = validate_settings(saved)
    hass.data[DOMAIN] = {"store": store, "settings": settings, "lock": asyncio.Lock()}
    runtime = hass.data[DOMAIN]
    engine = LightEngine(hass, lambda: runtime['settings'],
                         Store(hass, 1, DOMAIN + '.runtime'), make_solar_event(hass), dt_util.now)
    await engine.load()
    runtime['engine'] = engine
    runtime['lock'] = engine.lock
    covers = CoverCoordinator(hass, engine, Store(hass, 1, DOMAIN + '.covers'), dt_util.now)
    await covers.load()
    runtime['covers'] = engine.covers = covers
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.BINARY_SENSOR])
    async def manual_cover_call(event):
        # Observe manual UI calls only to discard stale pending requests. This
        # never blocks, changes or intercepts the manual cover action itself.
        if not getattr(event.context, 'user_id', None):
            return
        data = event.data
        if data.get('domain') != 'cover' or data.get('service') not in ('open_cover', 'close_cover', 'set_cover_position', 'stop_cover', 'toggle'):
            return
        selected = data.get('service_data', {}).get('entity_id')
        selected = [selected] if isinstance(selected, str) else selected
        if not selected or 'all' in selected:
            selected = list(covers.pending)
        async with engine.lock:
            for entity_id in selected:
                await covers.cancel(entity_id, 'Manuelle Rollladenbedienung; Anforderung verworfen')
    runtime['cancel_manual'] = hass.bus.async_listen('call_service', manual_cover_call)
    async def periodic(_now):
        if hass.is_running:
            await engine.tick()
    runtime['cancel_timer'] = async_track_time_interval(hass, periodic, timedelta(seconds=15))
    async def started(_event):
        await engine.tick()
    if hass.is_running:
        await engine.tick()
    else:
        runtime['cancel_start'] = hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = hass.data.get(DOMAIN)
    if runtime:
        if not await hass.config_entries.async_unload_platforms(entry, [Platform.BINARY_SENSOR]):
            return False
        runtime['cancel_timer']()
        runtime['cancel_manual']()
        if 'cancel_start' in runtime:
            runtime['cancel_start']()
        await runtime['engine'].stop()
        hass.data.pop(DOMAIN, None)
    return True


@websocket_api.websocket_command({vol.Required("type"): "weihnachtszentrale/get"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_get(hass, connection, msg):
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Integration not configured")
        return
    connection.send_result(msg["id"], deepcopy(runtime["settings"]))


@websocket_api.websocket_command({vol.Required("type"): "weihnachtszentrale/save", vol.Required("settings"): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_save(hass, connection, msg):
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg["id"], "not_loaded", "Integration not configured")
        return
    try:
        settings = validate_settings(msg["settings"])
    except (vol.Invalid, TypeError, ValueError) as exc:
        connection.send_error(msg["id"], "invalid_settings", str(exc))
        return
    async with runtime["lock"]:
        await runtime["store"].async_save(settings)
        runtime["settings"] = settings
        async_dispatcher_send(hass, SIGNAL_SETTINGS_CHANGED)
        if 'engine' in runtime:
            await runtime['engine']._tick()
    connection.send_result(msg["id"], {"saved": True})


@websocket_api.websocket_command({vol.Required("type"): "weihnachtszentrale/preview", vol.Required("settings"): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_preview(hass, connection, msg):
    """Preview current form values without saving or switching anything."""
    if DOMAIN not in hass.data:
        connection.send_error(msg["id"], "not_loaded", "Integration not configured")
        return
    try:
        settings = validate_settings(msg["settings"])
        result = build_preview(
            settings, dt_util.now(), hass.config.time_zone,
            make_solar_event(hass),
        )
    except (vol.Invalid, TypeError, ValueError) as exc:
        connection.send_error(msg["id"], "invalid_settings", str(exc))
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required('type'): 'weihnachtszentrale/engine'})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_engine(hass, connection, msg):
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg['id'], 'not_loaded', 'Integration not configured')
        return
    connection.send_result(msg['id'], runtime['engine'].status())


@websocket_api.websocket_command({vol.Required('type'): 'weihnachtszentrale/cover_options', vol.Optional('options'): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_cover_options(hass, connection, msg):
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg['id'], 'not_loaded', 'Integration not configured')
        return
    if 'options' in msg:
        try:
            async with runtime['lock']:
                await runtime['covers'].update_options(msg['options'])
        except ValueError as exc:
            connection.send_error(msg['id'], 'invalid_settings', str(exc))
            return
    connection.send_result(msg['id'], {'options': deepcopy(runtime['covers'].options)})


@websocket_api.websocket_command({vol.Required('type'): 'weihnachtszentrale/enable', vol.Required('enabled'): bool})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_enable(hass, connection, msg):
    runtime = hass.data.get(DOMAIN)
    if runtime is None:
        connection.send_error(msg['id'], 'not_loaded', 'Integration not configured')
        return
    await runtime['engine'].enable(msg['enabled'])
    connection.send_result(msg['id'], runtime['engine'].status())


@websocket_api.websocket_command({vol.Required("type"): "weihnachtszentrale/actions", vol.Required("settings"): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_actions(hass, connection, msg):
    """Read-only rolling action preview; never calls device services."""
    if DOMAIN not in hass.data:
        connection.send_error(msg["id"], "not_loaded", "Integration not configured")
        return
    try:
        settings = validate_settings(msg["settings"])
        result = build_actions(settings, dt_util.now(), hass.config.time_zone, make_solar_event(hass))
    except (vol.Invalid, TypeError, ValueError) as exc:
        connection.send_error(msg["id"], "invalid_settings", str(exc))
        return
    connection.send_result(msg["id"], result)
