# Lastzonen Deutschland

Schnee-, Wind- und Erdbebenzone mit den zugehörigen Lastwerten für einen Standort in Deutschland, gewählt per Karte oder Ortssuche:

- Schneelastzone und charakteristische Schneelast s_k nach DIN EN 1991-1-3/NA
- Windzone, Grundgeschwindigkeitsdruck q_b und Böengeschwindigkeitsdruck q_p nach DIN EN 1991-1-4/NA
- Erdbebenzone, Untergrundklasse und Bodenbeschleunigung a_gR nach DIN 4149

Die Seite ermittelt Gemeinde und Geländehöhe des Standorts, ordnet die Zonen über die DIBt-Tabellen nach Verwaltungsgrenzen zu und rechnet die Lastwerte aus. Alle Zonen lassen sich von Hand überschreiben.

> **Prototyp, ungeprüft, keine Gewähr, ersetzt keine eigene Prüfung der Zonenzuordnung.**
> Die Zuordnung ist verbindlich nach den DIBt-Tabellen und dem jeweiligen Landesrecht zu prüfen. Bei geteilten Gemeinden, Ortsteilregeln, Gebietsreformen und Sonderlagen kann die automatische Zuordnung falsch sein.

## Aufbau

| Datei | Inhalt |
|---|---|
| `index.html` | fertige Seite mit eingebetteten Daten (GitHub Pages); wird erzeugt, nicht von Hand bearbeiten |
| `page_head.html` | HTML-Gerüst und CSS der Seite |
| `app.js` | Logik: Namensabgleich, Regelauswahl, Lastformeln, Karte, Ortssuche |
| `zonen.json` | Zuordnungsregeln für Schnee, Wind und Erdbeben, erzeugt aus den DIBt-Tabellen |
| `build_zonen.py` | erzeugt `zonen.json` aus den DIBt-Excel-Dateien (benötigt `openpyxl`) |
| `assemble.py` | baut `index.html` aus `page_head.html`, `zonen.json` und `app.js` |
| `test_lookup.js` | Stichproben der Zuordnung für ausgewählte Gemeinden |
| `.nojekyll` | schaltet die Jekyll-Verarbeitung von GitHub Pages ab |

Die DIBt-Excel-Dateien liegen nicht im Repository.

## Aktualisieren bei neuen DIBt-Tabellen

1. Die drei Excel-Dateien von der [DIBt-Seite „Technische Baubestimmungen“](https://www.dibt.de/de/wir-bieten/technische-baubestimmungen) in einen Ordner außerhalb des Repositorys laden.
2. Den neuen Stand in `build_zonen.py` (Feld `stand`) eintragen und die Regeln erzeugen:
   `python build_zonen.py <ordner-mit-xlsx> zonen.json`
3. Stichproben prüfen und mit den Tabellen vergleichen:
   `node test_lookup.js app.js zonen.json`
4. Seite neu bauen:
   `python assemble.py`
5. `index.html` im Browser öffnen und einige Standorte von Hand gegen die Tabellen prüfen.

`build_zonen.py` enthält von Hand gepflegte Sonderregeln und setzt den Blattaufbau der Tabellen voraus. Bei geänderten Tabellen ist das Skript zu prüfen.

## Datenquellen

- **Zonenzuordnung:** Tabellen des Deutschen Instituts für Bautechnik (DIBt), <https://www.dibt.de/de/wir-bieten/technische-baubestimmungen>
  - Zuordnung der Schneelastzonen nach Verwaltungsgrenzen, Stand 07.02.2023
  - Zuordnung der Windzonen nach Verwaltungsgrenzen, Stand 02.06.2022
  - Zuordnung der Erdbebenzonen und Untergrundklassen nach Verwaltungsgrenzen, Stand 02.06.2022
- **Karte:** TopPlusOpen. Kartendarstellung: © [BKG](https://www.bkg.bund.de) (Jahr des Abrufs) [dl-de/by-2-0](https://www.govdata.de/dl-de/by-2-0), Datenquellen: <https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_topplusopen.html>. Ersatzkarte bei Ausfall: © [OpenStreetMap](https://www.openstreetmap.org/copyright)-Mitwirkende.
- **Ortssuche:** [Nominatim](https://nominatim.org), bei Ausfall [Photon](https://photon.komoot.io) (komoot). Daten © [OpenStreetMap](https://www.openstreetmap.org/copyright)-Mitwirkende, Open Database License (ODbL).
- **Geländehöhe:** [Open-Meteo.com](https://open-meteo.com/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); Höhenmodell Copernicus DEM GLO-90, © ESA/Copernicus.

### Nutzungsbedingungen der Dienste

- **Nominatim** ([Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)): höchstens 1 Anfrage pro Sekunde über alle Nutzer der Seite zusammen, kein Massenbetrieb, keine Suchvorschläge beim Tippen, gleiche Anfragen nicht wiederholen. Die Seite drosselt je Browser auf 1 Anfrage pro Sekunde und merkt sich Ergebnisse für die Sitzung.
- **Open-Meteo** ([Terms](https://open-meteo.com/en/terms)): kostenlos nur für nicht-kommerzielle Nutzung, unter 10 000 Abrufen pro Tag. Kommerzielle Nutzung erfordert einen bezahlten Zugang.
- **TopPlusOpen** ([BKG](https://gdz.bkg.bund.de/index.php/default/wmts-topplusopen-wmts-topplus-open.html)): Datenlizenz Deutschland – Namensnennung – Version 2.0, Quellenvermerk wie oben.
- **OpenStreetMap-Kacheln** ([Tile Usage Policy](https://operations.osmfoundation.org/policies/tiles/)) und **Photon**: nur als Ersatz bei Ausfall, maßvolle Nutzung, keine zugesicherte Verfügbarkeit.

Lizenz: keine. © Fabian Böttinger, alle Rechte vorbehalten.
