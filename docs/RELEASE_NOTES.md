# v0.7.1 – Geräte ohne Zustandsrückmeldung

Pro Licht/Steckdose ist „Keine Zustandsrückmeldung (z. B. 433 MHz)“ wählbar. Die Automatik übergibt dann pro Zeitplanphase einmal den Ein-/Aus-Befehl, auch bei unbekanntem gemeldetem Zustand. Ein vorhandener gemeldeter Zustand wird bei dieser Option nicht als Bestätigung verwendet. Nicht verfügbare/fehlende Entitäten und Servicefehler bleiben Fehler, da HA nicht verfügbare Entitäten nicht ansteuert. Keine Dauersendung im 15-Sekunden-Takt; abgeschlossene Phasen bleiben über Neustarts gespeichert.

Standard bleibt die bisherige Zustandsbehandlung. Alte Konfigurationen bleiben gültig. Auf der Übersicht wird bei solchen Geräten ausdrücklich kein tatsächlicher Schaltzustand behauptet. Option im Dashboard pro Gerät aktivieren und Einstellungen speichern. Die Änderung dieser Option gleicht einmal den aktuellen Zeitplan an.

Update über Marketplace installieren, HA neu starten und Browser neu laden. Rollladenkoordination weiterhin optional und unverändert.
