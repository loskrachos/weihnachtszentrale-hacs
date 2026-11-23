# v0.9.0 – Structured configuration and separate field selection

Configuration now has two internal pages: Zeiten (central schedules/preview) and Geräte (participants, turn-on values and cover options). Tabs preserve unsaved drafts. Separate server-side save scopes prevent schedule saves from overwriting devices or the season, and device saves from overwriting central times.

Additional device properties are selected in a labeled checkbox panel and persisted with “Feldauswahl speichern”. This operation only stores the field layout; it sends no light commands and leaves current runtime values unchanged. Selected value editors appear in the standard device form with aligned rows. Apply changed values or remove hidden values explicitly with “Geräteeinstellungen speichern”. Existing opted-in values remain visible without migration. Effect, RGB color and color temperature are alternatives.

Dividers, stable field order, section icons and responsive alignment improve scanning. Existing dashboard cards remain compatible. Automatic sidebar navigation and seasonal visibility (#5) are not included.

Automated tests use simulated HA/DOM interfaces. Device effect behavior still requires separate real-device acceptance. No new values are selected automatically during installation. Addresses #4.
