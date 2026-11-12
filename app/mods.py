"""Comlink-Rohdaten in eine schlanke, stabile Form bringen (die auch so in Snapshots gespeichert wird)."""

# Set = erste Ziffer der definitionId einer Mod
SETS = {
    1: "Gesundheit", 2: "Angriff", 3: "Verteidigung", 4: "Tempo",
    5: "Krit.-Chance", 6: "Krit.-Schaden", 7: "Effektivität", 8: "Zähigkeit",
}
# Slot = dritte Ziffer der definitionId
SLOTS = {1: "Quadrat", 2: "Pfeil", 3: "Raute", 4: "Dreieck", 5: "Kreis", 6: "Kreuz"}
# unitStatId -> Name
STATS = {
    1: "Gesundheit", 5: "Tempo", 16: "Krit.-Schaden", 17: "Effektivität", 18: "Zähigkeit", 28: "Schutz",
    41: "Angriff", 42: "Verteidigung", 48: "Angriff", 49: "Verteidigung", 52: "Genauigkeit",
    53: "Krit.-Chance", 54: "Krit.-Vermeidung", 55: "Gesundheit", 56: "Schutz",
}
PROZENT = {16, 17, 18, 48, 49, 52, 53, 54, 55, 56}
# tier 1..5 = grau, grün, blau, lila, gold (im Spiel E..A)
STUFEN = {1: "E", 2: "D", 3: "C", 4: "B", 5: "A"}


def _wert(stat: dict) -> float:
    """Comlink liefert Werte skaliert: unscaledDecimalValue = Wert × 1e8 (Prozentwerte als Anteil)."""
    sid = int(stat.get("unitStatId", 0))
    if stat.get("unscaledDecimalValue") not in (None, ""):
        wert = int(stat["unscaledDecimalValue"]) / 1e8
    else:
        wert = int(stat.get("statValueDecimal", 0)) / 1e4
    if sid in PROZENT:
        wert *= 100
    return round(wert, 2)


def _stat(roh: dict, rolls: int | None = None) -> dict:
    s = roh.get("stat", roh)
    sid = int(s.get("unitStatId", 0))
    ergebnis = {"id": sid, "name": STATS.get(sid, f"Wert {sid}"), "wert": _wert(s), "prozent": sid in PROZENT}
    if rolls is not None:
        ergebnis["rolls"] = rolls
    return ergebnis


def mod_lesen(roh: dict) -> dict:
    definition = str(roh["definitionId"])
    set_id, pips, slot = int(definition[0]), int(definition[1]), int(definition[2])
    return {
        "id": roh["id"],
        "set": set_id,
        "slot": slot,
        "pips": pips,
        "level": int(roh.get("level", 1)),
        "stufe": int(roh.get("tier", 1)),
        "ausbaukosten": int((roh.get("removeCost") or {}).get("quantity", 0) or 0),
        "primaer": _stat(roh["primaryStat"]),
        "sekundaer": [_stat(s, int(s.get("statRolls", 1))) for s in roh.get("secondaryStat", [])],
    }


def basis_id(definition_id: str) -> str:
    """'DARTHVADER:SEVEN_STAR' -> 'DARTHVADER'"""
    return definition_id.split(":")[0]


def spieler_lesen(roh: dict) -> dict:
    """Nur Einheiten mit ausgerüsteten Mods (Schiffe haben keine)."""
    einheiten = {}
    for u in roh.get("rosterUnit", []):
        mods = [mod_lesen(m) for m in u.get("equippedStatMod") or []]
        if not mods:
            continue
        bid = basis_id(u["definitionId"])
        einheiten[bid] = {
            "id": bid,
            "sterne": u.get("currentRarity"),
            "level": u.get("currentLevel"),
            "ausruestung": u.get("currentTier"),
            "relikt": max(0, int((u.get("relic") or {}).get("currentTier", 0)) - 2),
            # angelegte Ausrüstungsteile der aktuellen Stufe (für das Tempo)
            "teile": [e["equipmentId"] for e in u.get("equipment") or []],
            "mods": sorted(mods, key=lambda m: m["slot"]),
        }
    return {
        "name": roh.get("name", ""),
        "ally_code": str(roh.get("allyCode", "")),
        "level": roh.get("level"),
        "einheiten": einheiten,
    }


# Mods je Set für den Bonus (Gesundheit, Verteidigung, Krit.-Chance, Effektivität, Zähigkeit: 2; sonst 4)
SET_GROESSE = {1: 2, 2: 4, 3: 2, 4: 4, 5: 2, 6: 4, 7: 2, 8: 2}


def set_boni(mods: list[dict]) -> dict:
    """{'voll': [{'set', 'anzahl', 'max'}], 'rest': [{'set', 'mods'}]}

    anzahl = wie oft der Bonus aktiv ist; max = alle Mods des Sets auf Level 15 (voller Bonus).
    rest = Mods, die keinen vollständigen Satz bilden.
    """
    nach_set: dict[int, list[dict]] = {}
    for m in mods:
        nach_set.setdefault(m["set"], []).append(m)
    voll, rest = [], []
    for s in sorted(nach_set, key=lambda s: (-SET_GROESSE[s], s)):
        liste = nach_set[s]
        anzahl, uebrig = divmod(len(liste), SET_GROESSE[s])
        if anzahl:
            voll.append({"set": s, "anzahl": anzahl, "max": all(m["level"] >= 15 for m in liste)})
        if uebrig:
            rest.append({"set": s, "mods": uebrig})
    return {"voll": voll, "rest": rest}


def tempo(mods: list[dict]) -> float:
    """Summe Tempo aus Mods (Pfeil-Primärwert + Sekundärwerte, ohne Set-Bonus)."""
    summe = 0.0
    for m in mods:
        if m["primaer"]["id"] == 5:
            summe += m["primaer"]["wert"]
        summe += sum(s["wert"] for s in m["sekundaer"] if s["id"] == 5)
    return round(summe)


# Tempo-Set laut Spieldaten (statModSet 4): +5 % bei vollständigem Set, weitere +5 % wenn alle 4 Mods auf Level 15
TEMPO_SET_PROZENT = 5
TEMPO_SET_MAX_PROZENT = 10


def tempo_gesamt(mods: list[dict], grundtempo: int | None, ausruestung: int = 0) -> dict:
    """Aufschlüsselung des Tempos: Grundtempo (Ausrüstungsstufe) + angelegte Teile + Mods + Tempo-Set.

    Der Set-Bonus ist ein Prozentsatz des Grundtempos (abgerundet). Ohne bekanntes Grundtempo (Charakter
    neuer als die Spieldaten-Datei) sind nur die Mod-Werte bekannt; gesamt ist dann None.
    """
    tempo_set = next((s for s in set_boni(mods)["voll"] if s["set"] == 4), None)
    prozent = 0 if not tempo_set else TEMPO_SET_MAX_PROZENT if tempo_set["max"] else TEMPO_SET_PROZENT
    aus_mods = tempo(mods)
    if grundtempo is None:
        return {"grund": None, "ausruestung": ausruestung, "mods": aus_mods, "set_prozent": prozent,
                "set": None, "gesamt": None}
    set_bonus = grundtempo * prozent // 100
    return {"grund": grundtempo, "ausruestung": ausruestung, "mods": aus_mods, "set_prozent": prozent,
            "set": set_bonus, "gesamt": grundtempo + ausruestung + aus_mods + set_bonus}
