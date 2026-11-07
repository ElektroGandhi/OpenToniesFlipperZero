# ESP8266 BLE Bridge für OpenTonies (iOS Support - Optional)

## Warum diese Brücke?

**Hinweis:** Diese Bridge ist **optional**! 

Es gibt Browser im App Store (z. B. Chrome, Edge, WebBLE), die **WebBluetooth unterstützen** und direkt mit dem Flipper Zero kommunizieren können. Die Bridge ist nur für **Safari-Nutzer** nötig, die keinen alternativen Browser installieren möchten.

Safari auf iOS unterstützt **kein WebBluetooth**. Eine Web-App in Safari kann daher nicht direkt mit dem Flipper Zero kommunizieren. 

**Lösung:** Ein ESP8266 dient als Vermittler:
- **ESP8266 ↔ Flipper Zero:** Kommunikation über **BLE (Serial Profile)**
- **ESP8266 ↔ Web-App:** Kommunikation über **HTTP/REST oder WebSocket**

Das iPhone (in Safari) spricht dann nur noch HTTP mit dem ESP8266, der die Befehle per BLE an den Flipper weiterleitet.

## Architektur

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   iPhone    │────▶│   ESP8266    │────▶│  Flipper    │
│  (Safari)   │ HTTP │  BLE Bridge   │ BLE  │   Zero      │
└─────────────┘     └──────────────┘     └─────────────┘
       │                                      │
       │ Web-App (HTTPS)                      │ NFC-Emulation
       ▼                                      ▼
┌─────────────────────────────────────────────────────────┐
│                  Toniebox (erkennt Figur)                  │
└─────────────────────────────────────────────────────────┘
```

## Optionen für die ESP8266-Implementierung

### Option A: MicroPython (empfohlen ⭐)
Einfacher zu debuggen, mehr Flexibilität mit BLE.

**Voraussetzungen:**
- ESP8266 mit MicroPython Firmware
- `micropython-esp8266` oder `micropython-esp32`
- Bibliotheken: `micropython-umqtt.simple`, `ble_advertising`

**Dateien:**
- [`main.py`](micropython/main.py) - Hauptanwendung
- [`config.json`](micropython/config.json) - Konfiguration (WLAN, Flipper MAC)

### Option B: ESPHome (für Home Assistant Nutzer)
Integration in bestehende Home Assistant Installation.

**Voraussetzungen:**
- Home Assistant mit ESPHome Add-on
- ESP8266 (NodeMCU v2 oder ähnlich)

**Dateien:**
- [`esp8266_ble_bridge.yaml`](esp8266_ble_bridge.yaml) - ESPHome Konfiguration
- [`secrets.yaml`](secrets_example.yaml) - Geheimnisse (anpassen!)

### Option C: Arduino IDE mit ESP8266 Core
Für Entwickler, die Arduino bevorzugen.

**Dateien:**
- [`ble_bridge.ino`](arduino/ble_bridge.ino) - Arduino Sketch

---

## Vorbereitung

### 1. Flipper Zero BLE-MAC-Adresse ermitteln

```bash
# Auf einem Linux-Rechner mit Bluetooth:
nimble scan
# Oder:
bleak --scan
```

Such nach einem Gerät mit Namen wie `Flipper Zero` oder `Momentum`. Die MAC-Adresse sieht so aus: `A4:CF:12:XX:XX:XX`

### 2. ESP8266 vorbereiten

#### Für MicroPython:
```bash
# MicroPython auf ESP8266 flashen
esptool.py --port /dev/ttyUSB0 erase_flash
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 firmware.bin

# Dateien hochladen
ampy --port /dev/ttyUSB0 put micropython/main.py
ampy --port /dev/ttyUSB0 put micropython/config.json
```

#### Für ESPHome:
1. Datei `esp8266_ble_bridge.yaml` nach `~/homeassistant/esphome/` kopieren
2. `secrets.yaml` anpassen (WLAN, BLE MAC)
3. In Home Assistant: ESPHome Integration → Konfiguration hochladen
4. ESP8266 flashen

---

## API-Spezifikation (HTTP)

Die Bridge stellt folgende Endpunkte bereit:

### GET /ping
Testverbindung
```
→ Request:  GET /ping
← Response: PONG
```

### POST /ble/send
Befehl an Flipper senden
```
→ Request:  POST /ble/send
           Body: {"command": "PING\n"}
← Response: {"status": "sent", "command": "PING\n"}
```

### GET /ble/response
Letzte Antwort vom Flipper abrufen
```
→ Request:  GET /ble/response
← Response: {"response": "OK\n"}
```

### GET /ble/status
Verbindungsstatus
```
→ Request:  GET /ble/status
← Response: {"ble_status": "connected", "flipper_mac": "A4:CF:12:XX:XX:XX"}
```

### GET /ble/connect
Mit Flipper verbinden
```
→ Request:  GET /ble/connect?mac=A4:CF:12:XX:XX:XX
← Response: {"status": "connecting"}
```

### GET /ble/disconnect
Verbindung trennen
```
→ Request:  GET /ble/disconnect
← Response: {"status": "disconnected"}
```

---

## Web-App Anpassungen

Die Web-App muss so angepasst werden, dass sie erkennt, ob sie:
1. **Direkt mit Flipper** (Android/Desktop) kommuniziert
2. **Über die ESP-Bridge** (iOS) kommuniziert

### Erkennung

```javascript
// In web/index.html oder einem neuen Modul
const USE_BRIDGE = /iPad|iPhone|iPod/.test(navigator.userAgent) || 
                  !navigator.bluetooth;

let BRIDGE_URL = "http://opentonies-bridge.local"; // mDNS
// oder: "http://<ESP8266_IP>:80"
```

### Verbindung

```javascript
async function connect() {
  if (USE_BRIDGE) {
    // Über ESP-Bridge
    const response = await fetch(`${BRIDGE_URL}/ble/connect?mac=${FLIPPER_MAC}`);
    const data = await response.json();
    if (data.status === "connected") {
      console.log("Verbindung über Bridge hergestellt");
    }
  } else {
    // Direktes BLE (bestehend)
    await navigator.bluetooth.requestDevice(...);
  }
}

async function sendCommand(cmd) {
  if (USE_BRIDGE) {
    await fetch(`${BRIDGE_URL}/ble/send`, {
      method: "POST",
      body: JSON.stringify({command: cmd + "\n"}),
      headers: {"Content-Type": "application/json"}
    });
  } else {
    // Direktes BLE
    await device.gatt.writeValue(...);
  }
}
```

---

## Flipper Zero - BLE Serial Profile

Der Flipper Zero verwendet das **Nordic Serial Service** für die Kommunikation:

| UUID | Typ | Richtung | Beschreibung |
|------|-----|----------|--------------|
| `0000180d-0000-1000-8000-00805f9b34fb` | Service | - | Nordic Serial Service |
| `00002012-0000-1000-8000-00805f9b34fb` | Characteristic | Write | Befehle an Flipper senden |
| `00002013-0000-1000-8000-00805f9b34fb` | Characteristic | Notify | Antworten von Flipper empfangen |

**Protokoll:**
- Befehle werden als **Klartext + Zeilenende (`\n`)** gesendet
- Unterstützte Befehle: `PING`, `LIST`, `PLAY <path>`, `STOP`, `STATUS`, `FAV+`, `FAV-`, `FAVS`
- Antworten enden ebenfalls mit `\n`

---

## Hardware-Empfehlungen

| Komponente | Empfehlung | Preis | Hinweise |
|-----------|------------|-------|----------|
| ESP8266 | NodeMCU v2 | ~10 € | Integrierter USB-Serial, einfach zu flashen |
| ESP8266 | Wemos D1 Mini | ~8 € | Kompakter, gute Pins |
| ESP32 | ESP32 DevKit | ~15 € | Mehr RAM, besser für komplexe Logik |
| Strom | USB Power Bank | ~10 € | 5V, 2A für stabilen Betrieb |
| Gehäuse | 3D-gedruckt | - | Optional für schöne Integration |

---

## Troubleshooting

### ESP8266 verbindet nicht mit Flipper
1. **MAC-Adresse prüfen:** `bleak --scan`
2. **Flipper BLE einschalten:** In OpenTonies App → Setup → Bluetooth = AN
3. **Abstand prüfen:** Max. 5-10 Meter
4. **Störquellen vermeiden:** Andere BLE-Geräte in der Nähe

### ESP8266 startet nicht
1. **Serielle Monitor prüfen:** `screen /dev/ttyUSB0 115200`
2. **Stromversorgung prüfen:** Mindestens 5V, 500mA
3. **Firmware prüfen:** MicroPython oder ESPHome korrekt geflasht?

### HTTP-API antwortet nicht
1. **ESP-IP prüfen:** `ping opentonies-bridge.local`
2. **Port prüfen:** Standardmäßig Port 80
3. **Firewall prüfen:** Lokales Netzwerk erlaubt HTTP?

---

## Nächste Schritte

1. **ESP8266 vorbereiten** (MicroPython oder ESPHome)
2. **Flipper MAC-Adresse ermitteln**
3. **Bridge konfigurieren** (WLAN, Flipper MAC)
4. **Bridge flashen und testen**
5. **Web-App anpassen** für iOS
6. **Test mit iPhone**

---

## Links

- [MicroPython](https://micropython.org/)
- [ESPHome](https://esphome.io/)
- [Flipper Zero BLE Dokumentation](https://github.com/flipperdevices/flipperzero-firmware/tree/dev/.github/scripts/ble)
- [Nordic Serial Service Spezifikation](https://www.bluetooth.com/specifications/specs/nordic-serial-service/)
