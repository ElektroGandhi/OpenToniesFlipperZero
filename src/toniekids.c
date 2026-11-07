// Tonie Box - kinderfreundliches, grafisches Menue im HOCHFORMAT (64x128).
// Ebene 1: Serien.  Ebene 2: Geschichten.  Grosses Bild (64x96) + Name.
// OK auf einer Geschichte emuliert die SLIX-L-Figur direkt fuer die Toniebox.

#include <furi.h>
#include <stdarg.h>
#include <gui/gui.h>
#include <input/input.h>
#include <storage/storage.h>
#include <nfc/nfc.h>
#include <nfc/nfc_device.h>
#include <nfc/nfc_listener.h>
#include <furi_hal_light.h>
#include <furi_hal_resources.h>
#include <furi_hal_bt.h>
#include <bt/bt_service/bt.h>
#include <profiles/serial_profile.h>

#define TONIE_DIR "/ext/nfc/Toniebox Figuren"
#define ICON_DIR  "/ext/apps_data/toniekids/icons_p" // Hochformat 64x96
#define ICON_W    64
#define ICON_H    96
#define ICON_MAX_BYTES ((ICON_W / 8) * ICON_H) // 768
#define FAV_FILE "/ext/apps_data/toniekids/favorites.txt"
#define SETTINGS_FILE "/ext/apps_data/toniekids/settings.txt"
#define DURATIONS_FILE "/ext/apps_data/toniekids/durations.txt"
#define LOG_FILE "/ext/apps_data/toniekids/log.txt"

// --- Fernsteuerung per Bluetooth (Handy-Bibliothek) ---
// Eigener Schluesselspeicher: das Pairing der Web-App darf das System-Pairing des
// Flippers (offizielle App) nicht ueberschreiben.
#define BLE_KEYS_FILE "/ext/apps_data/toniekids/ble_keys.bin"
#define BLE_RX_LINE_MAX 192 // laengste Befehlszeile, die wir annehmen
#define BLE_TX_CHUNK 200    // < BLE_SVC_SERIAL_CHAR_VALUE_LEN_MAX (243)
#define BLE_TX_RETRY 25     // Flow-Control: so oft auf freien Puffer warten

// LED-Farbpalette (Light-Kanalmasken) + Anzeigenamen
static const uint8_t LED_COLOR_MASK[] = {
    LightGreen | LightBlue,            // Zyan
    LightBlue,                         // Blau
    LightGreen,                        // Gruen
    LightRed,                          // Rot
    LightRed | LightBlue,              // Magenta
    LightRed | LightGreen,             // Gelb
    LightRed | LightGreen | LightBlue, // Weiss
};
static const char* const LED_COLOR_NAME[] =
    {"Zyan", "Blau", "Gruen", "Rot", "Magenta", "Gelb", "Weiss"};
#define LED_COLOR_COUNT 7
static const uint8_t LED_BRIGHT_VAL[] = {30, 120, 255};
static const char* const LED_BRIGHT_NAME[] = {"niedrig", "mittel", "hoch"};
#define LED_BRIGHT_COUNT 3
// Auto-Timer: Index 0 = Aus; sonst Fallback-Minuten (echte Spieldauer hat Vorrang).
static const uint16_t TIMER_MIN[] = {0, 30, 45, 60, 90};
static const char* const TIMER_NAME[] = {"Aus", "30 min", "45 min", "60 min", "90 min"};
#define TIMER_COUNT 5
// Puffer: Spielraum, der auf jede Timer-Zeit aufgeschlagen wird. Spieldauern sind
// gerundet, und bis die Box zu spielen beginnt, vergeht auch etwas Zeit - ohne Puffer
// bricht die Emulation sonst kurz vor dem Ende der Geschichte ab.
static const uint8_t PUFFER_MIN[] = {0, 5, 10, 15, 20, 30};
static const char* const PUFFER_NAME[] = {"+0 min", "+5 min", "+10 min", "+15 min", "+20 min", "+30 min"};
#define PUFFER_COUNT 6
#define PUFFER_DEFAULT 1 // +5 min, auch fuer vorhandene settings.txt ohne den Schluessel
// Laufschrift-Tempo: Index 0 = Aus; sonst 1/8-Pixel pro Tick (Timer alle 120 ms).
// Sub-Pixel erlaubt sehr langsame Stufen (~px/s ≈ Wert): 2≈langsam-langsam, 14≈flott.
static const uint8_t SCROLL_STEP[] = {0, 2, 4, 8, 14};
static const char* const SCROLL_NAME[] =
    {"Aus", "sehr langsam", "langsam", "mittel", "schnell"};
#define SCROLL_COUNT 5
#define SETTINGS_COUNT 11
static const char* const SETTING_LABEL[] = {"Schrift",    "Bilder",      "LED",
                                            "LED-Farbe",  "Helligkeit",  "Auto-Timer",
                                            "Puffer",     "Aktion",      "Laufschrift",
                                            "Log",        "Bluetooth"};

// 13x13 Stern (Favoriten-Marker), XBM LSB-first
static const uint8_t star_bits[] = {
    0x40, 0x00, 0x60, 0x00, 0xe0, 0x00, 0xf0, 0x00, 0xff, 0x0f, 0xfc, 0x03, 0xf8,
    0x01, 0xf8, 0x01, 0xf8, 0x01, 0xbc, 0x03, 0x0c, 0x03, 0x04, 0x02, 0x00, 0x00};

typedef enum { ScreenSeries, ScreenEpisode, ScreenPlay, ScreenSettings } Screen;

typedef struct {
    char** items;
    size_t count;
    size_t cap;
} StrList;

typedef struct {
    uint8_t buf[ICON_MAX_BYTES];
    uint8_t w, h;
    bool valid;
} TkIcon;

typedef struct {
    FuriMutex* mutex;
    Gui* gui;
    ViewPort* view_port;
    FuriMessageQueue* queue;
    Storage* storage;

    Screen screen;
    StrList series;
    size_t series_idx;
    StrList episodes;
    size_t episode_idx;
    StrList favorites;

    TkIcon ic;

    Nfc* nfc;
    NfcDevice* dev;
    NfcListener* listener;
    bool emulating;

    // Einstellungen (versteckte Setup-Seite, langes Zurueck auf der Serien-/Episoden-Ebene)
    bool opt_uppercase;     // Namen in GROSSBUCHSTABEN
    bool opt_hide_images;   // Bilder ausblenden (Lesen lernen ohne Spickzettel)
    bool opt_led_on;        // LED-Blink waehrend Emulation
    uint8_t opt_led_color;  // Index in LED_COLOR_*
    uint8_t opt_led_bright; // Index in LED_BRIGHT_*
    uint8_t opt_timer_idx;  // Index in TIMER_* (0 = Aus)
    uint8_t opt_puffer_idx; // Index in PUFFER_* (Spielraum auf die Timer-Zeit)
    bool opt_timer_action;  // false = Aus (Strom sparen), true = Replay-Bounce
    uint8_t opt_scroll;     // Laufschrift-Tempo: 0=Aus, 1..4 = sehr langsam..schnell
    bool opt_log;           // Diagnose-Log nach log.txt schreiben
    bool opt_ble;           // Fernsteuerung per Bluetooth (Handy-Bibliothek)
    size_t settings_idx;    // markierter Eintrag in der Setup-Seite

    // --- Bluetooth-Fernsteuerung ---
    Bt* bt;
    FuriHalBleProfileBase* ble_profile;
    bool ble_on;        // Profil laeuft (nur Hauptthread schreibt)
    bool ble_connected; // aus dem Status-Callback
    FuriMutex* ble_mutex;            // schuetzt NUR ble_cmd/ble_cmd_pending
    char ble_rx[BLE_RX_LINE_MAX];    // Zeilenpuffer, nur der BLE-Thread fasst ihn an
    size_t ble_rx_len;
    bool ble_rx_over;                // true = zu lange Zeile, gesamte Zeile bis '\n' verwerfen
    char ble_cmd[BLE_RX_LINE_MAX];   // fertige Zeile fuer die Hauptschleife
    bool ble_cmd_pending;

    FuriTimer* timer;         // Auto-Aus/Replay-Timer
    bool timer_fired;         // vom Timer gesetzt, in der Hauptschleife behandelt
    bool replay_pending;      // true = 5s-Pause vor Wiederaufstellen laeuft
    FuriTimer* scroll_timer;  // periodischer Tick fuer die Laufschrift
    uint16_t scroll_off;      // aktueller Marquee-Versatz (Pixel)

    bool running;
} App;

// ---------- StrList ----------
static void strlist_init(StrList* l) {
    l->items = NULL;
    l->count = 0;
    l->cap = 0;
}
static void strlist_append(StrList* l, const char* s) {
    if(l->count == l->cap) {
        size_t ncap = l->cap ? l->cap * 2 : 16;
        char** ni = realloc(l->items, ncap * sizeof(char*));
        if(!ni) return;
        l->items = ni;
        l->cap = ncap;
    }
    char* cp = strdup(s);
    if(!cp) return; // OOM: keinen NULL-Eintrag in die Liste haengen
    l->items[l->count++] = cp;
}
static void strlist_clear(StrList* l) {
    for(size_t i = 0; i < l->count; i++) free(l->items[i]);
    free(l->items);
    l->items = NULL;
    l->count = 0;
    l->cap = 0;
}
static void strlist_sort(StrList* l) {
    for(size_t i = 1; i < l->count; i++) {
        char* key = l->items[i];
        size_t j = i;
        while(j > 0 && strcmp(l->items[j - 1], key) > 0) {
            l->items[j] = l->items[j - 1];
            j--;
        }
        l->items[j] = key;
    }
}
static bool ends_with_nfc(const char* name) {
    size_t n = strlen(name);
    return n > 4 && strcmp(name + n - 4, ".nfc") == 0;
}
static void strip_nfc(const char* in, char* out, size_t out_sz) {
    size_t n = strlen(in);
    if(n > 4 && strcmp(in + n - 4, ".nfc") == 0) n -= 4;
    if(n > out_sz - 1) n = out_sz - 1;
    memcpy(out, in, n);
    out[n] = 0;
}
// Serien-Praefix aus dem Episodentitel entfernen: Ebene 2 zeigt nur die Episode.
// Greift nur, wenn der Titel exakt mit dem Serien-Namen beginnt (z. B.
// "Bibi Blocksberg - Englisch lernen" -> "Englisch lernen").
static const char* strip_series_prefix(const char* title, const char* series) {
    size_t sl = strlen(series);
    if(sl > 0 && strncmp(title, series, sl) == 0) {
        const char* p = title + sl;
        while(*p == ' ' || *p == '-' || *p == '_' || *p == ':' || *p == '.') p++;
        if(*p) return p; // nur wenn danach noch Text folgt
    }
    return title;
}
// UTF-8-bewusstes Grossschreiben: ASCII a-z + Latin-1-Kleinbuchstaben
// (C3 A0..BE -> C3 80..9E, deckt aeoeue etc. ab). Byte-laengenerhaltend; ss bleibt.
static void to_upper(const char* in, char* out, size_t out_sz) {
    size_t o = 0;
    for(size_t i = 0; in[i] && o + 1 < out_sz;) {
        unsigned char c = (unsigned char)in[i];
        unsigned char d = (unsigned char)in[i + 1];
        if(c >= 'a' && c <= 'z') {
            out[o++] = (char)(c - 32);
            i++;
        } else if(c == 0xC3 && d >= 0xA0 && d <= 0xBE && d != 0xB7) {
            if(o + 2 >= out_sz) break;
            out[o++] = (char)0xC3;
            out[o++] = (char)(d - 0x20);
            i += 2;
        } else {
            out[o++] = (char)c;
            i++;
        }
    }
    out[o] = 0;
}

// ---------- Diagnose ----------
static void diag_write(App* app, const char* line, bool truncate) {
    storage_common_mkdir(app->storage, "/ext/apps_data/toniekids");
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(
           f, "/ext/apps_data/toniekids/diag.txt", FSAM_WRITE,
           truncate ? FSOM_CREATE_ALWAYS : FSOM_OPEN_APPEND)) {
        storage_file_write(f, line, strlen(line));
    }
    storage_file_close(f);
    storage_file_free(f);
}

// ---------- Log (umschaltbar im Setup) ----------
// Frisches Log mit Kopfzeile (Einstellungs-Snapshot) — bei Aktivierung/Start.
static void log_start(App* app) {
    if(!app->opt_log) return;
    storage_common_mkdir(app->storage, "/ext/apps_data/toniekids");
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(f, LOG_FILE, FSAM_WRITE, FSOM_CREATE_ALWAYS)) {
        char l[176];
        int m = snprintf(
            l, sizeof(l), "== OpenTonies Log ==\n[%lu] timer=%s aktion=%s laufschrift=%s led=%d\n",
            (unsigned long)furi_get_tick(), TIMER_NAME[app->opt_timer_idx],
            app->opt_timer_action ? "replay" : "aus", SCROLL_NAME[app->opt_scroll],
            app->opt_led_on ? 1 : 0);
        if(m > 0) storage_file_write(f, l, (size_t)m);
    }
    storage_file_close(f);
    storage_file_free(f);
}
// Ereigniszeile mit ms-Zeitstempel anhaengen (nur wenn Log an).
static void tk_log(App* app, const char* fmt, ...) {
    if(!app->opt_log) return;
    char body[112];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(body, sizeof(body), fmt, ap);
    va_end(ap);
    char l[144];
    int m = snprintf(l, sizeof(l), "[%lu] %s\n", (unsigned long)furi_get_tick(), body);
    storage_common_mkdir(app->storage, "/ext/apps_data/toniekids");
    File* f = storage_file_alloc(app->storage);
    if(m > 0 && storage_file_open(f, LOG_FILE, FSAM_WRITE, FSOM_OPEN_APPEND)) {
        storage_file_write(f, l, (size_t)m);
    }
    storage_file_close(f);
    storage_file_free(f);
}

// ---------- Verzeichnis ----------
// Die Sammlung kennt seit Herbst 2026 eine dritte Ebene (Book Tonies/Conni/Folge.nfc).
// Folgen aus einem Unterordner stehen deshalb als "Conni/Folge.nfc" in der Liste - so
// funktionieren Pfad, Bild, Spieldauer und Bluetooth ohne weiteres Zutun.
static void read_episodes_flat(App* app, const char* path, const char* prefix, StrList* out) {
    File* dir = storage_file_alloc(app->storage);
    if(storage_dir_open(dir, path)) {
        FileInfo fi;
        char name[256];
        while(storage_dir_read(dir, &fi, name, sizeof(name))) {
            bool is_dir = (fi.flags & FSF_DIRECTORY);
            if(!is_dir && ends_with_nfc(name)) {
                if(prefix) {
                    FuriString* rel = furi_string_alloc_printf("%s/%s", prefix, name);
                    strlist_append(out, furi_string_get_cstr(rel));
                    furi_string_free(rel);
                } else {
                    strlist_append(out, name);
                }
            } else if(is_dir && !prefix) { // genau eine Ebene tiefer, nicht beliebig
                FuriString* sub = furi_string_alloc_printf("%s/%s", path, name);
                read_episodes_flat(app, furi_string_get_cstr(sub), name, out);
                furi_string_free(sub);
            }
        }
    }
    storage_dir_close(dir);
    storage_file_free(dir);
}
static void read_dir(App* app, const char* path, bool want_dirs, StrList* out) {
    strlist_clear(out);
    if(!want_dirs) {
        read_episodes_flat(app, path, NULL, out);
    } else {
        File* dir = storage_file_alloc(app->storage);
        if(storage_dir_open(dir, path)) {
            FileInfo fi;
            char name[256];
            while(storage_dir_read(dir, &fi, name, sizeof(name))) {
                if(fi.flags & FSF_DIRECTORY) strlist_append(out, name);
            }
        }
        storage_dir_close(dir);
        storage_file_free(dir);
    }
    if(out->count > 1) strlist_sort(out);
}

// ---------- Icon laden ----------
static void reload_icon(App* app) {
    app->scroll_off = 0; // neuer Name -> Laufschrift von vorne
    app->ic.valid = false;
    const char* series = NULL;
    const char* item = NULL; // NULL -> _series
    if(app->screen == ScreenSeries) {
        if(!app->series.count) return;
        series = app->series.items[app->series_idx];
    } else {
        if(!app->series.count || !app->episodes.count) return;
        series = app->series.items[app->series_idx];
        item = app->episodes.items[app->episode_idx];
    }
    FuriString* p = furi_string_alloc();
    if(item == NULL) {
        furi_string_printf(p, "%s/%s/_series.fxbm", ICON_DIR, series);
    } else {
        size_t n = strlen(item);
        size_t base = (n > 4) ? n - 4 : n;
        furi_string_printf(p, "%s/%s/", ICON_DIR, series);
        for(size_t i = 0; i < base; i++) furi_string_push_back(p, item[i]);
        furi_string_cat_str(p, ".fxbm");
    }
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(f, furi_string_get_cstr(p), FSAM_READ, FSOM_OPEN_EXISTING)) {
        uint8_t hdr[2];
        if(storage_file_read(f, hdr, 2) == 2) {
            uint8_t w = hdr[0], h = hdr[1];
            size_t bytes = ((size_t)((w + 7) / 8)) * h;
            if(bytes > 0 && bytes <= ICON_MAX_BYTES) {
                if(storage_file_read(f, app->ic.buf, bytes) == bytes) {
                    app->ic.w = w;
                    app->ic.h = h;
                    app->ic.valid = true;
                }
            }
        }
    }
    storage_file_close(f);
    storage_file_free(f);
    furi_string_free(p);
}

// ---------- Favoriten ----------
static bool is_favorite(App* app, const char* name) {
    for(size_t i = 0; i < app->favorites.count; i++)
        if(strcmp(app->favorites.items[i], name) == 0) return true;
    return false;
}
static void load_favorites(App* app) {
    strlist_clear(&app->favorites);
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(f, FAV_FILE, FSAM_READ, FSOM_OPEN_EXISTING)) {
        // Nicht auf einen festen Puffer stuetzen — ab 117 Eintraegen wuerde die
        // Datei sonst hinten abgeschnitten und der naechste save_favorites den
        // Rest still verlieren (FSOM_CREATE_ALWAYS ueberschreibt).
        uint64_t sz = storage_file_size(f);
        if(sz > 0 && sz < 65536) {
            char* buf = malloc((size_t)sz + 1);
            if(buf) {
                uint16_t rd = storage_file_read(f, buf, (uint16_t)sz);
                buf[rd] = 0;
                char* line = buf;
                for(uint16_t i = 0; i < rd; i++) {
                    if(buf[i] == '\n' || buf[i] == '\r') {
                        buf[i] = 0;
                        if(*line) strlist_append(&app->favorites, line);
                        line = &buf[i + 1];
                    }
                }
                if(*line) strlist_append(&app->favorites, line);
                free(buf);
            }
        }
    }
    storage_file_close(f);
    storage_file_free(f);
}
static void save_favorites(App* app) {
    storage_common_mkdir(app->storage, "/ext/apps_data/toniekids");
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(f, FAV_FILE, FSAM_WRITE, FSOM_CREATE_ALWAYS)) {
        for(size_t i = 0; i < app->favorites.count; i++) {
            storage_file_write(f, app->favorites.items[i], strlen(app->favorites.items[i]));
            storage_file_write(f, "\n", 1);
        }
    }
    storage_file_close(f);
    storage_file_free(f);
}

// ---------- Einstellungen ----------
// "key=" im Puffer suchen und die folgende Ganzzahl lesen (sonst Default).
static int cfg_int(const char* buf, const char* key, int def) {
    const char* p = strstr(buf, key);
    if(!p) return def;
    return atoi(p + strlen(key));
}
static void load_settings(App* app) {
    app->opt_uppercase = true;    // Default: GROSS (wie gewuenscht)
    app->opt_hide_images = false; // Default: Bilder an
    app->opt_led_on = true;       // Default: LED-Blink an
    app->opt_led_color = 0;       // Zyan
    app->opt_led_bright = 1;      // mittel
    app->opt_timer_idx = 0;       // Auto-Timer aus
    app->opt_puffer_idx = PUFFER_DEFAULT;
    app->opt_timer_action = false;// Aktion: Aus
    app->opt_scroll = 0;          // Laufschrift aus
    app->opt_log = false;         // Log aus
    // Default AUS: die App soll sich ohne Zutun genau wie bisher verhalten. Wer die
    // Handy-Bibliothek will, schaltet Bluetooth einmal im Setup an - das haelt.
    app->opt_ble = false;
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(f, SETTINGS_FILE, FSAM_READ, FSOM_OPEN_EXISTING)) {
        char buf[256];
        size_t n = storage_file_read(f, buf, sizeof(buf) - 1);
        buf[n] = 0;
        app->opt_uppercase = cfg_int(buf, "uppercase=", 1) != 0;
        app->opt_hide_images = cfg_int(buf, "hide_images=", 0) != 0;
        app->opt_led_on = cfg_int(buf, "led_on=", 1) != 0;
        // unsigned-Cast VOR dem Modulo: sonst bleibt z.B. -1 % N == -1 -> (uint8_t)255 -> OOB-Index
        app->opt_led_color = (uint8_t)((unsigned)cfg_int(buf, "led_color=", 0) % LED_COLOR_COUNT);
        app->opt_led_bright = (uint8_t)((unsigned)cfg_int(buf, "led_bright=", 1) % LED_BRIGHT_COUNT);
        app->opt_timer_idx = (uint8_t)((unsigned)cfg_int(buf, "timer_idx=", 0) % TIMER_COUNT);
        app->opt_puffer_idx =
            (uint8_t)((unsigned)cfg_int(buf, "puffer_idx=", PUFFER_DEFAULT) % PUFFER_COUNT);
        app->opt_timer_action = cfg_int(buf, "timer_action=", 0) != 0;
        app->opt_scroll = (uint8_t)((unsigned)cfg_int(buf, "scroll=", 0) % SCROLL_COUNT);
        app->opt_log = cfg_int(buf, "log=", 0) != 0;
        app->opt_ble = cfg_int(buf, "ble=", 0) != 0;
    }
    storage_file_close(f);
    storage_file_free(f);
}
static void save_settings(App* app) {
    storage_common_mkdir(app->storage, "/ext/apps_data/toniekids");
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(f, SETTINGS_FILE, FSAM_WRITE, FSOM_CREATE_ALWAYS)) {
        char line[192];
        int m = snprintf(
            line, sizeof(line),
            "uppercase=%d\nhide_images=%d\nled_on=%d\nled_color=%d\nled_bright=%d\n"
            "timer_idx=%d\npuffer_idx=%d\ntimer_action=%d\nscroll=%d\nlog=%d\nble=%d\n",
            app->opt_uppercase ? 1 : 0, app->opt_hide_images ? 1 : 0, app->opt_led_on ? 1 : 0,
            app->opt_led_color, app->opt_led_bright, app->opt_timer_idx, app->opt_puffer_idx,
            app->opt_timer_action ? 1 : 0, app->opt_scroll, app->opt_log ? 1 : 0,
            app->opt_ble ? 1 : 0);
        if(m > 0) storage_file_write(f, line, (size_t)m);
    }
    storage_file_close(f);
    storage_file_free(f);
}
// Serienliste bauen: Favoriten zuerst (in Favoriten-Reihenfolge), dann Rest alphabetisch
static void build_series_ordered(App* app) {
    StrList all;
    strlist_init(&all);
    read_dir(app, TONIE_DIR, true, &all);
    strlist_clear(&app->series);
    for(size_t i = 0; i < app->favorites.count; i++) {
        for(size_t j = 0; j < all.count; j++) {
            if(all.items[j] && strcmp(all.items[j], app->favorites.items[i]) == 0) {
                strlist_append(&app->series, all.items[j]);
                free(all.items[j]);
                all.items[j] = NULL;
                break;
            }
        }
    }
    for(size_t j = 0; j < all.count; j++)
        if(all.items[j]) strlist_append(&app->series, all.items[j]);
    strlist_clear(&all);
    if(app->series_idx >= app->series.count) app->series_idx = 0;
}
static void toggle_favorite(App* app) {
    if(!app->series.count) return;
    const char* cur = app->series.items[app->series_idx];
    int fi = -1;
    for(size_t i = 0; i < app->favorites.count; i++)
        if(strcmp(app->favorites.items[i], cur) == 0) {
            fi = (int)i;
            break;
        }
    if(fi >= 0) {
        free(app->favorites.items[fi]);
        for(size_t i = (size_t)fi; i + 1 < app->favorites.count; i++)
            app->favorites.items[i] = app->favorites.items[i + 1];
        app->favorites.count--;
    } else {
        strlist_append(&app->favorites, cur);
    }
    save_favorites(app);
    // Bewusst KEINE Neu-Sortierung der Serienliste hier: das Markieren soll das Durchblaettern
    // NICHT unterbrechen (Cursor bleibt stehen, nur der Stern erscheint/verschwindet). Die
    // Favoriten wandern erst beim naechsten App-Start nach vorne.
    {
        char line[96];
        snprintf(
            line, sizeof(line), "fav toggle idx=%u now=%d fav_n=%u\n", (unsigned)app->series_idx,
            fi < 0 ? 1 : 0, (unsigned)app->favorites.count);
        diag_write(app, line, false);
    }
}

// ---------- LED ----------
static void led_on(App* app) {
    if(app->opt_led_on)
        furi_hal_light_blink_start(
            LED_COLOR_MASK[app->opt_led_color], LED_BRIGHT_VAL[app->opt_led_bright], 200, 900);
}
static void led_off(void) {
    furi_hal_light_blink_stop();
    furi_hal_light_set(LightRed | LightGreen | LightBlue, 0);
}

// ---------- Spieldauer ----------
// Minuten fuer den aktuellen Tonie aus durations.txt (Schluessel "<Serie>/<Datei>.nfc"),
// 0 = unbekannt.
static uint16_t lookup_duration(App* app) {
    if(!app->series.count || !app->episodes.count) return 0;
    FuriString* key = furi_string_alloc();
    furi_string_printf(
        key, "%s/%s", app->series.items[app->series_idx], app->episodes.items[app->episode_idx]);
    uint16_t mins = 0;
    File* f = storage_file_alloc(app->storage);
    if(storage_file_open(f, DURATIONS_FILE, FSAM_READ, FSOM_OPEN_EXISTING)) {
        uint64_t sz = storage_file_size(f);
        if(sz > 0 && sz < 60000) {
            char* buf = malloc((size_t)sz + 1);
            if(buf) {
                uint16_t rd = storage_file_read(f, buf, (uint16_t)sz);
                buf[rd] = 0;
                const char* kc = furi_string_get_cstr(key);
                size_t kl = strlen(kc);
                char* line = buf;
                while(line && *line) {
                    char* nl = strchr(line, '\n');
                    if(nl) *nl = 0;
                    if(strncmp(line, kc, kl) == 0 && line[kl] == '\t') {
                        mins = (uint16_t)atoi(line + kl + 1);
                        break;
                    }
                    line = nl ? nl + 1 : NULL;
                }
                free(buf);
            }
        }
    }
    storage_file_close(f);
    storage_file_free(f);
    furi_string_free(key);
    return mins;
}
// Auto-Timer scharf schalten: echte Dauer, sonst Fallback aus der Einstellung. Rueckgabe = min (0 = aus).
static uint16_t arm_timer(App* app) {
    if(TIMER_MIN[app->opt_timer_idx] == 0) {
        tk_log(app, "auto-timer AUS -> keine automatische Abschaltung");
        return 0;
    }
    uint16_t real = lookup_duration(app);
    uint16_t puffer = PUFFER_MIN[app->opt_puffer_idx];
    uint16_t mins = (real ? real : TIMER_MIN[app->opt_timer_idx]) + puffer;
    furi_timer_start(app->timer, furi_ms_to_ticks((uint32_t)mins * 60u * 1000u));
    tk_log(
        app, "timer scharf: %umin (%s, puffer +%u), aktion=%s", (unsigned)mins,
        real ? "echte dauer" : "fallback", (unsigned)puffer,
        app->opt_timer_action ? "replay" : "aus");
    return mins;
}

// ---------- Emulation ----------
static NfcCommand listener_cb(NfcGenericEvent event, void* ctx) {
    UNUSED(event);
    UNUSED(ctx);
    return NfcCommandContinue;
}
// Listener starten (Feld an, LED an) fuer bereits geladenes dev/nfc.
static void listener_arm(App* app) {
    if(!app->nfc || !app->dev) return;
    NfcProtocol proto = nfc_device_get_protocol(app->dev);
    const NfcDeviceData* data = nfc_device_get_data(app->dev, proto);
    app->listener = nfc_listener_alloc(app->nfc, proto, data);
    nfc_listener_start(app->listener, listener_cb, app);
    led_on(app);
}
// Listener stoppen (Feld aus, LED aus) — dev/nfc bleiben fuer Replay geladen.
static void listener_disarm(App* app) {
    if(app->listener) {
        nfc_listener_stop(app->listener);
        nfc_listener_free(app->listener);
        app->listener = NULL;
    }
    led_off();
}
static bool emulate_start(App* app) {
    if(!app->episodes.count) return false;
    FuriString* path = furi_string_alloc();
    furi_string_printf(
        path, "%s/%s/%s", TONIE_DIR, app->series.items[app->series_idx],
        app->episodes.items[app->episode_idx]);
    app->nfc = nfc_alloc();
    app->dev = nfc_device_alloc();
    bool ok = nfc_device_load(app->dev, furi_string_get_cstr(path));
    furi_string_free(path);
    if(!ok) {
        nfc_device_free(app->dev);
        nfc_free(app->nfc);
        app->dev = NULL;
        app->nfc = NULL;
        return false;
    }
    NfcProtocol proto = nfc_device_get_protocol(app->dev);
    listener_arm(app);
    app->emulating = true;
    app->replay_pending = false;
    tk_log(app, "emulate START: %s", app->episodes.items[app->episode_idx]);
    uint16_t tmin = arm_timer(app);
    {
        char line[128];
        snprintf(
            line, sizeof(line), "emulate ok proto=%s file=%s timer=%umin action=%s\n",
            nfc_device_get_protocol_name(proto), app->episodes.items[app->episode_idx],
            (unsigned)tmin, app->opt_timer_action ? "replay" : "off");
        diag_write(app, line, false);
    }
    return true;
}
static void emulate_stop(App* app) {
    if(app->emulating) tk_log(app, "emulate STOP");
    if(app->timer) furi_timer_stop(app->timer);
    app->replay_pending = false;
    listener_disarm(app);
    if(app->dev) {
        nfc_device_free(app->dev);
        app->dev = NULL;
    }
    if(app->nfc) {
        nfc_free(app->nfc);
        app->nfc = NULL;
    }
    app->emulating = false;
}
// Timer-Callback: nur markieren + Hauptschleife wecken (Release wird sonst ignoriert).
static void timer_cb(void* ctx) {
    App* app = ctx;
    app->timer_fired = true;
    InputEvent ev = {.type = InputTypeRelease, .key = InputKeyMAX};
    furi_message_queue_put(app->queue, &ev, 0);
}
// Marquee-Tick: lange Namen weiterschieben (nur auf Browse-Screens + Laufschrift an).
static void scroll_cb(void* ctx) {
    App* app = ctx;
    // Bewusst ohne Mutex: nur Anzeige-Zustand. scroll_off (aligned uint16) sowie screen/opt_scroll
    // sind auf Cortex-M atomar; schlimmstenfalls ein ungenauer Marquee-Frame, kein Crash/OOB.
    if(app->opt_scroll && (app->screen == ScreenSeries || app->screen == ScreenEpisode)) {
        app->scroll_off += SCROLL_STEP[app->opt_scroll];
        view_port_update(app->view_port);
    }
}

// ---------- Fernsteuerung per Bluetooth ----------
// Gegenstelle ist die Web-App (Web Bluetooth) auf dem Telefon. Uebertragen wird
// Klartext, zeilenweise mit \n — das laesst sich im Fehlerfall mit jedem
// BLE-Terminal nachstellen, was bei Binaerprotokollen nicht geht.
//
//   PING              -> PONG toniekids 2
//   LIST              -> je Folge "I <Serie>/<Datei>.nfc", am Ende "END <n>"
//   PLAY <Serie>/<Datei>.nfc -> OK PLAY <pfad>   | ERR <grund>
//   STOP              -> OK STOP
//   STATUS            -> ST play <pfad> | ST idle
//   FAVS              -> je Liebling "F <Serie>", am Ende "ENDF <n>"
//   FAV+ <Serie>      -> OK FAV+ <Serie>
//   FAV- <Serie>      -> OK FAV- <Serie>
//
// Die Lieblinge sind dieselbe Liste, die am Geraet mit langem OK gesetzt wird
// (favorites.txt). Telefon und Flipper zeigen damit denselben Stand.
//
// Der Empfang laeuft im BLE-Thread, ausgefuehrt wird ausschliesslich in der
// Hauptschleife (siehe ble_rx_cb).

// Text senden. Zerlegt in Haeppchen und respektiert die Flusskontrolle: schlaegt
// tx fehl, ist der Sendepuffer voll — dann kurz warten statt Daten zu verlieren.
// Rueckgabe false, wenn Puffer voll BLEIBT oder die Verbindung weg ist — der
// Aufrufer (ble_send_list, FAVS-Schleife) bricht dann ab statt die naechste
// Zeile in denselben verstopften Kanal zu werfen.
static bool ble_send(App* app, const char* s) {
    if(!app->ble_on || !app->ble_profile) return false;
    // Ohne Verbindung fuellt sich der Sendepuffer sowieso nie — jedes ble_send
    // wuerde bis zum Gesamtbudget warten, ohne dass eine Antwort kommt.
    if(!app->ble_connected) return false;
    size_t len = strlen(s);
    size_t off = 0;
    // Gesamtbudget je Befehl (statt je Haeppchen). BLE_TX_RETRY * 20 ms war
    // frueher das Budget PRO CHUNK — bei einer langen Nachricht summierte sich
    // das zu mehreren Sekunden, waehrend die Hauptschleife stand.
    uint32_t start = furi_get_tick();
    const uint32_t budget_ms = BLE_TX_RETRY * 20;
    while(off < len) {
        size_t chunk = len - off;
        if(chunk > BLE_TX_CHUNK) chunk = BLE_TX_CHUNK;
        while(!ble_profile_serial_tx(app->ble_profile, (uint8_t*)(s + off), (uint16_t)chunk)) {
            if(furi_get_tick() - start > furi_ms_to_ticks(budget_ms) || !app->ble_connected) {
                tk_log(app, "BLE: tx haengt, Rest verworfen (%u Byte)", (unsigned)(len - off));
                return false;
            }
            furi_delay_ms(20);
        }
        off += chunk;
    }
    return true;
}
static bool ble_sendf(App* app, const char* fmt, ...) {
    char line[BLE_RX_LINE_MAX + 32];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line, sizeof(line), fmt, ap);
    va_end(ap);
    return ble_send(app, line);
}

// Serie + Folge anhand des relativen Pfades auswaehlen ("<Serie>/<Datei>.nfc").
// Setzt denselben Zustand, den auch die Tastenbedienung setzt — damit zeigt der
// Flipper waehrend der Wiedergabe Bild und Namen der richtigen Folge.
static bool select_by_path(App* app, const char* rel) {
    const char* slash = strchr(rel, '/');
    if(!slash || slash == rel || !*(slash + 1)) return false;
    size_t sl = (size_t)(slash - rel);
    for(size_t i = 0; i < app->series.count; i++) {
        const char* s = app->series.items[i];
        if(strlen(s) != sl || strncmp(s, rel, sl) != 0) continue;
        FuriString* p = furi_string_alloc();
        furi_string_printf(p, "%s/%s", TONIE_DIR, s);
        read_dir(app, furi_string_get_cstr(p), false, &app->episodes);
        furi_string_free(p);
        const char* ep = slash + 1;
        for(size_t j = 0; j < app->episodes.count; j++) {
            if(strcmp(app->episodes.items[j], ep) == 0) {
                app->series_idx = i;
                app->episode_idx = j;
                return true;
            }
        }
        // Serie da, Folge nicht. ⚠️ read_dir() hat app->episodes zu diesem
        // Zeitpunkt BEREITS ersetzt — die vorherige Auswahl kann hinter dem
        // Ende der neuen, kuerzeren Liste liegen. Bleibt episode_idx dann
        // stehen, liest der naechste Bildaufbau (reload_icon/draw_callback)
        // ueber den Puffer hinaus. Deshalb hier klemmen, nicht erst dort.
        if(app->episode_idx >= app->episodes.count) app->episode_idx = 0;
        return false;
    }
    return false;
}

// Komplette Sammlung senden. Bewusst aus der Hauptschleife heraus: das liest jedes
// Serienverzeichnis und dauert je nach Sammlungsgroesse einige Sekunden, in denen
// die App nicht auf Tasten reagiert.
static void ble_send_list(App* app) {
    StrList eps;
    strlist_init(&eps);
    size_t total = 0;
    bool abgebrochen = false;
    for(size_t i = 0; i < app->series.count && !abgebrochen; i++) {
        FuriString* p = furi_string_alloc();
        furi_string_printf(p, "%s/%s", TONIE_DIR, app->series.items[i]);
        read_dir(app, furi_string_get_cstr(p), false, &eps);
        furi_string_free(p);
        for(size_t j = 0; j < eps.count; j++) {
            // Beim ersten fehlgeschlagenen Senden abbrechen — sonst laeuft die
            // Schleife weitere Sekunden gegen einen verstopften oder toten
            // Kanal und die Hauptschleife (Tasteneingaben) steht so lange.
            if(!ble_sendf(app, "I %s/%s\n", app->series.items[i], eps.items[j])) {
                abgebrochen = true;
                break;
            }
            total++;
        }
    }
    strlist_clear(&eps);
    if(!abgebrochen) ble_sendf(app, "END %u\n", (unsigned)total);
    tk_log(app, "BLE: LIST %s (%u Folgen)",
           abgebrochen ? "abgebrochen" : "gesendet", (unsigned)total);
}

// Einen Lieblingseintrag entfernen. Gleiche Reihenfolge-Semantik wie
// toggle_favorite: die Serienliste wird NICHT neu sortiert, damit sich die
// Anzeige am Geraet nicht unter den Fingern verschiebt.
static bool fav_remove(App* app, const char* name) {
    for(size_t i = 0; i < app->favorites.count; i++) {
        if(strcmp(app->favorites.items[i], name) != 0) continue;
        free(app->favorites.items[i]);
        for(size_t j = i; j + 1 < app->favorites.count; j++)
            app->favorites.items[j] = app->favorites.items[j + 1];
        app->favorites.count--;
        return true;
    }
    return false;
}

// Einen empfangenen Befehl ausfuehren. Laeuft in der Hauptschleife.
static void ble_handle_cmd(App* app, const char* cmd) {
    tk_log(app, "BLE: rx '%s'", cmd);
    if(strcmp(cmd, "PING") == 0) {
        ble_send(app, "PONG toniekids 2\n");
    } else if(strcmp(cmd, "FAVS") == 0) {
        // Nur lesen, und nur aus der Hauptschleife heraus — geaendert wird die
        // Liste ausschliesslich hier und in toggle_favorite. Kein Mutex noetig,
        // und ein gehaltener Mutex waehrend des Sendens wuerde die Anzeige
        // fuer die Dauer der Uebertragung einfrieren.
        // Wie in ble_send_list: beim ersten Fehler abbrechen statt gegen
        // einen verstopften Kanal weiter zu senden.
        for(size_t i = 0; i < app->favorites.count; i++) {
            if(!ble_sendf(app, "F %s\n", app->favorites.items[i])) { break; }
        }
        ble_sendf(app, "ENDF %u\n", (unsigned)app->favorites.count);
    } else if(strncmp(cmd, "FAV+ ", 5) == 0 || strncmp(cmd, "FAV- ", 5) == 0) {
        bool add = (cmd[3] == '+');
        const char* name = cmd + 5;
        // Leere Namen und unbekannte Serien abweisen — sonst waechst die Liste
        // unbeschraenkt und save_favorites schreibt sie weiter fort.
        if(!*name) { ble_send(app, "ERR leerer Name\n"); return; }
        if(add) {
            bool bekannt = false;
            for(size_t i = 0; i < app->series.count; i++) {
                if(strcmp(app->series.items[i], name) == 0) { bekannt = true; break; }
            }
            if(!bekannt) { ble_sendf(app, "ERR unbekannte Serie: %s\n", name); return; }
        }
        furi_mutex_acquire(app->mutex, FuriWaitForever);
        bool changed = add ? (!is_favorite(app, name) ? (strlist_append(&app->favorites, name), true)
                                                      : false)
                           : fav_remove(app, name);
        if(changed) save_favorites(app);
        furi_mutex_release(app->mutex);
        ble_sendf(app, "OK FAV%c %s\n", add ? '+' : '-', name);
        tk_log(app, "BLE: fav%c %s (%s)", add ? '+' : '-', name, changed ? "geaendert" : "unveraendert");
    } else if(strcmp(cmd, "LIST") == 0) {
        ble_send_list(app);
    } else if(strcmp(cmd, "STOP") == 0) {
        furi_mutex_acquire(app->mutex, FuriWaitForever);
        if(app->emulating) {
            emulate_stop(app);
            app->screen = ScreenEpisode;
            reload_icon(app);
        }
        furi_mutex_release(app->mutex);
        ble_send(app, "OK STOP\n");
    } else if(strcmp(cmd, "STATUS") == 0) {
        // Erst unter dem Mutex kopieren, dann ausserhalb senden — sonst haelt
        // ein blockierendes ble_send die Anzeige (draw_callback nimmt denselben
        // Mutex) minutenlang fest.
        char pfad[256] = {0};
        bool playing = false;
        furi_mutex_acquire(app->mutex, FuriWaitForever);
        playing = app->emulating && app->episodes.count && app->series.count;
        if(playing) {
            snprintf(pfad, sizeof(pfad), "%s/%s",
                     app->series.items[app->series_idx],
                     app->episodes.items[app->episode_idx]);
        }
        furi_mutex_release(app->mutex);
        if(playing) ble_sendf(app, "ST play %s\n", pfad);
        else        ble_send(app, "ST idle\n");
    } else if(strncmp(cmd, "PLAY ", 5) == 0) {
        const char* rel = cmd + 5;
        furi_mutex_acquire(app->mutex, FuriWaitForever);
        if(app->emulating) emulate_stop(app); // laufende Folge zuerst beenden
        bool ok = select_by_path(app, rel);
        if(ok) {
            ok = emulate_start(app);
            if(ok) app->screen = ScreenPlay;
            reload_icon(app);
        }
        if(!ok) {
            // Fehlerzweig: emulate_stop() oben hat emulating=false gesetzt, den
            // Bildschirm aber nicht mitgezogen. Ohne diesen Zweig zeigt der
            // Flipper weiter "SPIELT!", waehrend gar nichts laeuft.
            app->screen = app->episodes.count ? ScreenEpisode : ScreenSeries;
            reload_icon(app);
        }
        furi_mutex_release(app->mutex);
        if(ok)
            ble_sendf(app, "OK PLAY %s\n", rel);
        else
            ble_sendf(app, "ERR nicht gefunden: %s\n", rel);
    } else {
        ble_sendf(app, "ERR unbekannt: %s\n", cmd);
    }
}

// Empfang (BLE-Thread!). Sammelt Bytes bis zum Zeilenende und uebergibt die fertige
// Zeile an die Hauptschleife — hier wird bewusst nichts ausgefuehrt.
static uint16_t ble_rx_cb(SerialServiceEvent event, void* ctx) {
    App* app = ctx;
    if(event.event != SerialServiceEventTypeDataReceived) return 0;
    for(uint16_t i = 0; i < event.data.size; i++) {
        char c = (char)event.data.buffer[i];
        if(c == '\n' || c == '\r') {
            // Nur dispatchen, wenn die Zeile NICHT ueberliefen ist — sonst ist
            // der Anfang verworfen und das Ende waere ein Bruchstueck, das der
            // Aufrufer als eigenen Befehl auffasst.
            if(app->ble_rx_len > 0 && !app->ble_rx_over) {
                app->ble_rx[app->ble_rx_len] = '\0';
                furi_mutex_acquire(app->ble_mutex, FuriWaitForever);
                // Noch ein unerledigter Befehl: der neue wird verworfen. Die Web-App
                // wartet je Befehl auf die Antwort, deshalb ist das kein Normalfall.
                bool took = !app->ble_cmd_pending;
                if(took) {
                    strncpy(app->ble_cmd, app->ble_rx, sizeof(app->ble_cmd) - 1);
                    app->ble_cmd[sizeof(app->ble_cmd) - 1] = '\0';
                    app->ble_cmd_pending = true;
                }
                furi_mutex_release(app->ble_mutex);
                if(took) {
                    // Hauptschleife wecken (gleiches Muster wie der Auto-Timer)
                    InputEvent ev = {.type = InputTypeRelease, .key = InputKeyMAX};
                    furi_message_queue_put(app->queue, &ev, 0);
                }
            }
            app->ble_rx_len = 0;
            app->ble_rx_over = false;
        } else if(app->ble_rx_len < sizeof(app->ble_rx) - 1) {
            if(!app->ble_rx_over) app->ble_rx[app->ble_rx_len++] = c;
        } else {
            // Zu lang: Flag setzen und bis zum naechsten '\n' alles wegwerfen.
            // Frueher wurde nur ble_rx_len auf 0 gesetzt, der Rest ab Byte 192
            // fuellte den Puffer erneut und wurde beim naechsten '\n' als eigener
            // (verstuemmelter) Befehl dispatched.
            app->ble_rx_over = true;
            app->ble_rx_len = 0;
        }
    }
    return event.data.size;
}

static void ble_status_cb(BtStatus status, void* ctx) {
    App* app = ctx;
    // Nur ein bool aus dem BT-Thread — auf Cortex-M atomar, wie beim Laufschrift-Tick.
    app->ble_connected = (status == BtStatusConnected);
    // Und den Zeilenpuffer beim Trennen leeren: sonst wird ein halb empfangener
    // Befehl beim Wiederverbinden mit dem naechsten Anfang verklebt. Waehrend
    // getrennter Verbindung liefert der Stack keine RX-Daten, der Zugriff
    // kollidiert also nicht.
    if(!app->ble_connected) { app->ble_rx_len = 0; app->ble_rx_over = false; }
}

static void ble_start(App* app) {
    if(app->ble_on) return;
    if(!app->bt) app->bt = furi_record_open(RECORD_BT);
    bt_disconnect(app->bt);
    furi_delay_ms(200); // Trennung abwarten, sonst startet das Profil auf einer offenen Verbindung
    // Eigener Schluesselspeicher: sonst ueberschreibt das Pairing mit dem Telefon
    // die gespeicherten Schluessel der offiziellen Flipper-App.
    bt_keys_storage_set_storage_path(app->bt, BLE_KEYS_FILE);
    app->ble_profile = bt_profile_start(app->bt, ble_profile_serial, NULL);
    if(!app->ble_profile) {
        tk_log(app, "BLE: Profilstart fehlgeschlagen");
        bt_keys_storage_set_default_path(app->bt);
        furi_record_close(RECORD_BT);
        app->bt = NULL;
        app->opt_ble = false; // nicht in einer Endlosschleife neu versuchen
        save_settings(app);
        return;
    }
    // Ausdruecklich kein RPC: der Serial-Kanal traegt sonst Protobuf-Rahmen der
    // offiziellen App. Wir wollen die rohen Bytes in unserem Callback.
    ble_profile_serial_set_rpc_active(app->ble_profile, false);
    ble_profile_serial_set_event_callback(app->ble_profile, BLE_RX_LINE_MAX, ble_rx_cb, app);
    bt_set_status_changed_callback(app->bt, ble_status_cb, app);
    furi_hal_bt_start_advertising();
    app->ble_on = true;
    tk_log(app, "BLE: an, wartet auf das Telefon");
}

static void ble_stop(App* app) {
    if(app->bt) {
        if(app->ble_on) {
            bt_set_status_changed_callback(app->bt, NULL, NULL);
            bt_disconnect(app->bt);
            furi_delay_ms(200);
            // Zustand des Flippers wiederherstellen: eigener Schluesselspeicher weg,
            // Standardprofil zurueck — sonst findet die offizielle App ihn nicht mehr.
            bt_keys_storage_set_default_path(app->bt);
            bt_profile_restore_default(app->bt);
            tk_log(app, "BLE: aus, Standardprofil wiederhergestellt");
        }
        furi_record_close(RECORD_BT);
        app->bt = NULL;
    }
    app->ble_profile = NULL;
    app->ble_on = false;
    app->ble_connected = false;
}

// Funkzustand an die Einstellung angleichen. Bewusst ausserhalb jedes Mutex und
// ausserhalb der Callbacks: bt_profile_start startet den zweiten Kern neu.
static void ble_sync(App* app) {
    if(app->opt_ble && !app->ble_on)
        ble_start(app);
    else if(!app->opt_ble && app->ble_on)
        ble_stop(app);
}

// ---------- Zeichnen (Hochformat 64x128) ----------
static void draw_wrapped_ex(
    Canvas* c, int x, int y, int w, const char* s, int max_lines, int line_h, int char_w) {
    int max_chars = char_w > 0 ? w / char_w : 12;
    if(max_chars < 1) max_chars = 1;
    if(max_chars > 24) max_chars = 24;
    const char* p = s;
    int line_no = 0;
    while(*p && line_no < max_lines) {
        int n = 0, last_space = -1;
        while(p[n] && n < max_chars) {
            if(p[n] == ' ') last_space = n;
            n++;
        }
        int take = n;
        if(p[n] && last_space > 0) take = last_space;
        char line[26];
        if(take > 25) take = 25;
        memcpy(line, p, take);
        line[take] = 0;
        canvas_draw_str(c, x, y + line_no * line_h, line);
        p += take;
        while(*p == ' ') p++;
        line_no++;
    }
}
static void draw_image(App* app, Canvas* canvas) {
    if(app->ic.valid) {
        int x = (ICON_W - app->ic.w) / 2;
        canvas_draw_xbm(canvas, x, 0, app->ic.w, app->ic.h, app->ic.buf);
    } else {
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 32, 48, AlignCenter, AlignCenter, "?");
    }
}
// Namen gemaess Einstellung aufbereiten (GROSS oder unveraendert).
static void disp_name(App* app, const char* raw, char* out, size_t out_sz) {
    if(app->opt_uppercase) {
        to_upper(raw, out, out_sz);
    } else {
        size_t n = strlen(raw);
        if(n > out_sz - 1) n = out_sz - 1;
        memcpy(out, raw, n);
        out[n] = 0;
    }
}
// Laufschrift: passt der Text in die Breite w, statisch; sonst laeuft er horizontal durch
// (nahtlos wiederholt), damit auch lange Namen komplett gelesen werden koennen.
static void draw_marquee(Canvas* c, int x, int y, int w, const char* s, uint16_t off) {
    uint16_t tw = canvas_string_width(c, s);
    if((int)tw <= w) {
        canvas_draw_str(c, x, y, s);
        return;
    }
    int period = (int)tw + 16; // Scroll-Distanz (Textbreite + Luecke)
    int pause = 8;             // kurzer Halt am Anfang jedes Durchlaufs (Namensanfang lesbar)
    int px = (int)(off >> 3);  // off ist in 1/8-Pixel -> ganze Pixel
    int t = px % (period + pause);
    int o = (t < pause) ? 0 : (t - pause);
    canvas_draw_str(c, x - o, y, s);
    canvas_draw_str(c, x - o + period, y, s);
}
// Favoriten-Stern deckend zeichnen (raeumt den Hintergrund frei), damit er auch ueber
// der Laufschrift sichtbar bleibt.
static void draw_star(Canvas* c, int x, int y) {
    canvas_set_color(c, ColorWhite);
    canvas_draw_box(c, x - 1, y - 1, 15, 15);
    canvas_set_color(c, ColorBlack);
    canvas_draw_xbm(c, x, y, 13, 13, star_bits);
}
// Funkzustand oben rechts, deckend (gleiches Prinzip wie der Favoriten-Stern).
// Klein "bt" = an und wartet, invers "BT" = das Telefon ist verbunden. Der
// Unterschied muss ohne Lesen erkennbar sein, deshalb invers statt nur Text.
static void draw_ble_badge(Canvas* c, App* app) {
    if(!app->ble_on) return;
    const char* t = app->ble_connected ? "BT" : "bt";
    canvas_set_font(c, FontSecondary);
    int w = (int)canvas_string_width(c, t);
    int x = 63 - w - 2, y = 0;
    canvas_set_color(c, app->ble_connected ? ColorBlack : ColorWhite);
    canvas_draw_box(c, x - 2, y, w + 4, 11);
    canvas_set_color(c, app->ble_connected ? ColorWhite : ColorBlack);
    canvas_draw_str(c, x, y + 8, t);
    canvas_set_color(c, ColorBlack);
}

// Aktuellen Wert eines Setup-Eintrags als Text.
static void setting_value(App* app, int i, char* out, size_t n) {
    switch(i) {
    case 0: snprintf(out, n, "%s", app->opt_uppercase ? "GROSS" : "klein"); break;
    case 1: snprintf(out, n, "%s", app->opt_hide_images ? "AUS" : "AN"); break;
    case 2: snprintf(out, n, "%s", app->opt_led_on ? "AN" : "AUS"); break;
    case 3: snprintf(out, n, "%s", LED_COLOR_NAME[app->opt_led_color]); break;
    case 4: snprintf(out, n, "%s", LED_BRIGHT_NAME[app->opt_led_bright]); break;
    case 5: snprintf(out, n, "%s", TIMER_NAME[app->opt_timer_idx]); break;
    case 6: snprintf(out, n, "%s", PUFFER_NAME[app->opt_puffer_idx]); break;
    case 7: snprintf(out, n, "%s", app->opt_timer_action ? "Replay" : "Aus"); break;
    case 8: snprintf(out, n, "%s", SCROLL_NAME[app->opt_scroll]); break;
    case 9: snprintf(out, n, "%s", app->opt_log ? "AN" : "AUS"); break;
    case 10:
        // Zeigt nicht nur die Einstellung, sondern den tatsaechlichen Funkzustand:
        // "AN" ohne Verbindung sagt sonst nicht, ob das Telefon schon dran ist.
        if(!app->opt_ble)
            snprintf(out, n, "AUS");
        else if(app->ble_connected)
            snprintf(out, n, "VERBUNDEN");
        else
            snprintf(out, n, "%s", app->ble_on ? "wartet" : "startet");
        break;
    default: out[0] = 0; break;
    }
}
// Versteckte Setup-Seite (Zugang: langes Zurueck auf der Serien-/Episoden-Ebene).
// Scrollbare Liste, 3 Eintraege sichtbar; OK aendert, Zurueck speichert.
static void draw_settings(Canvas* canvas, App* app) {
    canvas_set_font(canvas, FontPrimary);
    canvas_draw_str_aligned(canvas, 32, 6, AlignCenter, AlignTop, "SETUP");
    canvas_draw_line(canvas, 0, 18, 63, 18);
    canvas_set_font(canvas, FontSecondary);
    const int visible = 3;
    int top = (int)app->settings_idx - 1;
    if(top < 0) top = 0;
    if(top > SETTINGS_COUNT - visible) top = SETTINGS_COUNT - visible;
    for(int r = 0; r < visible; r++) {
        int i = top + r;
        int y = 30 + r * 26;
        if(i == (int)app->settings_idx) canvas_draw_str(canvas, 0, y, ">");
        canvas_draw_str(canvas, 8, y, SETTING_LABEL[i]);
        char val[24];
        setting_value(app, i, val, sizeof(val));
        canvas_draw_str(canvas, 10, y + 12, val);
    }
    canvas_draw_line(canvas, 0, 114, 63, 114);
    canvas_draw_str(canvas, 1, 125, "OK aendert");
}
static void draw_callback(Canvas* canvas, void* ctx) {
    App* app = ctx;
    furi_mutex_acquire(app->mutex, FuriWaitForever);
    canvas_clear(canvas);

    if(app->screen == ScreenSettings) {
        draw_settings(canvas, app);
        furi_mutex_release(app->mutex);
        return;
    }

    if(app->series.count == 0) {
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 32, 50, AlignCenter, AlignCenter, "KEINE");
        canvas_draw_str_aligned(canvas, 32, 66, AlignCenter, AlignCenter, "TONIES");
        furi_mutex_release(app->mutex);
        return;
    }

    if(app->screen == ScreenSeries) {
        const char* sname = app->series.items[app->series_idx];
        bool fav = is_favorite(app, sname);
        char nm[80];
        disp_name(app, sname, nm, sizeof(nm));
        if(app->opt_hide_images) {
            canvas_set_font(canvas, FontPrimary);
            if(app->opt_scroll)
                draw_marquee(canvas, 2, 55, 60, nm, app->scroll_off);
            else
                draw_wrapped_ex(canvas, 2, 26, 60, nm, 5, 13, 7);
            if(fav) draw_star(canvas, 1, 1);
        } else {
            draw_image(app, canvas);
            canvas_draw_line(canvas, 0, 98, 63, 98);
            canvas_set_font(canvas, FontSecondary);
            if(app->opt_scroll)
                draw_marquee(canvas, 1, 116, 62, nm, app->scroll_off);
            else
                draw_wrapped_ex(canvas, 1, 108, 62, nm, 2, 10, 5);
            if(fav) draw_star(canvas, 1, 1); // Badge ins Bild (oben links), nicht in den Text
        }
        canvas_set_font(canvas, FontSecondary);
        char cnt[16];
        snprintf(cnt, sizeof(cnt), "%u/%u", (unsigned)(app->series_idx + 1), (unsigned)app->series.count);
        canvas_draw_str_aligned(canvas, 63, 127, AlignRight, AlignBottom, cnt);
        canvas_draw_str(canvas, 1, 127, "OK");
    } else if(app->screen == ScreenEpisode) {
        if(app->episodes.count) {
            char base[80];
            strip_nfc(app->episodes.items[app->episode_idx], base, sizeof(base));
            // Folge aus einem Unterordner: nur ihren eigenen Namen zeigen.
            const char* leaf = strrchr(base, '/');
            const char* ep =
                strip_series_prefix(leaf ? leaf + 1 : base, app->series.items[app->series_idx]);
            char nm[80];
            disp_name(app, ep, nm, sizeof(nm));
            if(app->opt_hide_images) {
                canvas_set_font(canvas, FontPrimary);
                if(app->opt_scroll)
                    draw_marquee(canvas, 2, 55, 60, nm, app->scroll_off);
                else
                    draw_wrapped_ex(canvas, 2, 26, 60, nm, 5, 13, 7);
            } else {
                draw_image(app, canvas);
                canvas_draw_line(canvas, 0, 98, 63, 98);
                canvas_set_font(canvas, FontSecondary);
                if(app->opt_scroll)
                    draw_marquee(canvas, 1, 116, 62, nm, app->scroll_off);
                else
                    draw_wrapped_ex(canvas, 1, 108, 62, nm, 2, 10, 5);
            }
            canvas_set_font(canvas, FontSecondary);
            char cnt[16];
            snprintf(
                cnt, sizeof(cnt), "%u/%u", (unsigned)(app->episode_idx + 1),
                (unsigned)app->episodes.count);
            canvas_draw_str_aligned(canvas, 63, 127, AlignRight, AlignBottom, cnt);
            canvas_draw_str(canvas, 1, 127, "OK=PLAY");
        } else {
            canvas_set_font(canvas, FontSecondary);
            canvas_draw_str(canvas, 2, 112, "KEINE GESCHICHTEN");
        }
    } else { // ScreenPlay
        if(!app->opt_hide_images) draw_image(app, canvas);
        canvas_set_font(canvas, FontPrimary);
        canvas_draw_str_aligned(canvas, 32, 112, AlignCenter, AlignBottom, "SPIELT!");
        canvas_set_font(canvas, FontSecondary);
        canvas_draw_str_aligned(canvas, 32, 126, AlignCenter, AlignBottom, "Zurueck: Stop");
    }
    draw_ble_badge(canvas, app);
    furi_mutex_release(app->mutex);
}

static void input_callback(InputEvent* event, void* ctx) {
    App* app = ctx;
    furi_message_queue_put(app->queue, event, FuriWaitForever);
}

// ---------- Eingabe ----------
static void move_idx(size_t* idx, size_t count, int delta) {
    if(!count) return;
    long v = (long)*idx + delta;
    while(v < 0) v += count;
    v %= (long)count;
    *idx = (size_t)v;
}
static void handle_key(App* app, InputKey key) {
    // Alle Pfeilrichtungen navigieren (orientierungs-robust); Halten = schnell.
    if(app->screen == ScreenSeries) {
        size_t n = app->series.count;
        switch(key) {
        case InputKeyUp:
        case InputKeyLeft:
            move_idx(&app->series_idx, n, -1);
            reload_icon(app);
            break;
        case InputKeyDown:
        case InputKeyRight:
            move_idx(&app->series_idx, n, +1);
            reload_icon(app);
            break;
        case InputKeyOk: {
            if(!app->series.count) break; // leere Sammlung: kein items[0]-Deref
            FuriString* p = furi_string_alloc();
            furi_string_printf(p, "%s/%s", TONIE_DIR, app->series.items[app->series_idx]);
            read_dir(app, furi_string_get_cstr(p), false, &app->episodes);
            furi_string_free(p);
            app->episode_idx = 0;
            app->screen = ScreenEpisode;
            reload_icon(app);
            break;
        }
        case InputKeyBack:
            app->running = false;
            break;
        default:
            break;
        }
    } else if(app->screen == ScreenEpisode) {
        size_t n = app->episodes.count;
        switch(key) {
        case InputKeyUp:
        case InputKeyLeft:
            move_idx(&app->episode_idx, n, -1);
            reload_icon(app);
            break;
        case InputKeyDown:
        case InputKeyRight:
            move_idx(&app->episode_idx, n, +1);
            reload_icon(app);
            break;
        case InputKeyOk:
            if(emulate_start(app)) app->screen = ScreenPlay;
            break;
        case InputKeyBack:
            app->screen = ScreenSeries;
            reload_icon(app);
            break;
        default:
            break;
        }
    } else if(app->screen == ScreenPlay) {
        if(key == InputKeyBack || key == InputKeyOk) {
            emulate_stop(app);
            app->screen = ScreenEpisode;
            reload_icon(app);
        }
    } else if(app->screen == ScreenSettings) {
        switch(key) {
        case InputKeyUp:
        case InputKeyLeft:
            move_idx(&app->settings_idx, SETTINGS_COUNT, -1);
            break;
        case InputKeyDown:
        case InputKeyRight:
            move_idx(&app->settings_idx, SETTINGS_COUNT, +1);
            break;
        case InputKeyOk:
            switch(app->settings_idx) {
            case 0: app->opt_uppercase = !app->opt_uppercase; break;
            case 1: app->opt_hide_images = !app->opt_hide_images; break;
            case 2: app->opt_led_on = !app->opt_led_on; break;
            case 3: app->opt_led_color = (app->opt_led_color + 1) % LED_COLOR_COUNT; break;
            case 4: app->opt_led_bright = (app->opt_led_bright + 1) % LED_BRIGHT_COUNT; break;
            case 5: app->opt_timer_idx = (app->opt_timer_idx + 1) % TIMER_COUNT; break;
            case 6: app->opt_puffer_idx = (app->opt_puffer_idx + 1) % PUFFER_COUNT; break;
            case 7: app->opt_timer_action = !app->opt_timer_action; break;
            case 8: app->opt_scroll = (app->opt_scroll + 1) % SCROLL_COUNT; break;
            case 9:
                app->opt_log = !app->opt_log;
                if(app->opt_log) log_start(app); // frisches Log beim Einschalten
                break;
            // Nur die Einstellung kippen. Das eigentliche Starten/Stoppen macht die
            // Hauptschleife (Soll-Ist-Abgleich) - es startet den zweiten Kern neu und
            // darf deshalb nicht unter dem Zeichen-Mutex laufen.
            case 10: app->opt_ble = !app->opt_ble; break;
            default: break;
            }
            save_settings(app);
            break;
        case InputKeyBack:
            save_settings(app);
            app->screen = ScreenSeries;
            reload_icon(app);
            break;
        default:
            break;
        }
    }
}

// ---------- App ----------
static App* app_alloc(void) {
    App* app = malloc(sizeof(App));
    memset(app, 0, sizeof(App));
    app->mutex = furi_mutex_alloc(FuriMutexTypeNormal);
    // Eigener, kleiner Mutex nur fuer die Befehlsuebergabe. Nie zusammen mit
    // app->mutex halten — verschachtelte Sperren haengen lautlos fuer immer.
    app->ble_mutex = furi_mutex_alloc(FuriMutexTypeNormal);
    app->queue = furi_message_queue_alloc(8, sizeof(InputEvent));
    app->storage = furi_record_open(RECORD_STORAGE);
    app->gui = furi_record_open(RECORD_GUI);
    app->timer = furi_timer_alloc(timer_cb, FuriTimerTypeOnce, app);
    app->view_port = view_port_alloc();
    view_port_set_orientation(app->view_port, ViewPortOrientationVertical);
    strlist_init(&app->series);
    strlist_init(&app->episodes);
    strlist_init(&app->favorites);
    app->screen = ScreenSeries;
    app->running = true;
    view_port_draw_callback_set(app->view_port, draw_callback, app);
    view_port_input_callback_set(app->view_port, input_callback, app);
    gui_add_view_port(app->gui, app->view_port, GuiLayerFullscreen);
    app->scroll_timer = furi_timer_alloc(scroll_cb, FuriTimerTypePeriodic, app);
    furi_timer_start(app->scroll_timer, furi_ms_to_ticks(120));
    return app;
}
static void app_free(App* app) {
    emulate_stop(app);
    ble_stop(app); // Funk zurueck auf das Standardprofil, bevor die App verschwindet
    if(app->scroll_timer) {
        furi_timer_stop(app->scroll_timer);
        furi_timer_free(app->scroll_timer);
    }
    if(app->timer) furi_timer_free(app->timer);
    gui_remove_view_port(app->gui, app->view_port);
    view_port_free(app->view_port);
    strlist_clear(&app->series);
    strlist_clear(&app->episodes);
    strlist_clear(&app->favorites);
    furi_record_close(RECORD_GUI);
    furi_record_close(RECORD_STORAGE);
    furi_message_queue_free(app->queue);
    furi_mutex_free(app->ble_mutex);
    furi_mutex_free(app->mutex);
    free(app);
}

int32_t toniekids_app(void* p) {
    UNUSED(p);
    App* app = app_alloc();
    load_favorites(app);
    load_settings(app);
    build_series_ordered(app);
    reload_icon(app);
    {
        char line[128];
        snprintf(
            line, sizeof(line),
            "start series=%u fav=%u icon_c=%d up=%d img=%d led=%d timer=%s orient=vertical first=%s\n",
            (unsigned)app->series.count, (unsigned)app->favorites.count, app->ic.valid ? 1 : 0,
            app->opt_uppercase ? 1 : 0, app->opt_hide_images ? 1 : 0, app->opt_led_on ? 1 : 0,
            TIMER_NAME[app->opt_timer_idx], app->series.count ? app->series.items[0] : "-");
        diag_write(app, line, true);
    }
    log_start(app);
    view_port_update(app->view_port);
    ble_sync(app); // war Bluetooth zuletzt an, gleich beim Start wieder anbieten

    InputEvent event;
    while(app->running) {
        if(furi_message_queue_get(app->queue, &event, FuriWaitForever) == FuriStatusOk) {
            if(app->timer_fired) {
                // Auto-Timer abgelaufen: je nach Aktion beenden oder Replay-Bounce.
                furi_mutex_acquire(app->mutex, FuriWaitForever);
                app->timer_fired = false;
                if(app->screen == ScreenPlay) {
                    if(app->replay_pending) {
                        app->replay_pending = false; // 5s vorbei -> wieder aufstellen
                        listener_arm(app);
                        arm_timer(app);
                        tk_log(app, "replay: 5s um -> wieder aufgestellt");
                    } else if(app->opt_timer_action) {
                        tk_log(app, "replay: Timer abgelaufen -> 5s aus");
                        listener_disarm(app); // Replay: kurz weg (Feld aus), 5s Pause
                        app->replay_pending = true;
                        furi_timer_start(app->timer, furi_ms_to_ticks(5000));
                    } else {
                        tk_log(app, "auto-aus: Timer abgelaufen -> Emulation beenden");
                        emulate_stop(app); // Aus: Emulation beenden (Strom sparen)
                        app->screen = ScreenEpisode;
                        reload_icon(app);
                    }
                } else {
                    tk_log(app, "Timer feuerte ausserhalb der Wiedergabe (ignoriert)");
                }
                furi_mutex_release(app->mutex);
                view_port_update(app->view_port);
            }
            // Befehl vom Telefon: der BLE-Thread hat die Zeile nur abgelegt und geweckt,
            // ausgefuehrt wird sie hier. Kopie ziehen und den kleinen Mutex sofort wieder
            // freigeben — ble_handle_cmd nimmt selbst app->mutex.
            bool have_cmd = false;
            char cmd[BLE_RX_LINE_MAX];
            furi_mutex_acquire(app->ble_mutex, FuriWaitForever);
            if(app->ble_cmd_pending) {
                strncpy(cmd, app->ble_cmd, sizeof(cmd) - 1);
                cmd[sizeof(cmd) - 1] = '\0';
                app->ble_cmd_pending = false;
                have_cmd = true;
            }
            furi_mutex_release(app->ble_mutex);
            if(have_cmd) {
                ble_handle_cmd(app, cmd);
                view_port_update(app->view_port);
            }

            bool nav = (event.key == InputKeyUp || event.key == InputKeyDown ||
                        event.key == InputKeyLeft || event.key == InputKeyRight);
            if(event.type == InputTypeShort || (event.type == InputTypeRepeat && nav)) {
                furi_mutex_acquire(app->mutex, FuriWaitForever);
                handle_key(app, event.key);
                furi_mutex_release(app->mutex);
                view_port_update(app->view_port);
            } else if(event.type == InputTypeLong && event.key == InputKeyOk) {
                // Langes OK: Serie als Favorit markieren/entfernen
                furi_mutex_acquire(app->mutex, FuriWaitForever);
                if(app->screen == ScreenSeries) toggle_favorite(app);
                furi_mutex_release(app->mutex);
                view_port_update(app->view_port);
            } else if(event.type == InputTypeLong && event.key == InputKeyBack) {
                // Verstecktes Setup: langes Zurueck (nicht offensichtlich fuer Kinder)
                furi_mutex_acquire(app->mutex, FuriWaitForever);
                if(app->screen == ScreenSeries || app->screen == ScreenEpisode) {
                    app->settings_idx = 0;
                    app->screen = ScreenSettings;
                }
                furi_mutex_release(app->mutex);
                view_port_update(app->view_port);
            }
            // Funk an die Einstellung angleichen (im Setup umgeschaltet). Muss hier
            // stehen: startet den zweiten Kern neu und darf keinen Mutex halten.
            ble_sync(app);
        }
    }
    app_free(app);
    return 0;
}
