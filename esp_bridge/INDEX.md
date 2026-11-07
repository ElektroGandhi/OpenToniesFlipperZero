# ESP8266 BLE Bridge - Index (Optional)

Dieses Verzeichnis enthält alle Dateien für die **ESP8266 BLE Bridge**, die iOS-Geräten in **Safari** den Zugriff auf OpenTonies ermöglicht.

**Hinweis:** Diese Bridge ist **optional**! Es gibt Browser im App Store (Chrome, Edge, WebBLE), die WebBluetooth unterstützen und direkt mit dem Flipper kommunizieren können.

## 📁 Struktur

```
esp_bridge/
├── README.md                    # Hauptdokumentation
├── INDEX.md                     # Dies Datei - Übersicht
├── 
│── micropython/
│   ├── main.py                  # Hauptanwendung für MicroPython
│   ├── config.json              # Konfigurationsdatei
│   └── requirements.txt         # Benötigte Python-Module
│
│── esp8266_ble_bridge.yaml      # ESPHome Konfiguration
│── secrets_example.yaml         # Beispiel für Geheimnisse
│
└── web/
    └── opentonies_bridge.js     # JavaScript-Bibliothek für Web-App
```

## 🎯 Welche Lösung soll ich wählen?

| Kriterium | MicroPython | ESPHome | Arduino |
|-----------|-------------|---------|---------|
| **Einfachheit** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Flexibilität** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Home Assistant Integration** | ❌ | ⭐⭐⭐⭐⭐ | ❌ |
| **BLE-Support** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Empfohlen für** | Entwickler, schnelle Tests | HA-Nutzer | C++-Entwickler |

### Empfehlung: **MicroPython** ⭐
- Einfacher zu debuggen
- Mehr Kontrolle über BLE
- Schnellere Entwicklungszyklen
- Gut dokumentiert

## 🚀 Schnellstart mit MicroPython

### 1. MicroPython auf ESP8266 installieren

```bash
# ESP8266 löschen
esptool.py --port /dev/ttyUSB0 erase_flash

# MicroPython Firmware flashen
wget https://micropython.org/resources/firmware/esp8266-20240111-v1.22.0.bin
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp8266-20240111-v1.22.0.bin
```

### 2. Benötigte Module installieren

```bash
# ble_advertising Modul installieren
ampy --port /dev/ttyUSB0 upip install ble-advertising
```

### 3. Bridge-Dateien kopieren

```bash
# Dateien auf den ESP8266 kopieren
ampy --port /dev/ttyUSB0 put micropython/main.py
ampy --port /dev/ttyUSB0 put micropython/config.json
```

### 4. Konfiguration anpassen

Bearbeite `micropython/config.json`:
```json
{
  "wifi": {
    "ssid": "DEIN_WLAN_NAME",
    "password": "DEIN_WLAN_PASSWORT"
  },
  "flipper": {
    "mac": "A4:CF:12:XX:XX:XX"
  }
}
```

### 5. ESP8266 starten

Der ESP verbindet sich automatisch mit WLAN und BLE.

### 6. Testen

```bash
# PING-Test
curl http://opentonies-bridge.local/ping
# → PONG

# Status abrufen
curl http://opentonies-bridge.local/ble/status
# → {"ble_status": "connected", ...}
```

## 🏗️ Alternative: ESPHome (für Home Assistant)

### 1. Konfiguration vorbereiten

Kopiere `esp8266_ble_bridge.yaml` nach `~/homeassistant/esphome/`:
```bash
cp esp8266_ble_bridge.yaml ~/homeassistant/esphome/opentonies_bridge.yaml
```

### 2. Geheimnisse anpassen

Kopiere und passe `secrets_example.yaml` an:
```bash
cp secrets_example.yaml ~/homeassistant/esphome/secrets.yaml
# Datei bearbeiten und eigene Werte eintragen
```

### 3. In Home Assistant

1. Gehe zu: Einstellungen → Geräte & Dienste → ESPHome
2. Klicke auf "Konfiguration hochladen"
3. Wähle `opentonies_bridge.yaml` aus
4. ESP8266 flashen

## 🌐 Web-App Integration

### 1. Bridge-JavaScript einbinden

In `web/index.html` oder `web/index2.html`:

```html
<!-- OpenTonies Bridge Support für iOS -->
<script src="opentonies_bridge.js"></script>
```

### 2. Anpassungen in der Web-App

Ersetze direkte BLE-Aufrufe durch Bridge-Aufrufe:

**Vorher (direktes BLE):**
```javascript
const device = await navigator.bluetooth.requestDevice({...});
await device.gatt.writeValue(characteristic, command);
```

**Nachher (mit Bridge-Fallback):**
```javascript
// Prüfen ob Bridge benötigt wird
const useBridge = OpenToniesBridge.isSupported();

let device;
if (useBridge) {
    await OpenToniesBridge.connect();
} else {
    device = await navigator.bluetooth.requestDevice({...});
}

// Befehl senden
if (useBridge) {
    await OpenToniesBridge.sendCommand("PING");
} else {
    await device.gatt.writeValue(characteristic, command);
}
```

### 3. Automatische Erkennung

Die Bridge erkennt automatisch:
- iOS-Geräte (kein WebBluetooth)
- Browser ohne WebBluetooth-Unterstützung
- Manuelle URL-Konfiguration

## 📡 API-Referenz

Die Bridge stellt folgende HTTP-Endpunkte bereit:

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| GET | `/ping` | Testverbindung |
| GET | `/ble/status` | Verbindungsstatus |
| GET | `/ble/connect?mac=XX:XX` | Mit Flipper verbinden |
| GET | `/ble/disconnect` | Verbindung trennen |
| POST | `/ble/send` | Befehl an Flipper senden |
| GET | `/ble/response` | Letzte Antwort abrufen |
| GET | `/ble/scan` | Nach Flippers scannen |

### Beispiel: Befehl senden

```bash
# PING senden
curl -X POST http://opentonies-bridge.local/ble/send \
  -H "Content-Type: application/json" \
  -d '{"command": "PING\n"}'

# Antwort abrufen
curl http://opentonies-bridge.local/ble/response
# → {"response": "OK\n"}
```

## 🔧 Flipper Zero BLE-Details

### Service UUIDs (Nordic Serial Service)

| UUID | Typ | Richtung | Beschreibung |
|------|-----|----------|--------------|
| `0000180d-0000-1000-8000-00805f9b34fb` | Service | - | Nordic Serial Service |
| `00002012-0000-1000-8000-00805f9b34fb` | Characteristic | Write | RX - Befehle senden |
| `00002013-0000-1000-8000-00805f9b34fb` | Characteristic | Notify | TX - Antworten empfangen |

### Unterstützte Befehle

| Befehl | Beschreibung |
|--------|--------------|
| `PING` | Testverbindung |
| `LIST` | Liste aller Serien/Folgen |
| `PLAY <path>` | Folge abspielen (z.B. `PLAY Bibi Blocksberg/Die Hexe.nfc`) |
| `STOP` | Abspielen stoppen |
| `STATUS` | Aktueller Status |
| `FAV+` | Serie zu Favoriten hinzufügen |
| `FAV-` | Serie aus Favoriten entfernen |
| `FAVS` | Liste aller Favoriten |

## 🔍 Troubleshooting

### ESP8266 verbindet nicht mit WLAN
- SSID und Passwort prüfen
- WLAN-Frequenz prüfen (2.4 GHz für ESP8266!)
- Signalstärke prüfen

### ESP8266 verbindet nicht mit Flipper
- Flipper BLE einschalten (Setup → Bluetooth = AN)
- MAC-Adresse prüfen (`bleak --scan`)
- Abstand prüfen (max. 5-10m)
- Andere BLE-Geräte in der Nähe können stören

### HTTP-API nicht erreichbar
- IP-Adresse prüfen
- Firewall prüfen
- Port 80 freigeben

### iOS kann Bridge nicht finden
- mDNS prüfen (`ping opentonies-bridge.local`)
- IP-Adresse manuell eingeben
- Netzwerk-Konfiguration prüfen

## 📚 Weiterführende Links

- [MicroPython](https://micropython.org/)
- [ESPHome](https://esphome.io/)
- [ESP8266 Technical Reference](https://www.espressif.com/en/products/socs/esp8266)
- [Nordic Serial Service Specification](https://www.bluetooth.com/specifications/specs/nordic-serial-service/)
- [WebBluetooth API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API)
- [Flipper Zero BLE Documentation](https://github.com/flipperdevices/flipperzero-firmware/tree/dev/.github/scripts/ble)

## 💡 Tipps

1. **Für beste Kompatibilität:** Nutze einen ESP32 statt ESP8266 - mehr RAM, bessere BLE-Unterstützung
2. **Stromversorgung:** Mindestens 5V, 500mA für stabilen Betrieb
3. **Gehäuse:** Ein 3D-gedrucktes Gehäuse schützt den ESP und sieht gut aus
4. **Debugging:** Nutze die serielle Konsole (`screen /dev/ttyUSB0 115200`) für Debug-Meldungen
5. **Sicherheit:** Nutze HTTPS oder ein sicheres lokales Netzwerk für die Bridge

## 🎉 Fertig!

Die ESP8266 BLE Bridge ist jetzt bereit! 🎊

**Nächste Schritte:**
1. ESP8266 flashen und testen
2. Web-App anpassen
3. Mit iPhone testen
4. Bei Problemen: Troubleshooting oben
