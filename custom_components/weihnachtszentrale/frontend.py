"""Serve and register the card shipped inside the integration directory."""
from pathlib import Path
from urllib.parse import urlsplit

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace import LOVELACE_DATA
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, VERSION

PREFIX = '/weihnachtszentrale'
CARD = 'weihnachtszentrale-card-v' + VERSION.replace('.', '') + '.js'
RESOURCE_URL = PREFIX + '/' + CARD


def owned_resource(url):
    """Only replace this integration's known URLs, never other resources."""
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme or parsed.netloc:
        return False
    path = parsed.path
    if path == '/local/weihnachtszentrale-card.js':
        return True
    for prefix in ('/local/weihnachtszentrale-card-v', PREFIX + '/weihnachtszentrale-card-v'):
        if path.startswith(prefix) and path.endswith('.js'):
            return path[len(prefix):-3].isdigit()
    return False


async def async_setup_frontend(hass):
    """Keep exactly one module resource and migrate the old /local resource."""
    marker = DOMAIN + '_static_registered'
    if not hass.data.get(marker):
        await hass.http.async_register_static_paths([
            StaticPathConfig(PREFIX, str(Path(__file__).parent / 'frontend'), False)])
        hass.data[marker] = True
    lovelace = hass.data[LOVELACE_DATA]
    if lovelace.resource_mode != 'storage':
        raise HomeAssistantError('Automatische Kartenregistrierung benötigt Dashboard-Ressourcen im Speichermodus')
    resources = lovelace.resources
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True
    matches = [item for item in resources.async_items() if owned_resource(item.get('url', ''))]
    if matches:
        first = matches[0]
        if first['url'] != RESOURCE_URL or first.get('type') != 'module':
            await resources.async_update_item(first['id'], {'url': RESOURCE_URL, 'res_type': 'module'})
        for extra in matches[1:]:
            await resources.async_delete_item(extra['id'])
    else:
        await resources.async_create_item({'url': RESOURCE_URL, 'res_type': 'module'})
