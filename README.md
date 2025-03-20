# Minecraft Log Scraper

Ein einfaches Python-Skript, das CityBuild Toplist-Daten aus Minecraft-Logdateien extrahiert und optional als ZIP-Archiv speichert.

## Nutzung

### Parameter

- **`input_path`** *(erforderlich)* – Pfad zum Ordner mit den Minecraft-Logdateien.
- **`output_name`** *(erforderlich)* – Name des Ordners, in dem die extrahierten Daten gespeichert werden.
- **`--pack`** *(optional)* – erstellt nach der Verarbeitung eine ZIP-Datei des Ausgabeordners.
- **`--threading`** *(optional)* – aktiviert Multithreading für besonders große Verzeichnisse.
    - **Hinweis:** Falls eine chronologisch geordnete Ausgabe wichtig ist, sollte diese Option nicht genutzt werden.

### Demo

**[Video Link](https://www.youtube.com/watch?v=Do2OcHd_0_k)**

### Beispiel

```bash
python scraper.py "C:\Users\Benutzer\AppData\Roaming\.minecraft\logs" "out" --pack
```


