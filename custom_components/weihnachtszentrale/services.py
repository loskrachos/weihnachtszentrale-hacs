"""Graphical automation actions for explicitly routed cover requests."""
import voluptuous as vol
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN

COVER = vol.Match(r'^cover\.[a-z0-9_]+$')


@callback
def async_setup_services(hass):
    async def request(call):
        runtime = hass.data.get(DOMAIN)
        if runtime is None:
            raise HomeAssistantError('Weihnachtszentrale ist nicht geladen')
        data = call.data
        if data.get('safety_script') and data['position'] != 0:
            raise HomeAssistantError('Sicherheitsskript nur für vollständiges Schließen verwenden')
        async with runtime['lock']:
            await runtime['covers'].request(data['cover_entity'], data['position'],
                                            data.get('safety_script', ''), data['source'])

    async def cancel(call):
        runtime = hass.data.get(DOMAIN)
        if runtime is None:
            raise HomeAssistantError('Weihnachtszentrale ist nicht geladen')
        async with runtime['lock']:
            await runtime['covers'].cancel(call.data['cover_entity'])

    hass.services.async_register(DOMAIN, 'request_cover_close', request, schema=vol.Schema({
        vol.Required('cover_entity'): COVER,
        vol.Optional('position', default=0): vol.All(int, vol.Range(min=0, max=100)),
        vol.Optional('safety_script'): vol.Match(r'^script\.[a-z0-9_]+$'),
        vol.Optional('source', default='Automation'): str,
    }))
    hass.services.async_register(DOMAIN, 'cancel_cover_close', cancel,
                                 schema=vol.Schema({vol.Required('cover_entity'): COVER}))
