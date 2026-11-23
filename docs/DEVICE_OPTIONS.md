# Per-device turn-on settings

## Configuration pages

“Zeiten” contains central morning/evening rules and the preview. “Geräte” contains participants, cover assignments and additional light values. Drafts survive switching between these internal pages. “Zeiten speichern” and “Geräteeinstellungen speichern” affect only their own section. Use the overview to change the Christmas season. Cover options retain their separate save button.

## Select fields, then set values

After adding and saving a light, advertised HA capabilities are inspected automatically. The optional “Weitere Einstellmöglichkeiten vorhanden” button opens a labeled checklist. Select brightness, transition, or one of effect/RGB/color temperature and press “Feldauswahl speichern”. This saves only which fields are displayed. It does not send commands or change currently applied values.

The selected value editors then appear in the regular device form. Choose the values and press “Geräteeinstellungen speichern”. Removing fields also requires this device-save operation before their old runtime values are removed; until then the last saved light behavior remains active. The interface explicitly explains this separation. Values not set yet are omitted from commands. Existing opted-in values become visible automatically, preserving compatibility.

During an active lighting phase, saving changed device values applies them once immediately. During an inactive phase the next scheduled turn-on uses them. Repeated timer ticks and restarts do not enforce them continuously. Turn-off remains a normal turn_off request. Capabilities are checked again at dispatch; unavailable properties show an error while normal turn-off remains possible.

Only opted-in values are passed to HA. HA/device defaults can still affect other attributes. Separate scene/script/select actions remain outside this version; preset effects reported by the light work without vendor-specific code.
