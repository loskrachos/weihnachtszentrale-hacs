# Zusatz v0.8.0 – optionale, allgemeine Koordination

Standardmäßig deaktiviert. Im Konfigurations-Dashboard separat aktivieren und Ablaufzeit für wartende Anfragen wählen (Ausgangswert06:00). Deaktivieren verwirft wartende Aufträge ohne Bewegung; neue explizite Anfragen werden direkt ausgeführt. Individuelle HA-Automationen und vorhandene Sicherheitsprüfungen bleiben beim Nutzer. Keine automatische Anbindung oder universelle Sicherheitslösung. Die Ablaufzeit wird bei einer neuen Anfrage übernommen; bestehende Aufträge behalten ihre ursprüngliche Grenze. Historische feste06:00-Angaben unten sind durch diese Einstellbarkeit ersetzt.

# Abendliche Rollladensperre v0.6.1

## Verhalten

Im Dashboard pro Licht „Abends offen halten: Rollladen (optional)“ wählen. „Keiner“ bedeutet keine Sperre. Mehrere Lichter dürfen denselben Rollladen halten. Ein Licht kann weiterhin nur einem Rollladen zugeordnet werden. Morgenöffnung und Party sind nicht implementiert.

Nur Schließwünsche über `weihnachtszentrale.request_cover_close` werden geprüft. Bei aktiver Automatik und aktivem Saisonmodus halten zugeordnete, teilnehmende eingeschaltete Lichter die Fahrt zurück. Unbekannte Lichtzustände werden zunächst als Sperre behandelt. Sobald das letzte Licht aus ist, wird eine weiterhin gültige Anforderung ausgeführt. Ein von der Lichtautomatik übergebener Ausschaltbefehl genügt bei veralteter Zustandsrückmeldung. Ein danach neu gemeldetes manuelles Einschalten sperrt wieder. Lichtfehler dürfen die unabhängigen Sicherheitsprüfungen des Rollladens nicht umgehen.

Die Sperre selbst öffnet keinen Rollladen. Der Rollladen muss bei der Schließanforderung noch offen sein. Beim Systemstart oder Licht-An ohne vorgemerkte Anforderung gibt es keine zusätzliche Fahrt. Zeitprofile bestimmen die Lichtschaltung; eine manuell eingeschaltete zugeordnete Leuchte hält einen abendlichen Schließwunsch ebenfalls zurück.

Eine Anforderung behält Zielposition, Anlass und optional das vorhandene Sicherheitsskript. Keine Fahrt zu einer weiter geöffneten Position. Auch eine Teil-Schließanforderung bleibt eine Schließung. Bestehende Bedingungen der HA-Automation nicht entfernen. Bedingungen, die zum tatsächlichen Nachholzeitpunkt erneut geprüft werden müssen, müssen in einem vorhandenen Sicherheitsskript liegen; dessen Prüfungen werden nicht in der Integration nachgebaut.

Anforderungen werden im HA-Store gespeichert. Sie verfallen am nächsten06:00Uhr, damit nach einer Störung morgens keine alte Abendfahrt nachgeholt wird. Das ist eine aktuelle feste Gültigkeitsgrenze, kein Öffnungszeitpunkt. Vorher kann die Anforderung auf der Übersicht oder über „Schließanforderung verwerfen“ entfernt werden. Für spätere Partylogik wird die Gültigkeit separat weiterentwickelt.

Während Pause werden vorgemerkte Fahrten nicht nachgeholt. NEUE Anfragen der weiterhin aktiven HA-Schließautomation werden dann wie ohne Weihnachtssteuerung ausgeführt; Pause ist keine dauerhafte Offenhaltefunktion. Modus Aus entfernt die weihnachtliche Licht-Sperre bei aktiver Automatik.

Manuelle Rollladenbedienung bleibt möglich und verwirft ab v0.8.0 keine vorgemerkte Schließanforderung mehr. Auch eine geänderte gemeldete Position erhält den ursprünglichen Zielwert. Während die Lichter an sind, bleibt die manuell gewählte Position bestehen. Nach Licht-Aus wird der gespeicherte Schließwunsch ausgeführt. Ist der Rollladen bereits am Ziel oder weiter geschlossen, wird er nicht wieder geöffnet. Soll eine spätere Fahrt ausdrücklich entfallen, „Verwerfen“ auf der Übersicht verwenden. Ablaufzeit, Pause, Deaktivierung und Sicherheitsprüfungen bleiben wirksam.

Schalt-/Skriptfehler oder ein Neustart während der Befehlsübergabe verlangen eine Sichtprüfung; keine blinde Wiederholung. Auf Übersicht erscheint der Status. `blocked`/`timeout` eines Sicherheitsskripts sind kein Erfolg. Für einen bewusst erneuten Versuch dieselbe Schließanforderung erneut ausführen; Sicherheitsbedingungen werden dabei erneut geprüft.

## Grafische Anbindung – getrennte Zweige je Rollladen

1. Zuerst v0.6.1 installieren. Native Entität „Weihnachtszentrale | Weihnachtsmodus aktiv“ unter Einstellungen → Geräte & Dienste → Entitäten finden und ihre tatsächliche ID prüfen. off bedeutet Saison Aus, on bedeutet Reduziert oder Vollbetrieb. Kein zusätzlicher Helfer nötig.
2. Einstellungen → Automationen & Szenen → vorhandene Abendautomation öffnen. Auslöser, bestehende Bedingungen, Modus und unbetroffene Aktionen erhalten.
3. Für jeden gewünschten Rollladen einzeln einen „Auswählen“-Baustein erstellen. Zwei Optionen mit jeweils einer Zustandsbedingung auf die verifizierte Modus-Entität:
   - Option1: Zustand off → bisherige direkte Schließaktion mit bisherigem Ziel.
   - Option2: Zustand on → „Weihnachtszentrale: Rollladen | Schließung anfordern“, gleicher Rollladen und gleiche Zielposition.
4. Bei der Anfrage Zielposition0 für vollständiges Schließen, bei bestehender Teilfahrt die tatsächlich konfigurierte Position übernehmen. Sicherheitsskript nur auswählen, wenn bislang eines verwendet wird; dieses unverändert wiederverwenden. Anlass z.B. Abendautomation.
5. Bisherige direkte Aktion IN den off-Zweig verschieben; sie darf nicht zusätzlich außerhalb des Bausteins laufen. Beide Optionen schließen sich aus. Kein Default-Fahrbefehl bei unknown/unavailable: ein fehlender Modus ist keine bestätigte Saison-Aus-Freigabe. Die übrigen Aktionsbausteine werden dadurch nicht ersetzt.
6. Für den zweiten gewünschten Rollladen denselben Aufbau erstellen. Alle anderen Aktionen bleiben unverändert. Speichern.

Außerhalb Weihnachten schließt der off-Zweig direkt, ohne Aufruf der Cover-Koordination. Während Weihnachten stellt der on-Zweig die Anfrage, damit sie gegebenenfalls vorgemerkt und nach Licht-Aus nachgeholt werden kann. Eine globale Bedingung vor die gesamte Automation wäre ungeeignet, weil sie auch die Entstehung dieser Anfragen verhindern würde.

Die native Modus-Entität liest denselben HA-Store wie das Dashboard. Speichern im Dashboard aktualisiert sie sofort. Entität unavailable/unknown nicht mit off gleichsetzen. Die Integration muss für die Modus-Entität installiert bleiben; vor Deinstallation direkte Aktionen wiederherstellen.

Kein vollständiges Automations-YAML als Einbauweg. Diese Änderungen gemeinsam im grafischen Editor aufbauen. Ausdrücklich kein manueller Fahrttest beauftragt: nach Umsetzung nächsten regulären Abendlauf abwarten und Nutzer-Rückmeldung erfassen.

## Zurückgestellter Funktionstest (nicht jetzt durchführen)

- Nur ein geeignetes Licht und einen unkritischen Rollladen zuordnen. Automatik aktiv und Saison Vollbetrieb. Licht eingeschaltet, Rollladen offen.
- Werkzeuge → Aktionen → „Rollladen | Schließung anfordern“ wählen. Richtigen Rollladen, Ziel0, keinen neuen Sicherheitsweg erfinden. Ausführen.
- Erwartung: keine Fahrt, Übersicht zeigt „Wartet auf Licht-Aus“.
- Licht manuell ausschalten. Innerhalb etwa15Sekunden wird die angeforderte Schließung übergeben, sofern keine unabhängige Sicherheit sie verhindert.
- Ein tatsächlicher Fahrttest bewegt den ausgewählten Rollladen. Erst diesen Test gemeinsam durchführen, dann weitere Zuordnungen aktivieren.
- Lokale Tests ersetzen diesen HA-Test nicht. Fehler/ausstehende Fahrten auf Übersicht prüfen.

Grundlagen: [HA-Aktionen für Integrationen](https://developers.home-assistant.io/docs/dev_101_services/), [HA-Cover-Aktionen](https://www.home-assistant.io/integrations/cover/).
