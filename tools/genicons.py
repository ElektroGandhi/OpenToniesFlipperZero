#!/usr/bin/env python3
import os, sys, json, re, unicodedata

LOCAL = "/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad/flipper-zero-tonies-master/German"
TJSON = "/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad/tonies.json"

def norm(s):
    if not s: return ""
    s = s.lower()
    s = s.replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s

def tokens(s):
    if not s: return set()
    s = s.lower().replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")
    s = unicodedata.normalize("NFKD", s); s="".join(c for c in s if not unicodedata.combining(c))
    return set(t for t in re.split(r"[^a-z0-9]+", s) if len(t) > 2)

def load_db():
    d = json.load(open(TJSON))
    entries = []
    for e in d:
        pic = e.get("pic")
        if not pic: continue
        ser = e.get("series") or ""
        ep = e.get("episodes") or ""
        title = e.get("title") or ""
        entries.append({
            "ser": ser, "ep": ep, "title": title, "pic": pic,
            "nser": norm(ser), "nep": norm(ep), "ntitle": norm(title),
            "tser": tokens(ser), "tep": tokens(ep),
        })
    return entries

def build_local():
    items = []
    for root, _, files in os.walk(LOCAL):
        for fn in files:
            if fn.endswith(".nfc"):
                rel = os.path.relpath(os.path.join(root, fn), LOCAL)
                parts = rel.split(os.sep)
                series = parts[0]
                episode = fn[:-4]
                items.append({"rel": rel, "series": series, "episode": episode,
                              "nser": norm(series), "nep": norm(episode),
                              "tser": tokens(series), "tep": tokens(episode)})
    return items

def match(item, db):
    # candidates by series match (normalized equality or containment)
    best = None; best_score = 0
    for e in db:
        s = 0
        # series score
        if e["nser"] and item["nser"]:
            if e["nser"] == item["nser"]: s += 100
            elif e["nser"] in item["nser"] or item["nser"] in e["nser"]: s += 60
            else:
                ov = len(e["tser"] & item["tser"])
                s += 12 * ov
        # episode score
        if e["nep"] and item["nep"]:
            if e["nep"] == item["nep"]: s += 120
            elif item["nep"] in e["nep"] or e["nep"] in item["nep"]: s += 70
            else:
                ov = len(e["tep"] & item["tep"])
                s += 15 * ov
        # title fallback (series+episode combined often equals title)
        combo = norm(item["series"] + item["episode"])
        if e["ntitle"] and combo and (e["ntitle"] == combo or combo in e["ntitle"] or e["ntitle"] in combo):
            s += 40
        if s > best_score:
            best_score = s; best = e
    return best, best_score

def main():
    dry = "--dry" in sys.argv
    db = load_db()
    items = build_local()
    print(f"DB entries with pic: {len(db)} | local .nfc: {len(items)}")
    strong=0; weak=0; none=0
    samples_ok=[]; samples_bad=[]
    matches={}
    for it in items:
        e, sc = match(it, db)
        # thresholds: strong if episode matched well
        if e and sc >= 150:
            strong += 1; matches[it["rel"]] = e["pic"]
            if len(samples_ok)<8: samples_ok.append((it["series"], it["episode"], e["ser"], e["ep"], sc))
        elif e and sc >= 90:
            weak += 1; matches[it["rel"]] = e["pic"]
            if len(samples_bad)<8: samples_bad.append((it["series"], it["episode"], e["ser"], e["ep"], sc))
        else:
            none += 1
            if len(samples_bad)<16 and none<=8: samples_bad.append((it["series"], it["episode"], "—","—", sc))
    total=len(items)
    print(f"STRONG(>=150): {strong}  WEAK(90-149): {weak}  NONE(<90): {none}  = {strong+weak} mit Bild ({100*(strong+weak)//total}%)")
    print("\n-- starke Treffer (Beispiele) --")
    for s in samples_ok: print(f"  [{s[4]:>4}] {s[0]} / {s[1]}  ->  {s[2]} / {s[3]}")
    print("\n-- schwache/keine Treffer (Beispiele) --")
    for s in samples_bad: print(f"  [{s[4]:>4}] {s[0]} / {s[1]}  ->  {s[2]} / {s[3]}")
    json.dump(matches, open("/tmp/claude-1000/-home-blotto/8cabb340-082f-483d-bbea-f2847f5010ca/scratchpad/matches.json","w"))

if __name__ == "__main__":
    main()
