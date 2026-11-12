"""Schneidet die Original-Mod-Grafiken aus dem Spiel-Paket shared_uicontainer (Unity-AssetBundle).

Läuft im Container python:3.13-slim (UnityPy lässt sich unter neueren Python-Versionen nicht bauen)
und wird von tools/mod_grafiken_laden.ps1 aufgerufen:
    python mod_grafiken_entpacken.py <shared_uicontainer.bundle> <zielordner> [asset-version]

Inhalt (NGUI-Atlanten im Paket):
- charactermods_datacard_atlas: modchip_<form>_base (Silberrahmen, 5 Punkte), _6dot (Goldrahmen),
  _light (weiße Kontur, im Spiel in der Stufenfarbe eingefärbt), pip
- misc_atlas: icon_buff_* / icon_tenacity (weiße Set-Symbole, im Spiel eingefärbt)

Jedes Teil wird auf seine Originalgröße (Atlas-Padding) gebracht, damit Rahmen und Kontur deckungsgleich sind.
Zusätzlich entsteht mods.json mit Mitte und Radius des größten Kreises im dunklen Innenfeld je Form (dort sitzt das Set-Symbol).
Die Grafiken gehören EA/Lucasfilm: nur privat nutzen, nicht veröffentlichen, nicht ins Repo.
"""
import json
import sys
from pathlib import Path

import UnityPy
from PIL import Image

FORMEN = ["square", "arrow", "diamond", "triangle", "circle", "cross"]  # Slot 1–6
SYMBOLE = {1: "icon_buff_health", 2: "icon_buff_attack", 3: "icon_buff_armor", 4: "icon_buff_speed",
           5: "icon_buff_crit_chance", 6: "icon_buff_critical_damage", 7: "icon_buff_accuracy", 8: "icon_tenacity"}


def atlanten(bundle: str) -> dict:
    env = UnityPy.load(bundle)
    texturen, sprites = {}, {}
    for o in env.objects:
        if o.type.name == "Texture2D":
            d = o.read()
            texturen[d.m_Name] = d
        elif o.type.name == "MonoBehaviour":
            try:
                t = o.read_typetree()
            except Exception:
                continue
            if "mSprites" in t and t.get("m_Name") in ("charactermods_datacard_atlas", "misc_atlas"):
                sprites[t["m_Name"]] = {s["name"]: s for s in t["mSprites"]}
    return {n: (texturen[n].image.convert("RGBA"), sprites[n]) for n in sprites}


def teil(atlas, name: str) -> Image.Image:
    bild, sprites = atlas
    s = sprites[name]
    stueck = bild.crop((s["x"], s["y"], s["x"] + s["width"], s["y"] + s["height"]))
    breite = s["paddingLeft"] + s["width"] + s["paddingRight"]
    hoehe = s["paddingTop"] + s["height"] + s["paddingBottom"]
    voll = Image.new("RGBA", (breite, hoehe), (0, 0, 0, 0))
    voll.paste(stueck, (s["paddingLeft"], s["paddingTop"]))
    return voll


def innenfeld(rahmen: Image.Image) -> tuple:
    """Begrenzungsrechteck des schwarzen Felds im Rahmen: zusammenhängende dunkle Fläche ab der Bildmitte."""
    b, h = rahmen.size
    px = rahmen.load()
    def dunkel(x, y):
        r, g, bl, a = px[x, y]
        return a > 200 and r + g + bl < 120
    # Startpunkt: dunkler Pixel nahe der Mitte (beim Dreieck liegt das Feld tiefer)
    start = min(((x, y) for y in range(h) for x in range(b) if dunkel(x, y)),
                key=lambda p: (p[0] - b / 2) ** 2 + (p[1] - h * 0.55) ** 2)
    gesehen, offen = {start}, [start]
    while offen:
        x, y = offen.pop()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= n[0] < b and 0 <= n[1] < h and n not in gesehen and dunkel(*n):
                gesehen.add(n)
                offen.append(n)
    # größter Innenkreis: Abstand jedes Feldpixels zum nächsten Pixel außerhalb (Mehrquellen-Breitensuche)
    abstand, welle = {}, [p for p in gesehen
                          if any(n not in gesehen for n in ((p[0] + 1, p[1]), (p[0] - 1, p[1]), (p[0], p[1] + 1), (p[0], p[1] - 1)))]
    for p in welle:
        abstand[p] = 1
    while welle:
        neu = []
        for x, y in welle:
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in gesehen and n not in abstand:
                    abstand[n] = abstand[(x, y)] + 1
                    neu.append(n)
        welle = neu
    r = max(abstand.values())
    kern = [p for p, d in abstand.items() if d == r]  # Mitte = Schwerpunkt der Pixel mit größtem Abstand
    mitte = [sum(p[0] for p in kern) / len(kern) + 0.5, sum(p[1] for p in kern) / len(kern) + 0.5]
    # Flächenschwerpunkt und Begrenzungsrechteck des Felds (optische Mitte bei unregelmäßigen Feldern)
    schwer = [round(sum(p[0] for p in gesehen) / len(gesehen) + 0.5, 2), round(sum(p[1] for p in gesehen) / len(gesehen) + 0.5, 2)]
    xs, ys = [p[0] for p in gesehen], [p[1] for p in gesehen]
    return mitte, r, schwer, [min(xs), min(ys), max(xs) + 1, max(ys) + 1]


def main() -> None:
    bundle, ziel = sys.argv[1], Path(sys.argv[2])
    ziel.mkdir(parents=True, exist_ok=True)
    a = atlanten(bundle)
    karte, misc = a["charactermods_datacard_atlas"], a["misc_atlas"]
    info = {"version": sys.argv[3] if len(sys.argv) > 3 else "", "formen": {}, "symbole": {}}
    for slot, form in enumerate(FORMEN, start=1):
        eintrag = {}
        for art in ("base", "6dot", "light"):
            name = f"modchip_{form}_{art}"
            if name not in karte[1]:
                continue
            bild = teil(karte, name)
            bild.save(ziel / f"{form}_{art}.png")
            eintrag[art] = f"{form}_{art}.png"
            if art == "base":
                eintrag["groesse"] = list(bild.size)
                eintrag["mitte"], eintrag["radius"], eintrag["schwerpunkt"], eintrag["feld"] = innenfeld(bild)
        info["formen"][slot] = eintrag
    for set_id, name in SYMBOLE.items():
        voll = teil(misc, name)  # Originalgröße mit Leerraum, so zeichnet das Spiel das Symbol in sein Kästchen
        rand = voll.getbbox()
        bild = voll.crop(rand)
        bild.save(ziel / f"set_{set_id}.png")
        # Flächenschwerpunkt (nach Deckkraft gewichtet), als Anteil der Breite/Höhe – für die optische Mitte
        a = bild.getchannel("A").load()
        summe = sx = sy = 0
        for y in range(bild.height):
            for x in range(bild.width):
                summe += a[x, y]
                sx += a[x, y] * (x + 0.5)
                sy += a[x, y] * (y + 0.5)
        info["symbole"][set_id] = {"datei": f"set_{set_id}.png", "groesse": list(bild.size),
                                   "voll": list(voll.size), "versatz": [rand[0], rand[1]],
                                   "schwerpunkt": [round(sx / summe / bild.width, 3), round(sy / summe / bild.height, 3)]}
    teil(karte, "pip").save(ziel / "pip.png")
    (ziel / "mods.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(f"{len(list(ziel.glob('*.png')))} Grafiken nach {ziel}")


if __name__ == "__main__":
    main()
