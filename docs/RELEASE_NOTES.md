# v0.8.0 – Opt-in device turn-on settings

- Inspect advertised light capabilities without sending commands. A per-device button opens additional settings only where supported.
- Opt into brightness, effect or RGB color or color temperature, and transition. Unselected properties are omitted from the service call.
- Apply configured values once at turn-on, including when the light is already on. Saving changes during an active phase applies them once immediately. No repeated enforcement every 15 seconds or after restart.
- Revalidate current capabilities; unsupported settings show an error and do not prevent normal turn-off.
- Existing settings, lights and deferred cover requests remain compatible.

Automated tests use simulated HA/DOM interfaces. First real-device effect acceptance is pending. No preset is selected automatically. Separate scene/script/select startup actions are not included in this first part of #2. Update installation should follow completion of the current evening cover acceptance run.
