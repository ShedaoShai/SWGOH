from app import mods, vergleich


def roh_mod(mid, definition, primaer=48, sek=((5, 500000000, 1),), kosten=1000):
    return {
        "id": mid, "definitionId": definition, "level": 15, "tier": 5,
        "removeCost": {"quantity": str(kosten)},
        "primaryStat": {"stat": {"unitStatId": primaer, "unscaledDecimalValue": "5880000"}},
        "secondaryStat": [{"stat": {"unitStatId": s, "unscaledDecimalValue": str(w)}, "statRolls": r} for s, w, r in sek],
    }


def test_mod_lesen():
    m = mods.mod_lesen(roh_mod("a", "452", primaer=5, sek=((5, 1500000000, 3), (56, 3628000, 2))))
    assert (m["set"], m["pips"], m["slot"]) == (4, 5, 2)
    assert m["primaer"]["name"] == "Tempo"
    assert m["sekundaer"][0]["wert"] == 15
    assert m["sekundaer"][1]["wert"] == 3.63 and m["sekundaer"][1]["prozent"]
    assert m["ausbaukosten"] == 1000


def test_spieler_lesen_und_tempo():
    roh = {"name": "Test", "allyCode": "123456789", "rosterUnit": [
        {"definitionId": "VADER:SEVEN_STAR", "currentTier": 13, "relic": {"currentTier": 9},
         "equippedStatMod": [roh_mod("a", "451"), roh_mod("b", "452", primaer=5)]},
        {"definitionId": "SHIP:SEVEN_STAR", "equippedStatMod": []},
    ]}
    s = mods.spieler_lesen(roh)
    assert list(s["einheiten"]) == ["VADER"]
    assert s["einheiten"]["VADER"]["relikt"] == 7
    # Sekundär 5 + 5, Primär Pfeil 0.0588 (hier nur Testwert) -> nur Sekundärwerte sind ganze Zahlen
    assert mods.tempo(s["einheiten"]["VADER"]["mods"]) == 10


def einheit(*paare):
    return {"mods": [{"id": i, "slot": s, "ausbaukosten": 100} for s, i in paare]}


def test_vergleich_umsetzen_und_fehlt():
    snapshot = {"A": einheit((1, "m1"), (2, "m2"), (3, "m3")), "B": einheit((1, "m4"))}
    aktuell = {
        "A": einheit((1, "m1"), (2, "x9")),   # m1 passt, m2 woanders, m3 fehlt
        "B": einheit((1, "m4"), (2, "m2")),   # m2 liegt bei B
    }
    v = vergleich.vergleichen(snapshot, aktuell)
    assert v["zaehler"] == {"passt": 2, "umsetzen": 1, "fehlt": 1}
    a = next(z for z in v["ziele"] if z["id"] == "A")
    schritt = {s["slot"]: s for s in a["schritte"]}
    assert schritt[2]["status"] == "umsetzen" and schritt[2]["von"] == "B"
    assert schritt[2]["ersetzt"]["id"] == "x9"
    assert schritt[3]["status"] == "fehlt"
    assert v["verlierer"] == []  # B ist selbst im Snapshot
    assert v["credits"] == 200  # m2 ausbauen + x9 verdrängen
    assert not v["fertig"]


def test_vergleich_verlierer_ausserhalb_des_snapshots():
    snapshot = {"A": einheit((1, "m1"))}
    aktuell = {"A": einheit(), "C": einheit((1, "m1"))}
    v = vergleich.vergleichen(snapshot, aktuell)
    assert [l["id"] for l in v["verlierer"]] == ["C"]


def test_vergleich_fertig():
    snapshot = {"A": einheit((1, "m1"))}
    v = vergleich.vergleichen(snapshot, snapshot)
    assert v["fertig"] and v["credits"] == 0


def test_set_boni():
    def m(s, level=15):
        return {"set": s, "level": level}
    # 4 Tempo (voll), 2 Gesundheit (voll, aber ein Mod unter L15), 1 Effektivität (Rest)
    b = mods.set_boni([m(4), m(4), m(4), m(4), m(1), m(1, 12)])
    assert b["voll"] == [{"set": 4, "anzahl": 1, "max": True}, {"set": 1, "anzahl": 1, "max": False}]
    assert b["rest"] == []
    b = mods.set_boni([m(3)] * 4 + [m(7)] * 2 + [m(2)] * 0)
    assert b["voll"] == [{"set": 3, "anzahl": 2, "max": True}, {"set": 7, "anzahl": 1, "max": True}]
    b = mods.set_boni([m(2)] * 3 + [m(8)] * 3)
    assert b["voll"] == [{"set": 8, "anzahl": 1, "max": True}]
    assert b["rest"] == [{"set": 2, "mods": 3}, {"set": 8, "mods": 1}]


def test_tempo_gesamt():
    def m(s, level=15, tempo=0, slot=1):
        return {"set": s, "level": level, "slot": slot, "primaer": {"id": 48, "wert": 5.88},
                "sekundaer": [{"id": 5, "wert": tempo}] if tempo else []}
    voll = [m(4, tempo=10), m(4, tempo=5), m(4), m(4), m(1), m(1)]
    t = mods.tempo_gesamt(voll, 141, 0)
    assert t == {"grund": 141, "ausruestung": 0, "mods": 15, "set_prozent": 10, "set": 14, "gesamt": 170}
    # ein Tempo-Mod unter Level 15 -> nur 5 %
    halb = [m(4, level=12), m(4), m(4), m(4)]
    assert mods.tempo_gesamt(halb, 141)["set"] == 7
    # kein vollständiges Tempo-Set
    assert mods.tempo_gesamt([m(4), m(4), m(4), m(2)], 141)["set"] == 0
    # angelegte Ausrüstung zählt mit, Grundtempo unbekannt -> kein Gesamtwert
    assert mods.tempo_gesamt(voll, 121, 8)["gesamt"] == 121 + 8 + 15 + 12
    assert mods.tempo_gesamt(voll, None)["gesamt"] is None
