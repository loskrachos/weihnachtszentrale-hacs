"""Explicit opt-in light turn-on values; no manufacturer-specific behavior."""
from copy import deepcopy

BRIGHTNESS_MODES = {'brightness', 'color_temp', 'hs', 'xy', 'rgb', 'rgbw', 'rgbww', 'white'}
COLOR_MODES = {'hs', 'xy', 'rgb', 'rgbw', 'rgbww'}


def validate_turn_on(value, entity_id):
    if not isinstance(value, dict) or set(value) - {'brightness_pct', 'effect', 'rgb_color', 'color_temp_kelvin', 'transition'}:
        raise ValueError('Ungültige Einschalteinstellungen')
    if value and not entity_id.startswith('light.'):
        raise ValueError('Zusätzliche Lichtwerte nur für Lichtentitäten')
    if sum(key in value for key in ('effect', 'rgb_color', 'color_temp_kelvin')) > 1:
        raise ValueError('Effekt, Farbe und Farbtemperatur alternativ auswählen')
    for key, low, high in (('brightness_pct',1,100),('color_temp_kelvin',1000,40000),('transition',0,300)):
        if key in value and (type(value[key]) is not int or not low <= value[key] <= high):
            raise ValueError('Ungültiger Wert: ' + key)
    if 'effect' in value and (not isinstance(value['effect'],str) or not value['effect'] or len(value['effect'])>200):
        raise ValueError('Ungültiger Effekt')
    if 'rgb_color' in value and (not isinstance(value['rgb_color'],list) or len(value['rgb_color']) != 3
        or any(type(v) is not int or not 0 <= v <= 255 for v in value['rgb_color'])):
        raise ValueError('Ungültige RGB-Farbe')
    return deepcopy(value)


def supported_turn_on(value, entity_id, state):
    """Recheck current HA capabilities before applying explicitly selected values."""
    data = validate_turn_on(value, entity_id)
    if not data:
        return data
    attrs = getattr(state, 'attributes', {}) or {}
    modes = set(attrs.get('supported_color_modes') or [])
    if 'brightness_pct' in data and not modes & BRIGHTNESS_MODES:
        raise ValueError('Helligkeit wird nicht mehr angeboten; Einstellungen prüfen')
    if 'rgb_color' in data and not modes & COLOR_MODES:
        raise ValueError('Farbe wird nicht mehr angeboten; Einstellungen prüfen')
    if 'effect' in data and (not (attrs.get('supported_features',0) & 4) or data['effect'] not in (attrs.get('effect_list') or [])):
        raise ValueError('Effekt wird nicht mehr angeboten; Einstellungen prüfen')
    if 'color_temp_kelvin' in data:
        low, high = attrs.get('min_color_temp_kelvin'), attrs.get('max_color_temp_kelvin')
        if 'color_temp' not in modes or not isinstance(low,(int,float)) or not isinstance(high,(int,float)) or not low <= data['color_temp_kelvin'] <= high:
            raise ValueError('Farbtemperatur wird nicht mehr angeboten; Einstellungen prüfen')
    if 'transition' in data and not (attrs.get('supported_features',0) & 32):
        raise ValueError('Übergangszeit wird nicht mehr angeboten; Einstellungen prüfen')
    return data
