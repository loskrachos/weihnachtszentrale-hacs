# Installation und Updates über HACS/Marketplace v0.8.0

Erste öffentliche Vorabversion. Lokale Tests ersetzen keine Prüfung der eigenen HA-Migration. HA2026.11 oder neuer enthält HACS als Marketplace; diese Integration benötigt mindestens HA2026.11.2.

## Allgemeine Integration, individuelle Automation

Die Integration enthält keine fest eingebauten privaten Licht-/Rollladen-IDs, Türkontakte oder Sicherheitsskripte. Ihre allgemeinen Bausteine sind Geräteauswahl, Zeitmodell, Schaltsteuerung, optionale Schließanforderungen und Status. Individuelle Rollladen-Automationen bleiben beim Nutzer in HA und müssen gezielt angebunden werden. Keine globale Übernahme fremder Automationen, keine zusätzliche Morgenöffnung und keine implementierte Partyfunktion.

Rollladenkoordination ist standardmäßig deaktiviert, unabhängig von der Lichtautomatik. In Konfiguration aktivieren und eine Ablaufzeit wählen;06:00ist nur der Ausgangswert, keine universelle Sicherheitsregel und keine Öffnungszeit. Deaktivieren verwirft wartende Fahrten ohne Bewegung. Neue explizite Schließanfragen werden bei deaktivierter Koordination direkt weitergereicht. Bestehende Sicherheitslogik muss in den aufgerufenen Skripten bleiben und beim tatsächlichen Fahrtanlass erneut geprüft werden. Grenzen siehe COVERS.md.

Die Software steuert reale Aktoren; „keine Zugangsdaten im Paket“ bedeutet nicht „ohne Sicherheitsbezug“. Sicherheitsskripte dürfen nicht umgangen werden. unknown/unavailable, blockierte Skripte, fehlende Rückmeldungen und Fehler sind keine bestätigte erfolgreiche Fahrt. Mehrere Lampen pro Cover möglich, weiterhin ein Cover pro Lampe. Keine Unterstützung für alle herstellerspezifischen Sicherheitsfunktionen versprochen.

## Verteilung

Öffentliche Installationsquelle: https://github.com/loskrachos/weihnachtszentrale-hacs . Enthalten sind Runtime, allgemeine Anleitung, Tests und Releasewerkzeuge. Keine .storage-/HA-Konfiguration, Zugangsdaten, Screenshots oder privaten Automationsdateien. Als benutzerdefinierte Quelle hinzufügen; keine Aufnahme in den Standardkatalog vorausgesetzt.

Alle Runtime-Dateien liegen jetzt unter custom_components/weihnachtszentrale einschließlich frontend/*.js. hacs.json und Manifest sind vorbereitet. Release-Workflow prüft Tag/Manifest, Tests und Paket und erzeugt zunächst einen ENTWURF als Vorabversion. Der Entwurf wird erst nach Prüfung veröffentlicht. Verfügbare Versionen werden als echte GitHub-Releases bereitgestellt.

Nach einmaliger Aufnahme des Repositorys als benutzerdefinierte Integration übernimmt der Marketplace die Dateien. Danach bei Updates: Integrationsupdate im Marketplace installieren, HA neu starten, Dashboard neu laden. Keine einzelne JS-Datei kopieren und keine Ressourcen-URL pro Version bearbeiten. Erste Migration aus der manuellen Installation gesondert prüfen. Bestehende HA-Store-Einstellungen bleiben außerhalb des Integrationsordners erhalten.

## Automatische Dashboard-Karte

Das Backend stellt die mitgelieferte Karte unter /weihnachtszentrale/ bereit. In HA2026.11.2 mit Ressourcen im Speichermodus wird genau ein Moduleintrag angelegt/aktualisiert. Bekannte alte /local/weihnachtszentrale-card*.js-Einträge werden migriert, fremde Ressourcen bleiben unverändert. Versionspfad wird vom Backend gesetzt und verhindert altes Frontend im Browsercache. Vorhandene drei Karten behalten type und view. Alte www-Dateien können zunächst liegen bleiben.

YAML-Ressourcenmodus wird nicht automatisch überschrieben und ist für diesen automatischen Umstieg derzeit nicht unterstützt. Er muss vor dem Umstieg bewusst berücksichtigt werden. Nicht als vollständig HA-live-getestet ausgeben: aktuelle Tests simulieren Ressourcen-API und HTTP-Anmeldung. Keine HACS-Zugangsdaten im Projekt hinterlegen.

Quellen: https://hacs.dev/docs/publish/start/ und https://hacs.dev/docs/publish/integration/ . Ressourcen-API anhand HA2026.11.2-Quellcode geprüft.
