/**
 * OpenTonies ESP8266 Bridge Support für iOS (Optional)
 * 
 * Diese Datei fügt Unterstützung für die ESP8266 BLE Bridge hinzu,
 * damit iOS-Geräte in Safari (die kein WebBluetooth unterstützen) die Web-App nutzen können.
 * 
 * **Hinweis:** Die Bridge ist optional! Moderne Browser (Chrome, Edge, WebBLE im App Store)
 * unterstützen WebBluetooth und können direkt mit dem Flipper kommunizieren.
 * 
 * Verwendung:
 *   1. Diese Datei in die Web-App einbinden:
 *      <script src="opentonies_bridge.js"></script>
 *   2. Zuerst direktes BLE versuchen, bei Fehler auf Bridge fallen
 * 
 * API:
 *   - OpenToniesBridge.isSupported() - Prüft ob Bridge benötigt wird
 *   - OpenToniesBridge.connect(mac) - Verbindet mit Flipper über Bridge
 *   - OpenToniesBridge.disconnect() - Trennt Verbindung
 *   - OpenToniesBridge.sendCommand(cmd) - Sendet Befehl an Flipper
 *   - OpenToniesBridge.getStatus() - Hole Verbindungsstatus
 *   - OpenToniesBridge.scan() - Scannt nach verfügbaren Flippers
 */

class OpenToniesBridge {
    
    /**
     * Standard-Bridge-URL (kann überschrieben werden)
     * mDNS: opentonies-bridge.local (falls verfügbar)
     * Fallback: IP-Adresse des ESP8266
     */
    static BRIDGE_URL = null;
    
    /**
     * Timeout für HTTP-Anfragen in ms
     */
    static TIMEOUT = 10000;
    
    /**
     * Letzte Antwort vom Flipper
     */
    static lastResponse = "";
    
    /**
     * Callbacks für Event-Handling
     */
    static callbacks = {
        onConnect: null,
        onDisconnect: null,
        onResponse: null,
        onError: null,
        onScan: null
    };
    
    /**
     * Prüft ob eine Bridge benötigt wird (iOS oder kein WebBluetooth)
     * @returns {boolean} true wenn Bridge benötigt wird
     */
    static isSupported() {
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        const hasWebBluetooth = navigator.bluetooth !== undefined;
        
        return isIOS || !hasWebBluetooth;
    }
    
    /**
     * Prüft ob eine Bridge verfügbar ist
     * @returns {Promise<boolean>}
     */
    static async isAvailable() {
        if (!this.BRIDGE_URL) {
            // Versuche mDNS zuerst
            this.BRIDGE_URL = "http://opentonies-bridge.local";
        }
        
        try {
            const response = await fetch(`${this.BRIDGE_URL}/ping`, {
                method: "GET",
                signal: AbortSignal.timeout(this.TIMEOUT)
            });
            return response.ok && (await response.text()) === "PONG";
        } catch (error) {
            console.log("Bridge nicht unter mDNS erreichbar, versuche IP-Fallback...");
            // Versuche mit häufigen IP-Adressen
            const fallbackIPs = [
                "http://192.168.1.100",
                "http://10.0.0.100",
                "http://172.16.0.100"
            ];
            
            for (const ip of fallbackIPs) {
                try {
                    const response = await fetch(`${ip}/ping`, {
                        method: "GET",
                        signal: AbortSignal.timeout(this.TIMEOUT / 2)
                    });
                    if (response.ok && (await response.text()) === "PONG") {
                        this.BRIDGE_URL = ip;
                        console.log(`Bridge gefunden unter: ${ip}`);
                        return true;
                    }
                } catch (e) {
                    // Ignorieren und nächste IP versuchen
                }
            }
            
            return false;
        }
    }
    
    /**
     * Setzt die Bridge-URL manuell
     * @param {string} url - Komplette URL zur Bridge (z.B. "http://192.168.1.100")
     */
    static setBridgeURL(url) {
        this.BRIDGE_URL = url;
        localStorage.setItem("opentonies_bridge_url", url);
    }
    
    /**
     * Lädt die gespeicherte Bridge-URL
     */
    static loadBridgeURL() {
        const saved = localStorage.getItem("opentonies_bridge_url");
        if (saved) {
            this.BRIDGE_URL = saved;
        }
    }
    
    /**
     * Verbindet mit Flipper über die Bridge
     * @param {string} mac - BLE MAC-Adresse des Flippers (optional)
     * @returns {Promise<Object>} Status-Objekt
     */
    static async connect(mac = null) {
        if (!this.BRIDGE_URL) {
            const available = await this.isAvailable();
            if (!available) {
                throw new Error("Bridge nicht verfügbar. Bitte ESP8266 starten.");
            }
        }
        
        const url = mac ? `${this.BRIDGE_URL}/ble/connect?mac=${encodeURIComponent(mac)}` : `${this.BRIDGE_URL}/ble/connect`;
        
        try {
            const response = await fetch(url, {
                method: "GET",
                signal: AbortSignal.timeout(this.TIMEOUT)
            });
            
            const data = await response.json();
            
            if (data.status === "connected") {
                this.emit("onConnect", data);
                return data;
            } else {
                throw new Error(data.message || "Verbindung fehlgeschlagen");
            }
        } catch (error) {
            this.emit("onError", {type: "connect", error: error.message});
            throw error;
        }
    }
    
    /**
     * Trennt die Verbindung
     * @returns {Promise<Object>}
     */
    static async disconnect() {
        if (!this.BRIDGE_URL) return {status: "disconnected"};
        
        try {
            const response = await fetch(`${this.BRIDGE_URL}/ble/disconnect`, {
                method: "GET",
                signal: AbortSignal.timeout(this.TIMEOUT)
            });
            
            const data = await response.json();
            this.emit("onDisconnect", data);
            return data;
        } catch (error) {
            this.emit("onError", {type: "disconnect", error: error.message});
            throw error;
        }
    }
    
    /**
     * Sendet einen Befehl an den Flipper über die Bridge
     * @param {string} command - Der Befehl (ohne Zeilenende, wird automatisch hinzugefügt)
     * @returns {Promise<Object>}
     */
    static async sendCommand(command) {
        if (!this.BRIDGE_URL) {
            const available = await this.isAvailable();
            if (!available) {
                throw new Error("Bridge nicht verfügbar");
            }
        }
        
        try {
            // Zeilenende hinzufügen (Flipper erwartet \n)
            const cmdWithNewline = command.endsWith("\n") ? command : command + "\n";
            
            const response = await fetch(`${this.BRIDGE_URL}/ble/send`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({command: cmdWithNewline}),
                signal: AbortSignal.timeout(this.TIMEOUT)
            });
            
            const data = await response.json();
            
            if (data.status === "sent") {
                // Kurze Pause für Antwort
                await new Promise(resolve => setTimeout(resolve, 100));
                
                // Antwort abrufen
                const respResponse = await fetch(`${this.BRIDGE_URL}/ble/response`, {
                    method: "GET",
                    signal: AbortSignal.timeout(this.TIMEOUT)
                });
                
                const respData = await respResponse.json();
                if (respData.response) {
                    this.lastResponse = respData.response;
                    this.emit("onResponse", respData.response);
                }
            }
            
            return data;
        } catch (error) {
            this.emit("onError", {type: "send", error: error.message, command});
            throw error;
        }
    }
    
    /**
     * Hole den aktuellen Verbindungsstatus
     * @returns {Promise<Object>}
     */
    static async getStatus() {
        if (!this.BRIDGE_URL) {
            return {ble_status: "unknown", wifi_connected: false};
        }
        
        try {
            const response = await fetch(`${this.BRIDGE_URL}/ble/status`, {
                method: "GET",
                signal: AbortSignal.timeout(this.TIMEOUT)
            });
            return await response.json();
        } catch (error) {
            return {ble_status: "error", error: error.message};
        }
    }
    
    /**
     * Scannt nach verfügbaren Flipper-Geräten
     * @returns {Promise<Array>} Liste der gefundenen Geräte
     */
    static async scan() {
        if (!this.BRIDGE_URL) {
            const available = await this.isAvailable();
            if (!available) {
                throw new Error("Bridge nicht verfügbar");
            }
        }
        
        try {
            const response = await fetch(`${this.BRIDGE_URL}/ble/scan`, {
                method: "GET",
                signal: AbortSignal.timeout(this.TIMEOUT)
            });
            
            const data = await response.json();
            this.emit("onScan", data.devices);
            return data.devices;
        } catch (error) {
            this.emit("onError", {type: "scan", error: error.message});
            throw error;
        }
    }
    
    /**
     * Registriert einen Callback für Events
     * @param {string} eventName - Event-Name (onConnect, onDisconnect, onResponse, onError, onScan)
     * @param {Function} callback - Callback-Funktion
     */
    static on(eventName, callback) {
        this.callbacks[eventName] = callback;
    }
    
    /**
     * Emittiert ein Event an alle registrierten Callbacks
     * @param {string} eventName - Event-Name
     * @param {...any} args - Argumente für den Callback
     */
    static emit(eventName, ...args) {
        const callback = this.callbacks[eventName];
        if (callback) {
            try {
                callback(...args);
            } catch (error) {
                console.error(`Fehler im ${eventName}-Callback:`, error);
            }
        }
    }
    
    /**
     * Gibt die letzte Antwort vom Flipper zurück
     * @returns {string}
     */
    static getLastResponse() {
        return this.lastResponse;
    }
}

// Lade gespeicherte Bridge-URL beim Laden
OpenToniesBridge.loadBridgeURL();

// Export für CommonJS/Node.js Umgebungen (falls gebraucht)
if (typeof module !== "undefined" && module.exports) {
    module.exports = OpenToniesBridge;
}
