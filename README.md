# Weihnachtszentrale

v0.7.0 – erste öffentliche Vorabversion einer Home-Assistant-Integration für Weihnachtsbeleuchtung. Lokale Regressionstests bestanden; die Erstinstallation über den Marketplace und individuelle Rollladenfahrten sind separat zu prüfen.

Geräte, Zeitprofile und Saisonmodi im Dashboard konfigurieren. Lichtsteuerung läuft im Backend. Optionale Rollladenkoordination ist standardmäßig aus. Individuelle Automationen und Sicherheitsskripte werden ausdrücklich angebunden und bleiben in Home Assistant.

Ab HA2026.11.2. Unter Einstellungen → Marketplace dieses Repository als benutzerdefinierte Quelle der Kategorie Integration aufnehmen, Version installieren und HA neu starten. HACS ist seit HA2026.11 integriert; keine separate HACS-Installation nötig. Die Dashboard-Karte wird gemeinsam mit der Integration aktualisiert und im Ressourcen-Speichermodus automatisch registriert. Drei Kartenansichten bleiben: overview, configuration, actions.

- [Einbau und Migration](docs/INSTALL.md)
- [Rollladenfunktion und Grenzen](docs/COVERS.md)
- [HACS und Architektur](docs/HACS.md)

Noch keine Morgenöffnung, Partylogik oder Govee-Szenenauswahl. Die Integration bedient reale Aktoren und ersetzt keine unabhängige Sicherheitslogik. Lokale Tests verwenden simulierte HA-Schnittstellen. Erste Marketplace-Migration und individuelle Geräteanbindung gesondert prüfen.
