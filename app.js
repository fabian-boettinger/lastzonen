/* Lastzonen Deutschland – Logik
   Daten: zonen.json (aus DIBt-Tabellen, build_zonen.py), eingebettet in <script id="zonen">. */
let ZONEN = null;
try { ZONEN = JSON.parse(document.getElementById('zonen').textContent); } catch (e) { ZONEN = null; }

const $ = id => document.getElementById(id);
const fmt = (x, d = 2) => Number.isFinite(x) ? x.toLocaleString('de-DE', {minimumFractionDigits: d, maximumFractionDigits: d}) : '–';
const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

const LAND = {
  'Schleswig-Holstein': 'SH', 'Hamburg': 'HH', 'Niedersachsen': 'NI', 'Bremen': 'HB', 'Nordrhein-Westfalen': 'NW',
  'Hessen': 'HE', 'Rheinland-Pfalz': 'RP', 'Baden-Württemberg': 'BW', 'Bayern': 'BY', 'Saarland': 'SL', 'Berlin': 'BE',
  'Brandenburg': 'BB', 'Mecklenburg-Vorpommern': 'MV', 'Sachsen': 'SN', 'Sachsen-Anhalt': 'ST', 'Thüringen': 'TH'
};

/* ---------- Namensabgleich ---------- */
function norm(s) {
  return (s || '').toLowerCase()
    .replace(/^(landkreis|kreis|stadtkreis|kreisfreie stadt|städteregion|region|regierungsbezirk|direktionsbezirk|lk|sk|stadt)\s+/, '')
    .replace(/,\s*stadt.*$/, '')
    .replace(/\ba\.\s*d\.\s*/g, 'an der ').replace(/\bi\.\s*d\.\s*/g, 'in der ')
    .replace(/\ba\.\s*/g, 'am ').replace(/\bi\.\s*/g, 'im ').replace(/\bv\.\s*/g, 'vor ')
    .replace(/[.\-–]/g, ' ').replace(/\s+/g, ' ').trim();
}
const bare = s => norm(s).replace(/\s*\(.*?\)\s*/g, ' ').replace(/\/.*$/, '').trim();
function same(a, b) {
  if (!a || !b) return false;
  const x = norm(a), y = norm(b);
  return x === y || bare(a) === bare(b);
}
/* Gemeindenamen zusätzlich mit Zusatz vergleichen: "Isny" = "Isny im Allgäu" */
function sameGem(a, b) {
  if (same(a, b)) return true;
  const x = bare(a), y = bare(b);
  return x.length >= 4 && y.length >= 4 && (x.startsWith(y + ' ') || y.startsWith(x + ' '));
}

/* ---------- Regelauswahl ----------
   Punkte: Gemeindeschlüssel 100, Schlüsselbereich 85, Gemeindename 80 (Ortsteil 75),
   Kreis 45/40 (Ausnahme/Standard), Regierungsbezirk 30, ganzes Land 10. */
function score(r, loc) {
  if (r.kf !== undefined && loc.kf !== undefined && r.kf !== loc.kf && !r.gem) return -1;
  const kreisOk = !r.kreise || r.kreise.some(k => same(k, loc.kreis));
  const regOk = !r.regbez || same(r.regbez, loc.regbez);
  if (r.ags) {
    if (loc.ags) return r.ags === loc.ags ? 100 : -1;
    return r.gem && r.gem.some(g => same(g, loc.gem)) && kreisOk ? 70 : -1;
  }
  if (r.agsp) {
    if (loc.ags) return loc.ags.startsWith(r.agsp) ? 85 : -1;
    return kreisOk && r.kreise ? 35 : -1;
  }
  if (r.gem && r.gem.length) {
    const exact = r.gem.some(g => same(g, loc.gem));
    if (!exact && !(r.gem.some(g => sameGem(g, loc.gem)) && r.kreise && kreisOk)) return -1;
    if (r.kreise && loc.kreis && !kreisOk) return -1;
    return (r.teil ? 75 : 80) - (exact ? 0 : 3);
  }
  if (r.kreise) return kreisOk && regOk ? (r.default ? 40 : 45) : -1;
  if (r.regbez) return regOk ? (r.default ? 25 : 30) : -1;
  return r.default ? 10 : -1;
}

function lookup(typ, loc) {
  if (!ZONEN || !ZONEN[typ]) return null;
  const scored = ZONEN[typ].filter(r => r.land === loc.land)
    .map(r => ({r, s: score(r, loc)})).filter(x => x.s >= 0).sort((a, b) => b.s - a.s);
  if (!scored.length) return {best: null, alts: []};
  const best = scored[0];
  /* Weitere Treffer nur bei geteilten Gemeinden (Ortsteil-Regeln) */
  const alts = scored.filter(x => x !== best && x.s >= 70 && x.r.zone !== best.r.zone && (x.r.teil || best.r.teil));
  return {best: best.r, score: best.s, alts: alts.map(x => x.r)};
}

function quelle(r, s) {
  if (s >= 100) return 'Gemeindeschlüssel ' + r.ags;
  if (s >= 85) return 'Schlüsselbereich Kreis ' + r.agsp;
  if (s >= 70) return 'Gemeinde ' + (r.gem || [])[0] + (r.teil ? ' (Ortsteil ' + r.teil + ')' : '');
  if (s >= 40) return 'Kreis ' + (r.kreise || []).join(', ') + (r.default ? ' (alle übrigen Gemeinden)' : '');
  if (s >= 25) return 'Regierungsbezirk ' + r.regbez;
  return 'ganzes Land';
}

/* ---------- Schnee: DIN EN 1991-1-3/NA, Gl. NA.1–NA.3 ---------- */
function snow(zone, A, tiefland, skFix) {
  const base = {'1': [0.19, 0.91, 0.65], '2': [0.25, 1.91, 0.85], '3': [0.31, 2.91, 1.10]};
  const known = ['1', '1a', '2', '2a', '3'].includes(zone);
  const key = known ? zone.replace('a', '') : '3';
  const [c0, c1, min] = base[key];
  let sk = Math.max(min, c0 + c1 * ((A + 140) / 760) ** 2);
  const a = known && zone.endsWith('a');
  if (a) sk *= 1.25;
  let f = `s_k = max(${fmt(min)}; ${c0} + ${c1}·((A+140)/760)²)${a ? ' · 1,25' : ''}`;
  let warn = null;
  if (!known) {
    warn = `Zone „${zone}“ ist in DIN EN 1991-1-3/NA nicht geregelt. Gerechnet mit Zone 3 als Untergrenze – Wert bei der Bauaufsicht klären.`;
  }
  if (Number.isFinite(skFix)) { sk = Math.max(sk, skFix); f += `\nTabellenwert s_k = ${fmt(skFix)} kN/m² maßgebend, falls größer`; }
  const sAd = (tiefland && (key === '1' || key === '2')) ? 2.3 * sk : null;
  if (sAd) f += '\ns_Ad = 2,3 · s_k   (Norddeutsches Tiefland, außergewöhnlich)';
  return {sk, sAd, f, warn, min: a ? min * 1.25 : min};
}

/* ---------- Wind: DIN EN 1991-1-4/NA, Tab. NA.A.1 und NA.B.2/B.3 ---------- */
const WZ = {'1': [22.5, 0.32], '2': [25.0, 0.39], '3': [27.5, 0.47], '4': [30.0, 0.56]};
function wind(zone, terrain, z, A) {
  const [vb0, qb] = WZ[zone];
  let qp, f;
  if (terrain === 'binnen') {
    if (z <= 7) { qp = 1.5 * qb; f = 'q_p = 1,5·q_b  (z ≤ 7 m)'; }
    else if (z <= 50) { qp = 1.7 * qb * (z / 10) ** 0.37; f = 'q_p = 1,7·q_b·(z/10)^0,37  (7 < z ≤ 50 m)'; }
    else { qp = 2.1 * qb * (z / 10) ** 0.24; f = 'q_p = 2,1·q_b·(z/10)^0,24  (50 < z ≤ 300 m)'; }
  } else if (terrain === 'kueste') {
    if (z <= 4) { qp = 1.8 * qb; f = 'q_p = 1,8·q_b  (z ≤ 4 m)'; }
    else if (z <= 50) { qp = 2.3 * qb * (z / 10) ** 0.27; f = 'q_p = 2,3·q_b·(z/10)^0,27  (4 < z ≤ 50 m)'; }
    else { qp = 2.6 * qb * (z / 10) ** 0.19; f = 'q_p = 2,6·q_b·(z/10)^0,19  (50 < z ≤ 300 m)'; }
  } else {
    if (z <= 2) { qp = 1.1; f = 'q_p = 1,1 kN/m²  (z ≤ 2 m)'; }
    else { qp = 1.5 * qb * (z / 10) ** 0.19; f = 'q_p = 1,5·q_b·(z/10)^0,19  (2 < z ≤ 300 m)'; }
  }
  if (A > 800) { const fH = 0.2 + A / 1000; qp *= fH; f += `\n· (0,2 + A/1000) = ${fmt(fH, 3)}  (A > 800 m)`; }
  const T = {
    '1': {binnen: [0.50, 0.65, 0.75]},
    '2': {binnen: [0.65, 0.80, 0.90], kueste: [0.85, 1.00, 1.10]},
    '3': {binnen: [0.80, 0.95, 1.10], kueste: [1.05, 1.20, 1.30]},
    '4': {binnen: [0.95, 1.15, 1.30], kueste: [1.25, 1.40, 1.55], inseln: [1.40, null, null]}
  };
  let simp = null;
  const row = T[zone][terrain];
  if (row && z <= 25 && A <= 800) simp = z <= 10 ? row[0] : z <= 18 ? row[1] : row[2];
  return {vb0, qb, qp, f, simp};
}

const rowsHTML = rows => rows.map(([k, v, u, key]) =>
  `<tr${key ? ' class="key"' : ''}><td>${k}</td><td class="v">${v} ${u}</td></tr>`).join('');

let eq = null;   // Erdbeben-Ergebnis der Zuordnung
let skFix = NaN;

function calc() {
  const A = parseFloat($('alt').value) || 0;
  const z = Math.max(0, parseFloat($('z').value) || 0);
  const s = snow($('sz').value, A, $('tiefland').checked, skFix);
  $('snowOut').innerHTML = rowsHTML([
    ['Schneelastzone', esc($('sz').value), ''],
    ['Geländehöhe A', fmt(A, 0), 'm'],
    ['Mindestwert', fmt(s.min), 'kN/m²'],
    ['Charakteristischer Wert s<sub>k</sub>', fmt(s.sk), 'kN/m²', true],
    ...(s.sAd ? [['Außergewöhnlich s<sub>Ad</sub>', fmt(s.sAd), 'kN/m²']] : [])
  ]);
  $('snowF').textContent = s.f + (s.warn ? '\n' + s.warn : '');

  const w = wind($('wz').value, $('terrain').value, z, A);
  const zoneBad = $('terrain').value === 'inseln' && $('wz').value !== '4';
  $('windOut').innerHTML = rowsHTML([
    ['Windzone', $('wz').value, ''],
    ['Grundwert v<sub>b,0</sub>', fmt(w.vb0, 1), 'm/s'],
    ['Grundgeschwindigkeitsdruck q<sub>b</sub>', fmt(w.qb), 'kN/m²'],
    [`Böengeschwindigkeitsdruck q<sub>p</sub>(z = ${fmt(z, 1)} m)`, fmt(w.qp), 'kN/m²', true],
    ['Vereinfacht nach Tab. NA.B.3', w.simp != null ? fmt(w.simp) : 'nicht anwendbar', w.simp != null ? 'kN/m²' : '']
  ]);
  $('windF').textContent = w.f + (zoneBad ? '\nHinweis: Nordseeinseln liegen in Windzone 4.' : '');

  if (eq) {
    const zn = eq.zone, agR = ZONEN && ZONEN.agR ? ZONEN.agR[zn] : null;
    const keine = zn === '–' || zn === '';
    $('eqOut').innerHTML = rowsHTML([
      ['Erdbebenzone (DIN 4149)', keine ? 'keine Erdbebenzone' : 'Zone ' + esc(zn), '', true],
      ['Untergrundklasse', esc(eq.guk || '–'), ''],
      ['Bemessungswert Bodenbeschleunigung a<sub>gR</sub>', agR ? fmt(agR, 1) : '0', 'm/s²'],
      ['Erdbebennachweis', agR ? 'erforderlich' : 'nicht erforderlich', '']
    ]);
  } else {
    $('eqOut').innerHTML = rowsHTML([['Erdbebenzone', 'noch nicht ermittelt', '']]);
  }
  $('printdate').textContent = 'Erstellt am ' + new Date().toLocaleDateString('de-DE') + ' · ' + $('locText').textContent;
}
['alt', 'z', 'sz', 'wz', 'terrain', 'tiefland'].forEach(id => $(id).addEventListener('input', calc));

/* ---------- Zuordnung anwenden ---------- */
let lastLoc = null;
function applyZones(loc) {
  const notes = [];
  skFix = NaN; eq = null;
  if (!loc || !loc.land) { $('notes').innerHTML = '<li class="warn">Standort liegt nicht in Deutschland oder Bundesland nicht erkannt. Zonen manuell wählen.</li>'; calc(); return; }
  if (!ZONEN) { $('notes').innerHTML = '<li>Keine Zonentabelle geladen. Zonen manuell wählen.</li>'; calc(); return; }
  const LH = ZONEN.landHinweis || {};
  const note = (txt, cls = '', src = '') => notes.push(`<li class="${cls}">${txt}${src ? `<br><span class="src">${esc(src)}</span>` : ''}</li>`);

  const sn = lookup('schnee', loc);
  if (sn && sn.best) {
    const r = sn.best;
    const opt = [...$('sz').options].find(o => o.value === r.zone);
    $('sz').value = opt ? r.zone : (r.zone.startsWith('>') ? '>3' : '3a');
    $('tiefland').checked = !!r.tiefland;
    if (Number.isFinite(r.sk)) skFix = r.sk;
    note(`Schneelastzone <b>${esc(r.zone)}</b>${r.tiefland ? ' · Norddeutsches Tiefland' : ''}`, '', 'Quelle: ' + quelle(r, sn.score) + ' · ' + ZONEN.stand.schnee);
    if (r.hinweis) note(esc(r.hinweis), 'warn');
    sn.alts.forEach(a => note(`Gemeinde ist geteilt: ${esc(a.teil || (a.gem || []).join(', '))} → Zone ${esc(a.zone)}`, 'warn'));
    if (sn.score < 70 && sn.score >= 40) note('Nur auf Kreisebene zugeordnet – Gemeinde nicht in den Ausnahmen gefunden. Ausnahmelisten des Kreises prüfen.', 'warn');
  } else note('Schneelastzone nicht gefunden – manuell wählen.', 'warn');
  if (LH.schnee && LH.schnee[loc.land]) note(esc(LH.schnee[loc.land]), 'warn');

  const wi = lookup('wind', loc);
  if (wi && wi.best) {
    const r = wi.best;
    $('wz').value = r.zone;
    if (r.zone === '4' && /insel|borkum|helgoland|fehmarn|hiddensee/i.test((r.gem || []).join(' ') + ' ' + (loc.gem || ''))) $('terrain').value = 'inseln';
    else if (+r.zone >= 3 && $('terrain').value === 'binnen') note('Windzone 3/4: Profil „Küstennah“ prüfen.', 'warn');
    note(`Windzone <b>${esc(r.zone)}</b>`, '', 'Quelle: ' + quelle(r, wi.score) + ' · ' + ZONEN.stand.wind);
    if (r.hinweis) note(esc(r.hinweis), 'warn');
    wi.alts.forEach(a => note(`Alternative Zuordnung: ${esc((a.gem || []).join(', '))} → Windzone ${esc(a.zone)}`, 'warn'));
  } else note('Windzone nicht gefunden – manuell wählen.', 'warn');
  if (LH.wind && LH.wind[loc.land]) note(esc(LH.wind[loc.land]), 'warn');

  const eLH = (LH.erdbeben || {});
  const er = lookup('erdbeben', loc);
  if (er && er.best) {
    eq = er.best;
    $('eqHint').textContent = 'Quelle: ' + quelle(er.best, er.score) + ' · ' + ZONEN.stand.erdbeben + (er.best.hinweis ? ' · ' + er.best.hinweis : '');
  } else {
    eq = {zone: '–', guk: ''};
    $('eqHint').textContent = eLH[loc.land] || (['BY', 'RP', 'HE', 'TH', 'SN'].includes(loc.land) ? eLH._fehlt : eLH._ohne);
  }
  $('notes').innerHTML = notes.join('');
  calc();
}

function setTableState() {
  $('tableState').textContent = ZONEN
    ? `Zonentabelle: Schnee ${ZONEN.stand.schnee}, Wind ${ZONEN.stand.wind}, Erdbeben ${ZONEN.stand.erdbeben} (${ZONEN.schnee.length + ZONEN.wind.length + ZONEN.erdbeben.length} Regeln).`
    : 'Keine Zonentabelle geladen.';
  if (ZONEN) ['schnee', 'wind', 'erdbeben'].forEach(k => { $('stand-' + k).textContent = ZONEN.stand[k].replace(/^DIBt\s*/, ''); });
}
$('zfile').addEventListener('change', async e => {
  const f = e.target.files[0]; if (!f) return;
  try { ZONEN = JSON.parse(await f.text()); setTableState(); applyZones(lastLoc); }
  catch (err) { $('tableState').textContent = 'Datei konnte nicht gelesen werden: kein gültiges JSON.'; }
});

/* ---------- Karte, Suche, Höhe ----------
   Externe Dienste werden erst nach einer Nutzeraktion angesprochen:
   - Karte TopPlusOpen (BKG): nach „Karte laden“ oder der ersten Ortssuche
   - Ortssuche Nominatim (liefert den Gemeindeschlüssel) und Geländehöhe Open-Meteo:
     bei Ortssuche oder Klick auf die Karte */
const KARTE = 'TopPlusOpen (BKG)';
let map = null, marker = null;

function initMap() {
  if (map) return map;
  $('mapConsent').remove();
  map = L.map('map').setView([51.2, 10.4], 6);
  L.tileLayer('https://sgx.geodatenzentrum.de/wmts_topplus_open/tile/1.0.0/web/default/WEBMERCATOR/{z}/{y}/{x}.png',
    {maxZoom: 18, attribution: 'Kartendarstellung: © <a href="https://www.bkg.bund.de">BKG</a> (' + new Date().getFullYear()
      + ') <a href="https://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>, '
      + '<a href="https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_topplusopen.html">Datenquellen</a>'}).addTo(map);
  L.control.scale({imperial: false, position: 'bottomleft'}).addTo(map);
  map.on('click', e => setLocation(e.latlng.lat, e.latlng.lng));
  return map;
}
/* stopPropagation: der Klick auf die Schaltfläche darf nicht als Klick auf die neue Karte gelten. */
$('mapLoad').addEventListener('click', e => { e.stopPropagation(); initMap(); });
window.addEventListener('beforeprint', () => { if (map) map.invalidateSize({pan: false}); });
window.addEventListener('afterprint', () => { if (map) map.invalidateSize({pan: false}); });

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

/* Nominatim-Nutzungsbedingungen: höchstens 1 Anfrage pro Sekunde, gleiche Anfragen nicht wiederholen. */
const nomCache = new Map();
let nomNext = 0;
function nominatim(url) {
  if (!nomCache.has(url)) {
    const wait = Math.max(0, nomNext - Date.now());
    nomNext = Date.now() + wait + 1100;
    const p = new Promise(ok => setTimeout(ok, wait)).then(() => getJSON(url));
    p.catch(() => nomCache.delete(url));
    nomCache.set(url, p);
  }
  return nomCache.get(url);
}

/* Liefert {land, regbez, kf, kreis, gem, ags, stateName, countyName, quelle} oder null */
async function reverseGeocode(lat, lon) {
  const res = await nominatim(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=10&addressdetails=1&extratags=1&accept-language=de&lat=${lat.toFixed(5)}&lon=${lon.toFixed(5)}`);
  const a = res.address;
  if (!a) return null;
  const agsRaw = (res.extratags || {})['de:amtlicher_gemeindeschluessel'] || '';
  const gem = a.city || a.town || a.village || a.municipality || res.name || '';
  return {
    land: LAND[a.state] || (a.city === 'Berlin' ? 'BE' : a.city === 'Hamburg' ? 'HH' : null),
    regbez: a.state_district || '', kf: !a.county, kreis: a.county || gem, gem,
    ags: /^\d{8}$/.test(agsRaw) ? agsRaw : null, stateName: a.state || '', countyName: a.county || '', quelle: 'Nominatim'
  };
}

async function searchPlace(q) {
  const r = await nominatim(`https://nominatim.openstreetmap.org/search?format=jsonv2&countrycodes=de&limit=1&accept-language=de&q=${encodeURIComponent(q)}`);
  return r.length ? [+r[0].lat, +r[0].lon] : null;
}

async function setLocation(lat, lon) {
  initMap();
  if (marker) marker.setLatLng([lat, lon]); else marker = L.marker([lat, lon]).addTo(map);
  $('locText').textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)} · wird ermittelt …`;
  const [elev, rev] = await Promise.allSettled([
    getJSON(`https://api.open-meteo.com/v1/elevation?latitude=${lat.toFixed(5)}&longitude=${lon.toFixed(5)}`),
    reverseGeocode(lat, lon)
  ]);
  if (elev.status === 'fulfilled' && elev.value.elevation) $('alt').value = Math.round(elev.value.elevation[0]);
  const loc = rev.status === 'fulfilled' ? rev.value : null;
  if (loc) {
    $('locText').innerHTML = `<b>${esc(loc.gem || '–')}</b> · ${esc(loc.countyName || 'kreisfreie Stadt')} · ${esc(loc.stateName)}`
      + `<br><span style="color:var(--muted);font-family:var(--mono);font-size:.82rem">${lat.toFixed(5)}, ${lon.toFixed(5)} · A = ${$('alt').value} m ü. NN`
      + `${loc.ags ? ' · AGS ' + loc.ags : ''} · ${loc.quelle}</span>`;
  } else {
    $('locText').textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)} · Gemeinde nicht ermittelbar (Ortssuche nicht erreichbar) – Zonen manuell wählen`;
  }
  $('mapcap').textContent = `Lageplan: ${loc ? loc.gem + ', ' : ''}${lat.toFixed(5)} N, ${lon.toFixed(5)} O · Kartengrundlage ${KARTE}`;
  lastLoc = loc;
  applyZones(loc);
}
$('searchForm').addEventListener('submit', async e => {
  e.preventDefault();
  const q = $('q').value.trim(); if (!q) return;
  try {
    const ll = await searchPlace(q);
    if (!ll) { $('locText').textContent = 'Ort nicht gefunden.'; return; }
    initMap().setView(ll, 12); setLocation(ll[0], ll[1]);
  } catch (err) { $('locText').textContent = 'Ortssuche nicht erreichbar.'; }
});
$('printBtn').addEventListener('click', () => window.print());

$('bkgJahr').textContent = new Date().getFullYear();
setTableState();
calc();
