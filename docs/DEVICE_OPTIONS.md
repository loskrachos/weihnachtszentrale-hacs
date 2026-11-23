# Per-device turn-on settings

Device capabilities are inspected from Home Assistant state attributes without sending device commands. After adding a supported light, “Weitere Einstellmöglichkeiten vorhanden” opens an optional editor. Select only the properties Christmas Central should control. Supported fields: brightness, one of effect/RGB color/color temperature, and transition if advertised by the entity. Switches and on/off-only lights keep the simple interface.

Changing a value is a draft until “Einstellungen speichern”. With the automation enabled and the light in its active scheduled phase, saving applies the selected values once immediately. Subsequent ticks and restarts do not repeatedly reset them. On an inactive phase only the next turn-on uses the new values. Turn-off always remains a plain turn_off request.

Only opted-in fields are included in the light.turn_on call. Home Assistant or the device can still apply its own defaults to other attributes. Effect and static color settings are alternatives to avoid incompatible commands. Existing participant configurations need no migration. No effect or scene is chosen automatically.

Capabilities are revalidated before each new turn-on command. Removed effects or unsupported values become a visible error; turn-off remains available. Edit or clear the stored values to resolve the error. If a light exposes too little information while off, inspect again when its HA attributes become available.

Limits: only entity capabilities advertised through HA are discovered. Separate scene, select or script entities cannot reliably be assigned to a light automatically; selecting such alternative startup actions remains a later part of issue #2. The current Govee example exposes its presets through effect_list and needs no vendor-specific code. Saved targets still use normal light/switch entities. No arbitrary service data is accepted.
