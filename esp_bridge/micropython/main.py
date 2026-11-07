"""
OpenTonies ESP8266 BLE Bridge - MicroPython Implementierung

Diese Bridge ermöglicht iOS-Geräten (die kein WebBluetooth unterstützen) 
die OpenTonies Web-App zu nutzen.

Kommunikation:
- ESP8266 <-> Flipper Zero: BLE (Nordic Serial Service)
- ESP8266 <-> Web-App: HTTP/REST auf Port 80

Voraussetzungen:
- MicroPython auf ESP8266/ESP32
- ble_advertising Modul (für BLE Central)

Installation:
1. MicroPython Firmware flashen
2. Diese Datei als main.py auf den ESP kopieren
3. config.json anpassen (WLAN, Flipper MAC)
4. ESP starten - er verbindet sich mit WLAN und BLE

API Endpunkte:
- GET /ping                    - Testverbindung
- POST /ble/send              - Befehl an Flipper senden
- GET /ble/response           - Letzte Flipper-Antwort
- GET /ble/status             - Verbindungsstatus
- GET /ble/connect?mac=XX:XX  - Mit Flipper verbinden
- GET /ble/disconnect         - Verbindung trennen
- GET /ble/scan               - Available BLE devices scannen
"""

import json
import time
import socket
import network
import ubinascii
from machine import Pin

# ==================== KONFIGURATION ====================
try:
    with open("config.json", "r") as f:
        config = json.load(f)
except:
    # Fallback Konfiguration
    config = {
        "wifi": {
            "ssid": "YOUR_WIFI_SSID",
            "password": "YOUR_WIFI_PASSWORD"
        },
        "flipper": {
            "mac": "A4:CF:12:XX:XX:XX",  # Flipper Zero BLE MAC
            "auto_connect": True
        },
        "bridge": {
            "host": "0.0.0.0",
            "port": 80,
            "timeout": 30
        },
        "status_led": {
            "pin": 2,  # D4 auf NodeMCU
            "active_low": True
        }
    }

# ==================== GLOBALER STATE ====================
class State:
    def __init__(self):
        self.ble_connected = False
        self.flipper_mac = config["flipper"]["mac"]
        self.last_response = ""
        self.last_command = ""
        self.flipper_characteristic = None
        self.ble_device = None
        self.wifi_connected = False
        self.server_socket = None

state = State()

# ==================== STATUS LED ====================
class StatusLED:
    def __init__(self, pin_num, active_low=True):
        self.pin = Pin(pin_num, Pin.OUT)
        self.active_low = active_low
        self.off()
    
    def on(self):
        self.pin.value(0 if self.active_low else 1)
    
    def off(self):
        self.pin.value(1 if self.active_low else 0)
    
    def blink(self, times=1, duration=0.2):
        for _ in range(times):
            self.on()
            time.sleep(duration)
            self.off()
            time.sleep(duration)

led = StatusLED(
    pin_num=config["status_led"]["pin"],
    active_low=config["status_led"]["active_low"]
)

# ==================== WLAN ====================
def connect_wifi():
    """Verbinde mit WLAN"""
    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)
    
    if not sta_if.isconnected():
        print(f"Verbindung zu {config['wifi']['ssid']}...")
        sta_if.connect(config["wifi"]["ssid"], config["wifi"]["password"])
        
        # Warten auf Verbindung
        max_wait = 20
        while not sta_if.isconnected() and max_wait > 0:
            led.blink(1, 0.1)
            time.sleep(1)
            max_wait -= 1
    
    if sta_if.isconnected():
        print(f"WLAN verbunden! IP: {sta_if.ifconfig()[0]}")
        state.wifi_connected = True
        led.on()
        return sta_if.ifconfig()[0]
    else:
        print("WLAN Verbindung fehlgeschlagen!")
        # Fallback: Access Point Modus
        ap_if = network.WLAN(network.AP_IF)
        ap_if.active(True)
        ap_if.config(essid="OpenTonies-Bridge")
        print(f"Fallback AP gestartet! SSID: OpenTonies-Bridge, IP: {ap_if.ifconfig()[0]}")
        led.blink(3, 0.1)
        return ap_if.ifconfig()[0]

# ==================== BLE KONNEKTIVITÄT ====================
def scan_ble_devices(duration=5):
    """Scanne nach BLE-Geräten"""
    # Try to import ble_advertising
    try:
        from ble_advertising import decode_name, decode_services
        import bluetooth
    except ImportError:
        print("ERROR: ble_advertising Modul nicht gefunden!")
        print("Installiere es mit: micropython -m upip install ble-advertising")
        return []
    
    devices = []
    print("BLE Scan gestartet...")
    
    try:
        bluetooth.active(True)
        bluetooth.irq(None)  # Clear any pending IRQs
        
        # Scan für BLE Devices
        for _ in range(duration * 2):  # ~2 scans per second
            adv = bluetooth.get_adv()
            if adv:
                mac = ubinascii.hexlify(adv[0]).decode()
                mac = ":".join(mac[i:i+2] for i in range(0, len(mac), 2))
                
                # Decode name
                name = decode_name(adv) or "Unknown"
                
                # Check for Flipper Zero
                if "Flipper" in name or "Momentum" in name:
                    print(f"  Flipper gefunden: {name} ({mac})")
                
                devices.append({
                    "mac": mac,
                    "name": name,
                    "rssi": adv[4] if len(adv) > 4 else 0
                })
            
            time.sleep(0.5)
    except Exception as e:
        print(f"BLE Scan Fehler: {e}")
    
    return devices

def connect_ble(mac_address=None):
    """Verbinde mit Flipper Zero über BLE"""
    try:
        from ble_advertising import decode_name, decode_services
        import bluetooth
    except ImportError:
        print("ERROR: ble_advertising Modul nicht gefunden!")
        return False
    
    target_mac = mac_address or state.flipper_mac
    
    # MAC formatieren (ohne Doppelpunkte)
    target_mac_clean = target_mac.replace(":", "").lower()
    target_mac_bytes = ubinascii.unhexlify(target_mac_clean)
    
    print(f"Verbindung zu Flipper Zero ({target_mac})...")
    led.blink(2, 0.1)
    
    try:
        bluetooth.active(True)
        
        # Zuerst scannen, ob das Gerät verfügbar ist
        devices = scan_ble_devices(duration=3)
        found = any(d["mac"] == target_mac for d in devices)
        
        if not found:
            print(f"Flipper mit MAC {target_mac} nicht gefunden!")
            return False
        
        # Verbindung herstellen
        state.ble_device = bluetooth.BLE(target_mac_bytes)
        state.ble_connected = True
        
        # Serial Service Characteristics finden
        # Nordic Serial Service UUIDs
        SERIAL_SERVICE_UUID = ubinascii.unhexlify("0000180d00001000800000805f9b34fb")
        RX_CHAR_UUID = ubinascii.unhexlify("0000201200001000800000805f9b34fb")
        TX_CHAR_UUID = ubinascii.unhexlify("0000201300001000800000805f9b34fb")
        
        # Service und Characteristics finden
        services = state.ble_device.gattc_services()
        for service in services:
            if service.uuid == SERIAL_SERVICE_UUID:
                print("Serial Service gefunden!")
                characteristics = state.ble_device.gattc_characteristics(service.start_handle, service.end_handle)
                for char in characteristics:
                    if char.uuid == RX_CHAR_UUID:
                        state.flipper_characteristic = char
                        print("RX Characteristic gefunden!")
                        
                    if char.uuid == TX_CHAR_UUID:
                        # Enable notifications
                        state.ble_device.gattc_write(char.value_handle + 1, b"\x01\x00")
                        print("TX Characteristic gefunden, Notifications aktiviert!")
        
        if state.flipper_characteristic:
            print("BLE Verbindung erfolgreich!")
            led.on()
            return True
        else:
            print("RX Characteristic nicht gefunden!")
            disconnect_ble()
            return False
            
    except Exception as e:
        print(f"BLE Verbindung fehlgeschlagen: {e}")
        disconnect_ble()
        return False

def disconnect_ble():
    """Trenne BLE-Verbindung"""
    if state.ble_connected:
        try:
            if state.ble_device:
                state.ble_device.gattc_disconnect()
            state.ble_connected = False
            state.flipper_characteristic = None
            state.ble_device = None
            print("BLE Verbindung getrennt")
            led.blink(1, 0.1)
        except Exception as e:
            print(f"Fehler beim Trennen: {e}")

def send_ble_command(command):
    """Sende Befehl an Flipper über BLE"""
    if not state.ble_connected or not state.flipper_characteristic:
        return False, "Nicht verbunden"
    
    try:
        # Befehl als Bytes senden (mit Zeilenende)
        cmd_bytes = (command + "\n").encode("utf-8")
        state.ble_device.gattc_write(state.flipper_characteristic.value_handle, cmd_bytes)
        state.last_command = command
        return True, "Gesendet"
    except Exception as e:
        return False, f"Fehler: {e}"

# ==================== HTTP SERVER ====================
def handle_client(cl_socket):
    """Behandle HTTP-Anfrage"""
    try:
        request = cl_socket.recv(1024).decode("utf-8")
        if not request:
            return
        
        print(f"Request: {request.split(chr(10))[0]}")
        
        # Request parsen
        lines = request.split("\r\n")
        if not lines:
            return
        
        # Erste Zeile: METHOD PATH HTTP/1.1
        first_line = lines[0].strip()
        parts = first_line.split()
        if len(parts) < 2:
            return
        
        method = parts[0]
        path = parts[1]
        
        # Body extrahieren
        body = ""
        if method in ["POST", "PUT"]:
            body_start = request.find("\r\n\r\n") + 4
            if body_start > 3:
                body = request[body_start:]
                if "Content-Length" in request:
                    # Content-Length parsen
                    for line in lines:
                        if "Content-Length" in line:
                            cl = int(line.split(":")[1].strip())
                            body = request[body_start:body_start+cl]
                            break
        
        # Routing
        response_body = ""
        response_code = 200
        content_type = "text/plain"
        
        if path == "/ping":
            response_body = "PONG"
        
        elif path == "/ble/status":
            content_type = "application/json"
            response_body = json.dumps({
                "ble_status": "connected" if state.ble_connected else "disconnected",
                "flipper_mac": state.flipper_mac,
                "wifi_connected": state.wifi_connected
            })
        
        elif path == "/ble/response":
            content_type = "application/json"
            response_body = json.dumps({"response": state.last_response})
            state.last_response = ""  # Reset
        
        elif path == "/ble/connect":
            # MAC aus Query-Param extrahieren
            if "?mac=" in path:
                mac = path.split("?mac=")[1].split("&")[0]
                state.flipper_mac = mac
                config["flipper"]["mac"] = mac
                with open("config.json", "w") as f:
                    json.dump(config, f)
            
            if connect_ble():
                content_type = "application/json"
                response_body = json.dumps({"status": "connected", "mac": state.flipper_mac})
            else:
                response_code = 500
                content_type = "application/json"
                response_body = json.dumps({"status": "error", "message": "Verbindung fehlgeschlagen"})
        
        elif path == "/ble/disconnect":
            disconnect_ble()
            content_type = "application/json"
            response_body = json.dumps({"status": "disconnected"})
        
        elif path == "/ble/send" and method == "POST":
            try:
                cmd_data = json.loads(body)
                command = cmd_data.get("command", "")
                success, message = send_ble_command(command)
                content_type = "application/json"
                response_body = json.dumps({
                    "status": "sent" if success else "error",
                    "command": command,
                    "message": message
                })
            except:
                response_code = 400
                response_body = json.dumps({"status": "error", "message": "Ungültige Anfrage"})
        
        elif path == "/ble/scan":
            devices = scan_ble_devices(duration=3)
            content_type = "application/json"
            response_body = json.dumps({"devices": devices})
        
        else:
            response_code = 404
            response_body = "Not Found"
        
        # Response senden
        cl_socket.send(f"HTTP/1.1 {response_code} OK\r\n".encode())
        cl_socket.send(f"Content-Type: {content_type}\r\n".encode())
        cl_socket.send(f"Content-Length: {len(response_body)}\r\n".encode())
        cl_socket.send(f"Access-Control-Allow-Origin: *\r\n".encode())
        cl_socket.send(f"Connection: close\r\n\r\n".encode())
        cl_socket.send(response_body.encode())
        
    except Exception as e:
        print(f"Fehler bei Anfrage: {e}")
        try:
            cl_socket.send(b"HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/plain\r\n\r\nError")
        except:
            pass
    finally:
        cl_socket.close()

def start_http_server():
    """Starte HTTP-Server"""
    addr = socket.getaddrinfo("0.0.0.0", config["bridge"]["port"])[0][-1]
    
    state.server_socket = socket.socket()
    state.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    state.server_socket.bind(addr)
    state.server_socket.listen(1)
    
    print(f"HTTP Server gestartet auf {addr[0]}:{addr[1]}")
    
    while True:
        try:
            cl_socket, cl_addr = state.server_socket.accept()
            print(f"Verbindung von: {cl_addr}")
            handle_client(cl_socket)
        except Exception as e:
            print(f"Server Fehler: {e}")
            time.sleep(1)

# ==================== SETUP MULTICAST DNS (mDNS) ====================
def setup_mdns():
    """mDNS für opentonies-bridge.local einrichten"""
    try:
        import usocket as socket
        import struct
        
        # mDNS ist komplex in MicroPython - wir nutzen statische IP oder Hostname
        # Falls verfügbar: esp32_mdns oder ähnlich
        try:
            import esp32
            esp32.mdns_start("opentonies-bridge", "_http._tcp", 80)
            print("mDNS gestartet: opentonies-bridge.local")
        except:
            print("mDNS nicht verfügbar - verwende IP-Adresse")
    except Exception as e:
        print(f"mDNS Setup fehlgeschlagen: {e}")

# ==================== HAUPTPROGRAMM ====================
def main():
    print("=" * 50)
    print("OpenTonies ESP8266 BLE Bridge")
    print("=" * 50)
    print()
    
    # WLAN verbinden
    ip = connect_wifi()
    if not ip:
        print("Kritischer Fehler: Keine Netzwerkverbindung!")
        led.blink(5, 0.1)
        return
    
    # mDNS einrichten
    setup_mdns()
    
    # Automatisch mit Flipper verbinden (falls configured)
    if config["flipper"].get("auto_connect", True):
        time.sleep(2)  # Warten auf WLAN
        if not connect_ble():
            print("Automatische BLE-Verbindung fehlgeschlagen. Manuell mit /ble/connect verbinden.")
    
    # HTTP Server starten
    print()
    print("Bridge bereit!")
    print(f"  IP: {ip}")
    print(f"  BLE: {'verbunden' if state.ble_connected else 'nicht verbunden'}")
    print(f"  URL: http://{ip} oder http://opentonies-bridge.local")
    print()
    print("Endpunkte:")
    print("  GET /ping")
    print("  GET /ble/status")
    print("  GET /ble/connect?mac=XX:XX:XX:XX:XX:XX")
    print("  POST /ble/send -d '{\"command\":\"PING\\n\"}'")
    print()
    
    # Server starten
    start_http_server()

if __name__ == "__main__":
    main()
