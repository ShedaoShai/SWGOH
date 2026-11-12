"use strict";
// Mod-Snapshots – Oberfläche ohne Framework. Der Ally-Code wird nur im Browser gemerkt (wenn angehakt).

const SETS = {1: "Gesundheit", 2: "Angriff", 3: "Verteidigung", 4: "Tempo", 5: "Krit.-Chance", 6: "Krit.-Schaden", 7: "Effektivität", 8: "Zähigkeit"};
const SLOTS = {1: ["■", "Quadrat"], 2: ["➜", "Pfeil"], 3: ["◆", "Raute"], 4: ["▲", "Dreieck"], 5: ["●", "Kreis"], 6: ["✚", "Kreuz"]};
const STUFEN = {1: "E", 2: "D", 3: "C", 4: "B", 5: "A"};
// Namen hier statt aus den Daten, damit auch ältere Snapshots die aktuellen Bezeichnungen zeigen
const STATS = {1: "Gesundheit", 5: "Tempo", 16: "Krit.-Schaden", 17: "Effektivität", 18: "Zähigkeit", 28: "Schutz",
  41: "Angriff", 42: "Verteidigung", 48: "Angriff", 49: "Verteidigung", 52: "Genauigkeit", 53: "Krit.-Chance",
  54: "Krit.-Vermeidung", 55: "Gesundheit", 56: "Schutz"};
const SPEICHER_ALLY = "swgoh.allycode";

const SET_GROESSE = {1: 2, 2: 4, 3: 2, 4: 4, 5: 2, 6: 4, 7: 2, 8: 2};

const $ = (s) => document.querySelector(s);
const zustand = {ally: "", spieler: null, auswahl: new Set(), snapshots: [], vergleichId: null, kategorien: {}};

// ---------- Mod-Bilder (eigene Zeichnungen in Spieloptik: Form = Slot, Rahmenfarbe = Stufe, Symbol = Set,
// Punkte = Pips). Verläufe stehen einmal im <svg id="mod-defs"> in index.html. ----------
// Je Slot: Außenform (Rahmen), Innenform (Metallkörper), Mittelpunkt und Größe des Set-Symbols (viewBox 48×48)
const FORMEN = {
  1: {aussen: '<rect x="3" y="3" width="42" height="42" rx="5"/>', innen: '<rect x="7.5" y="7.5" width="33" height="33" rx="3"/>',
      mitte: [24, 24], faktor: 1.15},
  2: {aussen: '<path d="M2 12.5H21V2L46.5 24L21 46V35.5H2Z"/>', innen: '<path d="M6 16.5H25V11L40 24L25 37V31.5H6Z"/>',
      mitte: [25, 24], faktor: 0.85},
  3: {aussen: '<path d="M24 1L47 24L24 47L1 24Z"/>', innen: '<path d="M24 7.5L40.5 24L24 40.5L7.5 24Z"/>',
      mitte: [24, 24], faktor: 1.0},
  4: {aussen: '<path d="M24 2.5L46.5 43.5H1.5Z"/>', innen: '<path d="M24 11L39.5 39.5H8.5Z"/>',
      mitte: [24, 30], faktor: 0.8},
  5: {aussen: '<circle cx="24" cy="24" r="22"/>', innen: '<circle cx="24" cy="24" r="17.5"/>',
      mitte: [24, 24], faktor: 1.1},
  6: {aussen: '<path d="M15 2H33V15H46V33H33V46H15V33H2V15H15Z"/>', innen: '<path d="M18.5 5.5H29.5V18.5H42.5V29.5H29.5V42.5H18.5V29.5H5.5V18.5H18.5Z"/>',
      mitte: [24, 24], faktor: 0.95},
};
// Stern/Explosion mit n Zacken um (20, 21)
function stern(n, aussen, innen) {
  const p = [];
  for (let i = 0; i < 2 * n; i++) {
    const r = i % 2 ? innen : aussen, w = Math.PI * i / n - Math.PI / 2;
    p.push(`${(20 + r * Math.cos(w)).toFixed(2)} ${(21 + r * Math.sin(w)).toFixed(2)}`);
  }
  return `M${p.join("L")}Z`;
}
// Set-Symbole nach den Spiel-Symbolen nachgezeichnet, mittig um (20, 21).
// voll = Fläche in Stufenfarbe, linie = Strich in Stufenfarbe, loch = dunkle Aussparung
const SYMBOLE = {
  1: '<path class="voll" d="M17.4 12.5H22.6V18.4H28.5V23.6H22.6V29.5H17.4V23.6H11.5V18.4H17.4Z"/>' +
     '<path class="loch-linie" d="M15.5 25L19 21.5L21 23L25 18.5"/>',                                         // Gesundheit: Kreuz mit Puls
  2: `<path class="voll" d="${stern(12, 8.6, 5.6)}"/><circle class="loch" cx="20" cy="21" r="2.6"/>`,         // Angriff: Strahlenkranz
  3: '<path class="voll" d="M20 12.3L27.3 15V20.8C27.3 25.3 24 28.3 20 29.8C16 28.3 12.7 25.3 12.7 20.8V15Z"/>' +
     '<path class="loch-linie" d="M20 15.2V27"/>',                                                               // Verteidigung: Schild
  4: '<circle class="voll" cx="24.2" cy="13.8" r="2.1"/>' +
     '<path class="linie" d="M22.6 17L19.6 22.6M22.2 17.6L25 20.3L27.6 19M22.2 17.6L18.6 18.4L16.6 16.6' +
     'M19.6 22.6L23.2 24.4L22.4 28.8M19.6 22.6L17.4 26L13.2 26.2M10.8 18.6H14M10 21.6H13.4"/>',             // Tempo: Läufer
  5: `<path class="voll" d="${stern(8, 9, 5.2)}"/>` +
     '<text class="loch" x="20" y="23.6" text-anchor="middle" font-size="7.5" font-weight="900">%</text>',     // Krit.-Chance
  6: `<path class="voll" d="${stern(10, 9, 5.6)}"/>` +
     '<path class="loch" d="M19 16.4H21L20.6 22.6H19.4Z"/><circle class="loch" cx="20" cy="24.9" r="1.1"/>',  // Krit.-Schaden
  7: '<circle class="linie" cx="20" cy="21" r="5.6"/><circle class="voll" cx="20" cy="21" r="1.7"/>' +
     '<path class="linie" d="M20 12V16.2M20 25.8V30M11 21H15.2M24.8 21H29"/>',                                 // Effektivität: Fadenkreuz
  8: '<path class="voll" d="M14.6 15.6C14.6 14.2 15.4 13.4 16.6 13.4H24.2C25.6 13.4 26.4 14.4 26.4 15.6V21.4' +
     'C26.4 23.6 25.4 24.8 24 25.4V29.6H16.4V25.6C15.2 24.8 14.6 23.6 14.6 22Z"/>' +
     '<path class="loch-linie" d="M17.6 13.6V18M20.4 13.6V18M23.2 13.6V18M14.8 18.2H23.6C24.2 18.2 24.4 19 23.8 19.6L21.6 21.2' +
     'M16.4 25.4H24"/>',                                                                                         // Zähigkeit: Faust
};
// Original-Grafiken aus dem Spiel (tools/mod_grafiken_laden.ps1 → /static/mods/); fehlen sie, bleiben die Zeichnungen
let ORIGINAL = null;
async function originalLaden() {
  try {
    const r = await fetch("/static/mods/mods.json", {cache: "no-cache"});
    if (r.ok) ORIGINAL = await r.json();
  } catch { /* keine Originalgrafiken */ }
}
function modUrl(datei) { return `/static/mods/${datei}?v=${encodeURIComponent(ORIGINAL.version || "")}`; }
function maske(datei) { const u = `url('${modUrl(datei)}')`; return `-webkit-mask-image:${u};mask-image:${u}`; }
const pz = (wert, basis) => `${(100 * wert / basis).toFixed(2)}%`;
// Feinkorrektur der Symbol-Lage, in Pixeln der 80×80-Rahmengrafik: Schlüssel = Slot (1 Quadrat, 2 Pfeil,
// 3 Raute, 4 Dreieck, 5 Kreis, 6 Kreuz) oder "Slot-Set"; x/y = Verschiebung, s = Größenfaktor.
// Je Kombination gemessen (12.11.2026): gleicher schwarzer Rand links/rechts und oben/unten um das Symbol.
// Dreieck: Mitte = Innenkreis (gleicher Abstand zu allen drei Seiten), daher Form-Korrektur y −1,8.
const MOD_KORREKTUR = {
  4: {y: -1.8},
  "3-1": {y: 1}, "3-2": {x: -0.5, y: 0.5}, "3-3": {y: 0.5}, "3-4": {x: -0.5}, "3-5": {x: -0.5, y: 0.5},
  "3-6": {x: -0.5, y: 0.5}, "3-8": {y: 0.5},
  "4-2": {x: -0.5}, "4-4": {x: -0.5}, "4-5": {x: -0.5}, "4-6": {x: -0.5},
  "5-1": {y: -0.5}, "5-2": {x: -0.5, y: 0.5}, "5-4": {x: -1}, "5-5": {x: -0.5, y: 0.5}, "5-6": {x: -0.5, y: 0.5}, "5-8": {y: 0.5},
  "6-1": {y: 0.5}, "6-2": {x: -0.5}, "6-4": {x: -1}, "6-5": {x: -0.5}, "6-6": {x: -0.5}, "6-8": {y: 0.5},
};
// Symbol-Kästchen wie im Spiel, je Form aus Spiel-Screenshots kalibriert (Overlay am Silberrahmen ausgerichtet):
// Mitte x/y und Kantenlänge g für ein 128-px-Symbol, in Pixeln der 80×80-Rahmengrafik. Das Spiel zeichnet das Symbol
// mit seinem Original-Leerraum in dieses Kästchen – deshalb sitzt es nicht immer in der Feldmitte.
// Formen ohne Eintrag: Flächenschwerpunkt des schwarzen Felds + MOD_KORREKTUR.
const SPIEL_KAESTCHEN = {
  1: {x: 50.25, y: 31.75, g: 28.3},  // Quadrat, Vorlage Tempo-Quadrat (12.11.2026)
  2: {x: 53.2, y: 25.8, g: 22},      // Pfeil, Mittel aus zwei Tempo-Pfeil-Screenshots (12.11.2026)
};
// Lage des Set-Symbols in Pixeln der Rahmengrafik: {x, y, w, h}
function symbolLage(slot, set) {
  const f = ORIGINAL.formen[slot] || ORIGINAL.formen[1], s = ORIGINAL.symbole[set];
  if (!s) return null;
  const kasten = SPIEL_KAESTCHEN[slot];
  if (kasten && s.voll) {
    // quadratisches Kästchen; nicht quadratische Sprites (Läufer 132×128) staucht das Spiel hinein
    const ks = MOD_KORREKTUR[`${slot}-${set}`] || {}, g = kasten.g * (ks.s || 1);
    const mx = g / s.voll[0], my = g / s.voll[1];
    return {x: kasten.x + (ks.x || 0) - g / 2 + s.versatz[0] * mx,
            y: kasten.y + (ks.y || 0) - g / 2 + s.versatz[1] * my, w: s.groesse[0] * mx, h: s.groesse[1] * my};
  }
  // Symbol in den Flächenschwerpunkt des schwarzen Felds; Größe (aus dem größten Innenkreis) wie im Spiel gut die
  // Hälfte des Felds, bei allen Formen höchstens gleich groß. Seitenverhältnis bleibt. Ausgerichtet wird die optische
  // Mitte des Symbols (halb Rechteckmitte, halb Flächenschwerpunkt), danach Feinkorrektur je Form und je Form+Set.
  const [cx, cy] = f.schwerpunkt || f.mitte;
  const kf = MOD_KORREKTUR[slot] || {}, ks = MOD_KORREKTUR[`${slot}-${set}`] || {};
  const [sb, sh] = s.groesse, platz = Math.min(1.15 * f.radius, 24) * (kf.s || 1) * (ks.s || 1);
  const k = platz / Math.max(sb, sh), w = sb * k, h = sh * k;
  const [px, py] = s.schwerpunkt || [0.5, 0.5];
  return {x: cx + (kf.x || 0) + (ks.x || 0) - w * (0.5 + px) / 2, y: cy + (kf.y || 0) + (ks.y || 0) - h * (0.5 + py) / 2, w, h};
}
function modBildOriginal(m, groesse, t) {
  const f = ORIGINAL.formen[m.slot] || ORIGINAL.formen[1], s = ORIGINAL.symbole[m.set];
  const [b, h] = f.groesse, l = symbolLage(m.slot, m.set);
  let sym = "";
  if (l) sym = `<span class="sym" style="left:${pz(l.x, b)};top:${pz(l.y, h)};width:${pz(l.w, b)};height:${pz(l.h, h)};${maske(s.datei)}"></span>`;
  const n = Math.max(1, Math.min(6, m.pips || 1));
  return `<span class="modbild original stufe-${t}${m.pips >= 6 ? " sechs" : ""}" style="--g:${groesse}px" aria-hidden="true">
    <span class="mchip"><img src="${modUrl(m.pips >= 6 && f["6dot"] ? f["6dot"] : f.base)}" alt="">
    ${f.light ? `<span class="kontur" style="${maske(f.light)}"></span>` : ""}${sym}</span>
    <span class="punkte">${Array.from({length: n}, () => `<img src="${modUrl("pip.png")}" alt="">`).join("")}</span></span>`;
}
function setSymbol(set, groesse = 18) {
  const s = ORIGINAL && ORIGINAL.symbole[set];
  if (s) return `<span class="setsymbol original" style="width:${groesse}px;height:${groesse}px;${maske(s.datei)}"></span>`;
  return `<svg class="setsymbol" viewBox="10 10 20 22" width="${groesse}" height="${groesse}" aria-hidden="true">${SYMBOLE[set] || ""}</svg>`;
}
function pips(anzahl) {
  const n = Math.max(1, Math.min(6, anzahl || 1)), abstand = 6.2, start = 24 - (n - 1) * abstand / 2;
  return Array.from({length: n}, (_, i) => `<circle cx="${start + i * abstand}" cy="53" r="2.3"/>`).join("");
}
function modBild(m, groesse = 42) {
  const f = FORMEN[m.slot] || FORMEN[1];
  const t = Math.min(5, Math.max(1, m.stufe || 1));
  if (ORIGINAL) return modBildOriginal(m, groesse, t);
  const [cx, cy] = f.mitte;
  return `<svg class="modbild stufe-${t}${m.pips >= 6 ? " sechs" : ""}" viewBox="0 0 48 57" width="${groesse}" height="${Math.round(groesse * 57 / 48)}" aria-hidden="true">
    <g class="rahmen" fill="url(#mod-silber)">${f.aussen}</g>
    <g class="koerper" fill="url(#mod-koerper)" stroke="url(#mod-rand-${t})">${f.innen}</g>
    <g class="glanz" fill="url(#mod-glanz)">${f.innen}</g>
    <g class="symbol" transform="translate(${cx} ${cy}) scale(${f.faktor}) translate(-20 -21)">
      <rect class="kachel" x="9.5" y="10.5" width="21" height="21" rx="3.5" stroke="url(#mod-rand-${t})"/>${SYMBOLE[m.set] || ""}</g>
    <g class="pips">${pips(m.pips)}</g></svg>`;
}

// ---------- Hilfen ----------
function esc(t) {
  return String(t ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
}
function speicherLesen(k) { try { return localStorage.getItem(k); } catch { return null; } }
function speicherSchreiben(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch { /* egal */ } }
function zeit(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("de-DE", {dateStyle: "medium", timeStyle: "short"});
}
function zahl(n) { return Number(n).toLocaleString("de-DE"); }
function allyFormat(c) { return c.replace(/^(\d{3})(\d{3})(\d{3})$/, "$1-$2-$3"); }

// ---------- Farbmodus: Automatisch (Systemeinstellung) → Hell → Dunkel ----------
const FARBMODI = [
  {wert: "auto", text: "Automatisch", symbol: "◐"},
  {wert: "hell", text: "Hell", symbol: "☀"},
  {wert: "dunkel", text: "Dunkel", symbol: "☾"},
];
function farbmodusSetzen(wert) {
  const modus = FARBMODI.find((m) => m.wert === wert) || FARBMODI[0];
  if (modus.wert === "auto") delete document.documentElement.dataset.farbmodus;
  else document.documentElement.dataset.farbmodus = modus.wert;
  speicherSchreiben("farbmodus", modus.wert === "auto" ? null : modus.wert);
  const knopf = $("#farbmodus");
  knopf.querySelector(".symbol").textContent = modus.symbol;
  knopf.querySelector(".text").textContent = modus.text;
  knopf.setAttribute("aria-label", `Farbmodus: ${modus.text} (klicken zum Wechseln)`);
}
farbmodusSetzen(speicherLesen("farbmodus") || "auto");
$("#farbmodus").addEventListener("click", () => {
  const jetzt = document.documentElement.dataset.farbmodus || "auto";
  const i = FARBMODI.findIndex((m) => m.wert === jetzt);
  farbmodusSetzen(FARBMODI[(i + 1) % FARBMODI.length].wert);
});

function meldung(text, art = "") {
  const m = $("#meldung");
  m.hidden = !text;
  m.textContent = text || "";
  m.className = "meldung " + art;
  if (text && art === "ok") setTimeout(() => { if (m.textContent === text) m.hidden = true; }, 4000);
}

async function api(pfad, optionen = {}) {
  const antwort = await fetch(pfad, {
    ...optionen,
    headers: optionen.body ? {"Content-Type": "application/json"} : {},
  });
  const daten = await antwort.json().catch(() => ({}));
  if (!antwort.ok) {
    const d = daten.detail;
    throw new Error(Array.isArray(d) ? d.map((x) => x.msg).join(", ") : d || `Fehler ${antwort.status}`);
  }
  return daten;
}

async function beschaeftigt(knopf, fn) {
  const alt = knopf?.textContent;
  if (knopf) { knopf.disabled = true; knopf.textContent = "Bitte warten …"; }
  try { return await fn(); }
  catch (e) { meldung(e.message); }
  finally { if (knopf) { knopf.disabled = false; knopf.textContent = alt; } }
}

// ---------- Mod-Darstellung ----------
function wertText(s) {
  const w = s.prozent ? s.wert.toLocaleString("de-DE", {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " %"
                      : zahl(Math.round(s.wert));
  return `+${w} ${STATS[s.id] || s.name}`;
}
function modHtml(m) {
  if (!m) return `<div class="mod leer klein">– leer –</div>`;
  const [symbol, slotName] = SLOTS[m.slot] || ["?", ""];
  const sek = m.sekundaer.map((s) =>
    `<div class="${s.id === 5 ? "tempo" : ""}"${s.rolls > 1 ? ` title="${s.rolls}× verbessert"` : ""}>${esc(wertText(s))}${s.rolls > 1 ? ` <span class="rolls">(${s.rolls})</span>` : ""}</div>`).join("");
  return `<div class="mod stufe-${m.stufe}" title="${esc(slotName)} · ${esc(SETS[m.set])} · ${m.pips}-Punkte · Stufe ${STUFEN[m.stufe] || ""} · Level ${m.level}">
    ${modBild(m)}
    <div class="mod-text">
      <div class="mod-kopf"><span class="set">${esc(SETS[m.set] || "?")}</span>
        <span class="pips">${m.pips}•${STUFEN[m.stufe] || ""} L${m.level}</span></div>
      <div class="primaerwert">${esc(wertText(m.primaer))}</div>
      <div class="sek">${sek}</div></div></div>`;
}
function setsHtml(e) {
  if (!e.sets) return "";
  const voll = e.sets.voll.map((s) =>
    `<span class="setbonus ${s.max ? "" : "teil"}" title="${esc(SETS[s.set])}-Set${s.anzahl > 1 ? ` ×${s.anzahl}` : ""} vollständig${s.max ? "" : " – noch nicht alle Mods auf Level 15, daher nur halber Bonus"}">
      ${setSymbol(s.set, 16)}${esc(SETS[s.set])}${s.anzahl > 1 ? ` ×${s.anzahl}` : ""}${s.max ? "" : " ½"}</span>`).join("");
  const rest = e.sets.rest.map((r) =>
    `<span class="setrest" title="${r.mods} von ${SET_GROESSE[r.set]} ${esc(SETS[r.set])}-Mods – kein Bonus">${setSymbol(r.set, 14)}${r.mods}/${SET_GROESSE[r.set]}</span>`).join("");
  return `<div class="sets">${voll || `<span class="setrest">kein vollständiges Set</span>`}${rest}</div>`;
}
// Porträt (aus dem Spiel, per tools/bilder_laden.py); ohne Bild ein Kreis mit Anfangsbuchstaben
function portrait(e) {
  if (e.bild) return `<img class="portrait" src="${esc(e.bild)}" alt="" loading="lazy" width="36" height="36">`;
  return `<span class="portrait leer" aria-hidden="true">${esc((e.name || "?").charAt(0))}</span>`;
}

// Kopfzeile einer Charakterkarte: Stufe und Tempo (HTML)
function einheitInfo(e) {
  const stufe = e.relikt > 0 ? `R${e.relikt}` : e.ausruestung ? `G${e.ausruestung}` : "";
  const t = e.tempo;
  if (!t || typeof t !== "object") return esc(stufe);
  let tempoHtml;
  if (t.gesamt == null) {
    tempoHtml = `<span title="Grundtempo unbekannt (Charakter neuer als die Spieldaten-Datei)">+${t.mods} Tempo aus Mods</span>`;
  } else {
    const teile = [`Grundtempo ${t.grund} (Ausrüstungsstufe)`];
    if (t.ausruestung) teile.push(`+ ${t.ausruestung} angelegte Ausrüstung`);
    teile.push(`+ ${t.mods} aus Mods`);
    if (t.set_prozent) teile.push(`+ ${t.set} Tempo-Set (${t.set_prozent} %${t.set_prozent < 10 ? ", erst 10 % wenn alle 4 Mods Level 15" : ""})`);
    teile.push(`= ${t.gesamt}`);
    tempoHtml = `<span class="tempo-gesamt" title="${esc(teile.join("\n"))}">${t.gesamt} Tempo</span>`;
  }
  return `${esc(stufe)}${stufe ? " · " : ""}${tempoHtml}`;
}
function modsRaster(e) {
  const nachSlot = Object.fromEntries(e.mods.map((m) => [m.slot, m]));
  return `${setsHtml(e)}<div class="mods">${[1, 2, 3, 4, 5, 6].map((s) => modHtml(nachSlot[s])).join("")}</div>`;
}

// ---------- Reiter ----------
function reiter(name) {
  document.querySelectorAll(".reiter button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.reiter === name)));
  document.querySelectorAll(".bereich").forEach((s) => { s.hidden = s.id !== name; });
}
document.querySelectorAll(".reiter button").forEach((b) => b.addEventListener("click", () => {
  reiter(b.dataset.reiter);
  if (b.dataset.reiter === "snapshots") snapshotsLaden();
}));

// ---------- Spieler / aktuelle Mods ----------
function spielerZeigen(s) {
  zustand.spieler = s;
  $("#start").hidden = true;
  $("#inhalt").hidden = false;
  $("#spieler-name").textContent = s.name;
  $("#spieler-info").textContent = `${allyFormat(s.ally_code)} · ${s.einheiten.length} Charaktere mit Mods · ${zahl(s.anzahl_mods)} Mods · abgerufen ${zeit(s.abgerufen)}`;
  const vorhanden = new Set(s.einheiten.map((e) => e.id));
  zustand.auswahl = new Set([...zustand.auswahl].filter((id) => vorhanden.has(id)));
  modsZeigen();
}

function modsZeigen() {
  const s = zustand.spieler;
  if (!s) return;
  const liste = gefiltert();
  $("#treffer-info").textContent = liste.length < s.einheiten.length ? `${liste.length} von ${s.einheiten.length} angezeigt` : "";
  $("#gefilterte-waehlen").hidden = liste.length === s.einheiten.length || liste.every((e) => zustand.auswahl.has(e.id));
  $("#mod-liste").innerHTML = liste.length ? liste.map((e) => `
    <article class="einheit ${zustand.auswahl.has(e.id) ? "gewaehlt" : ""}" data-id="${esc(e.id)}">
      <div class="einheit-kopf"><label><input type="checkbox" ${zustand.auswahl.has(e.id) ? "checked" : ""}>
        ${portrait(e)}<h3>${esc(e.name)}</h3></label><span class="klein">${einheitInfo(e)}</span></div>
      ${modsRaster(e)}
    </article>`).join("") : `<div class="platzhalter">Keine Charaktere gefunden.</div>`;
  auswahlInfo();
}

function gefiltert() {
  const suche = $("#suche").value.trim().toLowerCase();
  const fraktion = $("#fraktion").value;
  const nurAuswahl = $("#nur-auswahl").checked;
  return zustand.spieler.einheiten.filter((e) =>
    (!suche || e.name.toLowerCase().includes(suche) || e.id.toLowerCase().includes(suche)) &&
    (!fraktion || (fraktion === "-" ? !e.kategorien.length : e.kategorien.includes(fraktion))) &&
    (!nurAuswahl || zustand.auswahl.has(e.id)));
}

async function kategorienLaden() {
  try {
    const d = await api("/api/kategorien");
    zustand.kategorien = d.kategorien;
    const gruppen = {};
    for (const [id, k] of Object.entries(d.kategorien)) (gruppen[k.gruppe] ||= []).push([id, k.name]);
    const reihenfolge = ["Fraktion", "Rolle", "Seite"];
    $("#fraktion").innerHTML = `<option value="">Alle Fraktionen</option>` + reihenfolge.filter((g) => gruppen[g]).map((g) =>
      `<optgroup label="${g}">${gruppen[g].sort((a, b) => a[1].localeCompare(b[1], "de"))
        .map(([id, n]) => `<option value="${esc(id)}">${esc(n)}</option>`).join("")}</optgroup>`).join("") +
      `<option value="-">ohne Zuordnung (neue Charaktere)</option>`;
  } catch { /* Filter bleibt leer */ }
}

function auswahlInfo() {
  const n = zustand.auswahl.size;
  $("#auswahl-info").textContent = n ? `${n} ausgewählt` : "";
  $("#auswahl-leeren").hidden = !n;
}

$("#mod-liste").addEventListener("change", (ev) => {
  const karte = ev.target.closest(".einheit");
  if (!karte || ev.target.type !== "checkbox") return;
  ev.target.checked ? zustand.auswahl.add(karte.dataset.id) : zustand.auswahl.delete(karte.dataset.id);
  karte.classList.toggle("gewaehlt", ev.target.checked);
  auswahlInfo();
});
// Tempo-Aufschlüsselung per Klick/Tippen auf- und zuklappen (auf dem Handy gibt es keinen Hover-Hinweis)
document.addEventListener("click", (ev) => {
  const t = ev.target.closest(".tempo-gesamt");
  if (!t) return;
  ev.preventDefault();
  const karte = t.closest(".einheit");
  const vorhanden = karte.querySelector(".tempo-detail");
  if (vorhanden) { vorhanden.remove(); return; }
  const d = document.createElement("div");
  d.className = "tempo-detail";
  d.textContent = t.title.split("\n").join(" ");
  karte.querySelector(".einheit-kopf").after(d);
});
$("#suche").addEventListener("input", modsZeigen);
$("#nur-auswahl").addEventListener("change", modsZeigen);
$("#fraktion").addEventListener("change", modsZeigen);
$("#gefilterte-waehlen").addEventListener("click", () => {
  gefiltert().forEach((e) => zustand.auswahl.add(e.id));
  modsZeigen();
});
$("#auswahl-leeren").addEventListener("click", () => { zustand.auswahl.clear(); modsZeigen(); });

async function abrufen(knopf) {
  const s = await api(`/api/spieler/${zustand.ally}/abrufen`, {method: "POST"});
  spielerZeigen(s);
  return s;
}

$("#ally-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const roh = $("#ally").value.replace(/[\s-]/g, "");
  if (!/^\d{9}$/.test(roh)) { meldung("Der Ally-Code besteht aus 9 Ziffern (z. B. 123-456-789)."); return; }
  const wechsel = zustand.ally && zustand.ally !== roh;
  zustand.ally = roh;
  if (wechsel) { zustand.auswahl.clear(); $("#reiter-vergleich").hidden = $("#reiter-ansicht").hidden = true; reiter("mods"); }
  $("#ally").value = allyFormat(roh);
  speicherSchreiben(SPEICHER_ALLY, $("#merken").checked ? roh : null);
  meldung("");
  await beschaeftigt(ev.submitter || $("#ally-form button"), async () => {
    await abrufen();
    await snapshotsLaden();
  });
});
$("#merken").addEventListener("change", () => {
  speicherSchreiben(SPEICHER_ALLY, $("#merken").checked && zustand.ally ? zustand.ally : null);
});

// ---------- Snapshots ----------
async function snapshotsLaden() {
  if (!zustand.ally) return;
  try {
    zustand.snapshots = await api(`/api/spieler/${zustand.ally}/snapshots`);
  } catch (e) { meldung(e.message); return; }
  $("#anzahl-snapshots").textContent = zustand.snapshots.length || "";
  $("#snapshot-liste").innerHTML = zustand.snapshots.length ? zustand.snapshots.map((s) => `
    <div class="snap" data-id="${s.id}">
      <div class="titel"><h3>${esc(s.name)}</h3>
        <div class="klein">${zeit(s.erstellt)} · ${s.anzahl_einheiten} Charaktere · ${s.anzahl_mods} Mods</div>
        ${s.notiz ? `<div class="notiz">${esc(s.notiz)}</div>` : ""}</div>
      <div class="knoepfe">
        <button data-aktion="vergleich" class="primaer">Wiederherstellen</button>
        <button data-aktion="ansehen">Ansehen</button>
        <button data-aktion="bearbeiten">Bearbeiten</button>
        <button data-aktion="loeschen" class="gefahr">Löschen</button>
      </div>
    </div>`).join("")
    : `<div class="platzhalter">Noch keine Snapshots. Unter <b>Aktuelle Mods</b> kannst du den jetzigen Stand speichern.</div>`;
}

$("#snapshot-liste").addEventListener("click", async (ev) => {
  const knopf = ev.target.closest("button[data-aktion]");
  if (!knopf) return;
  const id = Number(knopf.closest(".snap").dataset.id);
  const snap = zustand.snapshots.find((s) => s.id === id);
  if (knopf.dataset.aktion === "vergleich") return vergleichOeffnen(id, knopf);
  if (knopf.dataset.aktion === "ansehen") return ansehen(id, knopf);
  if (knopf.dataset.aktion === "bearbeiten") return dialogOeffnen(snap);
  if (knopf.dataset.aktion === "loeschen") {
    if (!confirm(`Snapshot „${snap.name}“ wirklich löschen? Das lässt sich nicht rückgängig machen.`)) return;
    await beschaeftigt(knopf, async () => {
      await api(`/api/snapshots/${id}`, {method: "DELETE"});
      if (zustand.vergleichId === id) { $("#reiter-vergleich").hidden = true; }
      meldung(`Snapshot „${snap.name}“ gelöscht.`, "ok");
      await snapshotsLaden();
    });
  }
});

// Dialog: neu oder bearbeiten
let dialogSnapshot = null;
function dialogOeffnen(snap = null) {
  dialogSnapshot = snap;
  $("#dlg-titel").textContent = snap ? "Snapshot bearbeiten" : "Snapshot erstellen";
  $("#snap-name").value = snap?.name || "";
  $("#snap-notiz").value = snap?.notiz || "";
  $("#snap-umfang").hidden = $("#snap-hinweis").hidden = !!snap;
  const n = zustand.auswahl.size;
  $("#umfang-alle").textContent = `alle Charaktere (${zustand.spieler?.einheiten.length ?? 0})`;
  $("#umfang-auswahl").textContent = `nur ausgewählte (${n})`;
  document.querySelector('input[name=umfang][value=auswahl]').disabled = !n;
  document.querySelector(`input[name=umfang][value=${n ? "auswahl" : "alle"}]`).checked = true;
  $("#dlg-snapshot").showModal();
}
$("#snapshot-neu").addEventListener("click", () => dialogOeffnen());

$("#form-snapshot").addEventListener("submit", async (ev) => {
  if (ev.submitter?.value !== "ok") return;
  ev.preventDefault();
  const name = $("#snap-name").value.trim();
  const notiz = $("#snap-notiz").value.trim();
  if (!name) return;
  const knopf = ev.submitter;
  await beschaeftigt(knopf, async () => {
    if (dialogSnapshot) {
      await api(`/api/snapshots/${dialogSnapshot.id}`, {method: "PUT", body: JSON.stringify({name, notiz})});
      meldung("Snapshot gespeichert.", "ok");
    } else {
      const umfang = document.querySelector("input[name=umfang]:checked").value;
      await abrufen();
      const einheiten = umfang === "auswahl" ? [...zustand.auswahl] : null;
      const s = await api(`/api/spieler/${zustand.ally}/snapshots`, {method: "POST", body: JSON.stringify({name, notiz, einheiten})});
      meldung(`Snapshot „${s.name}“ gespeichert (${s.anzahl_einheiten} Charaktere, ${s.anzahl_mods} Mods).`, "ok");
    }
    $("#dlg-snapshot").close();
    await snapshotsLaden();
  });
});

// ---------- Snapshot ansehen ----------
async function ansehen(id, knopf) {
  await beschaeftigt(knopf, async () => {
    const s = await api(`/api/snapshots/${id}`);
    $("#ansicht").innerHTML = `
      <h2>${esc(s.name)} <span class="anzahl">${zeit(s.erstellt)}</span></h2>
      ${s.notiz ? `<p class="klein">${esc(s.notiz)}</p>` : ""}
      <div class="karten">${s.einheiten.map((e) => `
        <article class="einheit"><div class="einheit-kopf">${portrait(e)}<h3>${esc(e.name)}</h3>
          <span class="klein">${einheitInfo(e)}</span></div>${modsRaster(e)}</article>`).join("")}</div>`;
    $("#reiter-ansicht").hidden = false;
    $("#reiter-ansicht").textContent = `Snapshot: ${s.name}`;
    reiter("ansicht");
  });
}

// ---------- Vergleich / Umbau-Liste ----------
const erledigtSchluessel = (id) => `swgoh.erledigt.${id}`;
function erledigtLesen(id) { try { return new Set(JSON.parse(speicherLesen(erledigtSchluessel(id)) || "[]")); } catch { return new Set(); } }
function erledigtSchreiben(id, menge) { speicherSchreiben(erledigtSchluessel(id), JSON.stringify([...menge])); }

async function vergleichOeffnen(id, knopf) {
  zustand.vergleichId = id;
  await beschaeftigt(knopf, async () => {
    await abrufen();
    const v = await api(`/api/snapshots/${id}/vergleich`);
    vergleichZeigen(v);
    $("#reiter-vergleich").hidden = false;
    $("#reiter-vergleich").textContent = `Umbau: ${v.snapshot.name}`;
    reiter("vergleich");
  });
}

function schrittHtml(s, erledigt) {
  const schluessel = `${s.mod.id}`;
  const statusText = {passt: "✓ sitzt bereits", umsetzen: s.von ? `von ${s.von_name}` : "umsetzen",
                      fehlt: "nicht gefunden (im Inventar oder verkauft?)"}[s.status];
  const ersetzt = s.ersetzt && s.status !== "passt" ? `<span class="klein">ersetzt ${esc(SETS[s.ersetzt.set])}-Mod (${esc(wertText(s.ersetzt.primaer))})</span>` : "";
  return `<div class="schritt ${erledigt.has(schluessel) ? "erledigt" : ""}" data-schluessel="${esc(schluessel)}">
    <input type="checkbox" ${s.status === "passt" ? "checked disabled" : erledigt.has(schluessel) ? "checked" : ""} title="erledigt">
    <div class="info"><div class="zeile1"><b>${SLOTS[s.slot][0]} ${SLOTS[s.slot][1]}</b>
      <span class="status-${s.status}">${esc(statusText)}</span>${ersetzt}</div>
      ${s.status !== "passt" ? modHtml(s.mod) : ""}</div></div>`;
}

function vergleichZeigen(v) {
  const erledigt = erledigtLesen(v.snapshot.id);
  const z = v.zaehler;
  const verlierer = v.verlierer.length ? `<div class="hinweisbox"><b>Achtung:</b> Diese Charaktere sind nicht im Snapshot und verlieren Mods:
    <ul>${v.verlierer.map((l) => `<li>${esc(l.name)}: ${l.mods.map((m) => `${SLOTS[m.slot][1]} → ${esc(m.an_name)}`).join(", ")}</li>`).join("")}</ul></div>` : "";
  const fehlt = z.fehlt ? `<div class="hinweisbox">${z.fehlt} Mod(s) trägt gerade kein Charakter. Sie liegen vermutlich im Inventar
    (das über Comlink nicht sichtbar ist) oder wurden verkauft. Im Spiel nach Set, Slot und Primärwert filtern.</div>` : "";
  $("#vergleich").innerHTML = `
    <div class="werkzeuge"><h2 style="margin:0">Umbau auf „${esc(v.snapshot.name)}“</h2>
      <button id="vergleich-neu" class="primaer">Neu abrufen &amp; prüfen</button></div>
    <div class="klein">Snapshot vom ${zeit(v.snapshot.erstellt)} · Stand im Spiel: ${zeit(v.abgerufen)}</div>
    <div class="zusammenfassung">
      ${v.fertig ? `<span class="chip gut">✓ Alles wie im Snapshot</span>` : ""}
      <span class="chip gut">${z.passt} passen</span>
      ${z.umsetzen ? `<span class="chip">${z.umsetzen} umsetzen</span>` : ""}
      ${z.fehlt ? `<span class="chip schlecht">${z.fehlt} nicht gefunden</span>` : ""}
      ${v.credits ? `<span class="chip warn">ca. ${zahl(v.credits)} Credits Ausbaukosten</span>` : ""}
      <label class="klein"><input type="checkbox" id="fertige-zeigen"> fertige Charaktere zeigen</label>
    </div>
    ${verlierer}${fehlt}
    <p class="klein">Im Spiel: Charakter öffnen, Slot antippen und die genannte Mod auswählen. Trägt sie ein anderer Charakter,
      wird sie ihm automatisch abgenommen. Abhaken merkt sich nur dieser Browser. Zum Schluss <b>Neu abrufen &amp; prüfen</b>.</p>
    <div id="ziele">${v.ziele.map((ziel) => `
      <details class="ziel" data-fertig="${ziel.offen === 0}" ${ziel.offen ? "open" : "hidden"}>
        <summary>${portrait(ziel)}<h3>${esc(ziel.name)}</h3><span class="rest klein">${ziel.offen ? `${ziel.offen} offen` : "✓ fertig"}</span></summary>
        <div class="schritte">${ziel.schritte.map((s) => schrittHtml(s, erledigt)).join("")}</div>
      </details>`).join("")}</div>`;

  $("#vergleich-neu").addEventListener("click", (ev) => vergleichOeffnen(v.snapshot.id, ev.currentTarget));
  $("#fertige-zeigen").addEventListener("change", (ev) => {
    document.querySelectorAll('#ziele .ziel[data-fertig="true"]').forEach((d) => { d.hidden = !ev.target.checked; });
  });
  $("#ziele").addEventListener("change", (ev) => {
    const zeile = ev.target.closest(".schritt");
    if (!zeile) return;
    const menge = erledigtLesen(v.snapshot.id);
    ev.target.checked ? menge.add(zeile.dataset.schluessel) : menge.delete(zeile.dataset.schluessel);
    erledigtSchreiben(v.snapshot.id, menge);
    zeile.classList.toggle("erledigt", ev.target.checked);
  });
}

// ---------- Start ----------
(async function start() {
  await Promise.all([kategorienLaden(), originalLaden()]);
  const gemerkt = speicherLesen(SPEICHER_ALLY);
  if (gemerkt) {
    $("#ally").value = allyFormat(gemerkt);
    zustand.ally = gemerkt;
    try {
      spielerZeigen(await api(`/api/spieler/${gemerkt}`));
      await snapshotsLaden();
    } catch { /* noch kein Abruf: Nutzer klickt selbst */ }
  }
  try {
    const st = await api("/api/status");
    $("#version").textContent = `Version ${st.version || "Entwicklung"}` + (st.comlink ? "" : " · Comlink nicht erreichbar");
    if (!st.comlink) meldung("Comlink ist nicht erreichbar. Läuft der Comlink-Container?", "info");
  } catch { /* ignorieren */ }
})();
