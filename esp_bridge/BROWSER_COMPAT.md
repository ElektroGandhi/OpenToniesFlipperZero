# Browser und Web Bluetooth

Die Web-App spricht den Flipper direkt über Web Bluetooth an, wenn der Browser das kann.
Diese Übersicht beruht auf den Angaben der Browser-Hersteller. Am echten Gerät mit OpenTonies
ist die Bluetooth-Kette **noch ungeprüft**.

| Browser | Web Bluetooth | Weg |
|---|---|---|
| Chrome, Edge (Android, Windows, macOS) | ja | direkt |
| Samsung Internet, Opera (Android) | ja | direkt |
| Chrome unter Linux | nur mit gesetztem Flag | Flag oder Brücke |
| Firefox (alle Systeme) | nein | anderer Browser oder Brücke |
| Safari, Chrome, Edge auf dem iPhone | nein, alle nutzen WebKit | [Bluefy](https://apps.apple.com/app/bluefy-web-ble-browser/id1492822055) oder Brücke |

Die Seite muss über **HTTPS oder localhost** laufen, sonst verweigert der Browser Bluetooth.

Die Brücke ist optional und in [`README.md`](README.md) beschrieben.
