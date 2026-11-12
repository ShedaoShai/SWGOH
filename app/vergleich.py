"""Snapshot mit dem aktuellen Stand vergleichen und eine Umbau-Liste erzeugen.

Im Spiel nimmt man beim Ausrüsten einer Mod, die ein anderer Charakter trägt, sie diesem automatisch ab.
Die Liste ist deshalb nach Ziel-Charakter gruppiert: Charakter öffnen, Slot für Slot die genannte Mod
auswählen.
"""


def vergleichen(snapshot_einheiten: dict, aktuell_einheiten: dict) -> dict:
    # Wo liegt jede Mod gerade?
    ort: dict[str, tuple[str, dict]] = {}
    for eid, e in aktuell_einheiten.items():
        for m in e["mods"]:
            ort[m["id"]] = (eid, m)

    ziele = []
    zaehler = {"passt": 0, "umsetzen": 0, "fehlt": 0}
    verlierer: dict[str, list] = {}  # Charaktere außerhalb des Snapshots, denen Mods abgenommen werden

    for eid, e in snapshot_einheiten.items():
        aktuell = {m["slot"]: m for m in aktuell_einheiten.get(eid, {}).get("mods", [])}
        schritte = []
        for soll in sorted(e["mods"], key=lambda m: m["slot"]):
            ist = aktuell.get(soll["slot"])
            if ist and ist["id"] == soll["id"]:
                status, von, mod = "passt", None, ist
            elif soll["id"] in ort:
                von, mod = ort[soll["id"]]
                status = "umsetzen"
                if von not in snapshot_einheiten:
                    verlierer.setdefault(von, []).append({"slot": soll["slot"], "an": eid, "mod": mod})
            else:
                status, von, mod = "fehlt", None, soll
            zaehler[status] += 1
            schritte.append({"slot": soll["slot"], "status": status, "von": von, "mod": mod,
                             "ersetzt": ist if status != "passt" else None})
        offen = sum(1 for s in schritte if s["status"] != "passt")
        ziele.append({"id": eid, "schritte": schritte, "offen": offen})

    # Credits (Schätzung): Ausbau jeder umzusetzenden Mod beim bisherigen Träger und jeder verdrängten Mod
    ausgebaut = {}
    for z in ziele:
        for s in z["schritte"]:
            if s["status"] == "umsetzen":
                ausgebaut[s["mod"]["id"]] = s["mod"].get("ausbaukosten", 0)
            if s["status"] != "passt" and s["ersetzt"]:
                ausgebaut[s["ersetzt"]["id"]] = s["ersetzt"].get("ausbaukosten", 0)

    # Charaktere mit offenen Schritten zuerst, dann alphabetisch
    ziele.sort(key=lambda z: (z["offen"] == 0, z["id"]))
    return {
        "zaehler": zaehler,
        "credits": sum(ausgebaut.values()),
        "ziele": ziele,
        "verlierer": [{"id": k, "mods": v} for k, v in sorted(verlierer.items())],
        "fertig": zaehler["umsetzen"] == 0 and zaehler["fehlt"] == 0,
    }
