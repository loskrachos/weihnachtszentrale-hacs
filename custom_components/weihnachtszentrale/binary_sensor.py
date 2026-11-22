"""Expose the stored season to graphical HA automation conditions."""
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_SETTINGS_CHANGED


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ChristmasModeActive(hass)])


class ChristmasModeActive(BinarySensorEntity):
    _attr_name = 'Weihnachtszentrale | Weihnachtsmodus aktiv'
    _attr_unique_id = 'weihnachtszentrale_season_active'
    _attr_should_poll = False
    _attr_icon = 'mdi:string-lights'

    def __init__(self, hass):
        self.hass = hass

    @property
    def available(self):
        return DOMAIN in self.hass.data

    @property
    def is_on(self):
        runtime = self.hass.data.get(DOMAIN)
        return runtime['settings']['season'] != 'off' if runtime else None

    @property
    def extra_state_attributes(self):
        runtime = self.hass.data.get(DOMAIN)
        return {'season': runtime['settings']['season']} if runtime else {}

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self.async_on_remove(async_dispatcher_connect(
            self.hass, SIGNAL_SETTINGS_CHANGED, self._settings_changed))

    @callback
    def _settings_changed(self):
        self.async_write_ha_state()
