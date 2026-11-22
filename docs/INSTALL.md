# Installation und Updates über den Marketplace

Voraussetzungen: HA2026.11.2 oder neuer, Dashboard-Ressourcen im Speichermodus. HACS ist seit HA2026.11 als Marketplace integriert. Keine zusätzliche HACS-Custom-Integration installieren. Dies ist eine frühe Version mit lokalen Tests; die Migration in der eigenen HA-Installation prüfen.

Unter Einstellungen → Marketplace in der Quellen-/Repositoryverwaltung https://github.com/loskrachos/weihnachtszentrale-hacs als benutzerdefinierte Quelle hinzufügen, Kategorie Integration. Vorabversionen gegebenenfalls aktivieren und v0.7.0 auswählen. Version installieren, HA neu starten. Neue Einrichtung unter Einstellungen → Geräte & Dienste → Integration hinzufügen → Weihnachtszentrale. Bestehende manuelle Installation nicht entfernen: Der Marketplace verwaltet denselben custom_components/weihnachtszentrale-Ordner. HA-Store-Daten bleiben außerhalb davon erhalten; kein zusätzlicher Helfer.

Die mitgelieferte Karte wird automatisch registriert. Bekannte alte lokale Weihnachtszentrale-Moduleinträge werden migriert; fremde Ressourcen bleiben unverändert. Browser vollständig neu laden. Keine JS-Datei separat nach www kopieren und keine URL pro Version ändern. YAML-Ressourcenmodus ist für den automatischen Umstieg derzeit nicht unterstützt.

Pro gewünschter Dashboard-Ansicht eine Karte mit type custom:weihnachtszentrale-card und view overview, configuration oder actions. Geräte/Zeiten in Konfiguration wählen und speichern. Lichtautomatik im Überblick aktivieren; neue Installation zunächst pausiert, bestehender Aktivierungsstand bleibt erhalten.

Rollladenkoordination gesondert aktivieren und Ablaufzeit einstellen. Konkrete Sicherheitsprüfungen/Automationen vorher prüfen, siehe COVERS.md. Bei Updates die neue Integrationsversion im Marketplace installieren, HA neu starten und Browser neu laden. Echte ID der Modus-Entität unter Einstellungen → Geräte & Dienste → Entitäten prüfen.

Offizielle Erklärung: https://www.hacs.xyz/docs/marketplace/ .
