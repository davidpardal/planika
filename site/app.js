/* Planika: filtros, lista, calendario, mapa, favoritos, compartir y "añadir al calendario". */
(function () {
  'use strict';
  // Los datos llegan en dos partes: data/core.js (lo justo para filtrar, ordenar, calendario y mapa) y
  // data/d/<n>.js (descripción, enlaces e imagen, en bloques que se piden solo cuando hay que pintar esas tarjetas).
  var DATA = window.PLANES_CORE || { events: [], categories: [], provinces: [], sources: [], srcNames: [], chunk: 250, v: '' };
  // Idioma de la interfaz (i18n.js): tr(«texto en español», {n: 3}) devuelve la traducción con los huecos rellenos.
  var I18N = window.PLANIKA_I18N || { lang: 'es', locale: 'es-ES', t: function (s, v) { return v ? String(s).replace(/\{(\w+)\}/g, function (m, k) { return v[k] != null ? v[k] : m; }) : s; },
    dtf: function (o) { return new Intl.DateTimeFormat('es-ES', o); }, num: function (n) { return Number(n).toLocaleString('es-ES'); } };
  var tr = I18N.t, LOC = I18N.locale, dtf = I18N.dtf, num = I18N.num;
  var CATS = {};
  DATA.categories.forEach(function (c) { CATS[c.key] = c; });
  var PROV = {};
  DATA.provinces.forEach(function (p) { PROV[p.code] = p; });
  var CHUNK = DATA.chunk || 250;
  var BY_ID = {};
  var EVENTS = DATA.events.map(function (r, i) {
    var p = PROV[r[7]] || {}, c = DATA.categories[r[2]] || {};
    var e = { i: i, id: r[0], title: r[1], category: c.key || 'otros', subtype: r[3] || '', start: r[4], end: r[5], time: r[6] || '',
      province_code: r[7], province: p.name || '', ccaa: p.ccaa || '', city: r[8] || '', venue: r[9] || '',
      lat: r[10] == null ? null : r[10], lon: r[11] == null ? null : r[11], price: r[12] || '', free: !!(r[13] & 1), tk: !!(r[13] & 2), xm: !!(r[13] & 4), ft: !!(r[13] & 8),
      audience: r[14] || '', source: DATA.srcNames[r[15]] || '', sessions: r[16] || null, title_es: r[17] || '', tc: r[18] || '',
      description: '', url: '', tickets_url: '', image: '', address: '', _d: false };
    BY_ID[e.id] = e;
    return e;
  });
  var NCHUNKS = Math.ceil(EVENTS.length / CHUNK);
  var PAGE = 48;
  var LONG_DAYS = 45; // a partir de aquí un evento se considera "de larga duración" en el calendario
  // Centro aproximado de cada provincia (capital) para el mapa de cobertura
  var CENTROIDS = { '01': [42.85, -2.67], '02': [38.99, -1.86], '03': [38.35, -0.48], '04': [36.84, -2.46], '05': [40.66, -4.70], '06': [38.88, -6.97], '07': [39.57, 2.65], '08': [41.39, 2.17], '09': [42.34, -3.70], '10': [39.47, -6.37], '11': [36.53, -6.29], '12': [39.99, -0.04], '13': [38.99, -3.93], '14': [37.89, -4.78], '15': [43.36, -8.41], '16': [40.07, -2.14], '17': [41.98, 2.82], '18': [37.18, -3.60], '19': [40.63, -3.17], '20': [43.32, -1.98], '21': [37.26, -6.95], '22': [42.14, -0.41], '23': [37.78, -3.79], '24': [42.60, -5.57], '25': [41.62, 0.62], '26': [42.47, -2.45], '27': [43.01, -7.56], '28': [40.42, -3.70], '29': [36.72, -4.42], '30': [37.98, -1.13], '31': [42.82, -1.64], '32': [42.34, -7.86], '33': [43.36, -5.85], '34': [42.01, -4.53], '35': [28.12, -15.43], '36': [42.43, -8.64], '37': [40.97, -5.66], '38': [28.47, -16.25], '39': [43.46, -3.81], '40': [40.95, -4.12], '41': [37.39, -5.98], '42': [41.76, -2.47], '43': [41.12, 1.25], '44': [40.34, -1.11], '45': [39.86, -4.02], '46': [39.47, -0.38], '47': [41.65, -4.72], '48': [43.26, -2.93], '49': [41.50, -5.74], '50': [41.65, -0.89], '51': [35.89, -5.32], '52': [35.29, -2.94] };

  var $ = function (id) { return document.getElementById(id); };
  var state = { q: '', ccaa: '', prov: '', city: '', from: '', to: '', free: false, tickets: false, cats: {}, tod: '', aud: '', pmax: '',
                favs: false, geo: null, radius: 25, view: 'list', shown: PAGE, month: null, days: [], planOnly: false };
  // days: días sueltos elegidos en el calendario ("2026-12-05"…), ordenados. Si hay alguno, es el filtro de fechas
  // de toda la web (lista, mapa, enlace) en lugar de from/to.
  var favSet = loadFavs();

  // ---------- utilidades
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoDate(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function fromIso(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function addDays(s, n) { var d = fromIso(s); d.setDate(d.getDate() + n); return isoDate(d); }
  var TODAY = isoDate(new Date());
  var thisYear = TODAY.slice(0, 4);
  var fmtDay = dtf({ weekday: 'short', day: 'numeric', month: 'short' });
  var fmtShort = dtf({ day: 'numeric', month: 'short' });
  var fmtLong = dtf({ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  var fmtMonth = dtf({ month: 'long', year: 'numeric' });
  var fmtDayName = dtf({ weekday: 'long', day: 'numeric', month: 'long' });
  function fmtD(s) { return fmtDay.format(fromIso(s)) + (s.slice(0, 4) !== thisYear ? ' ' + s.slice(0, 4) : ''); }
  // updated_at va en hora de Madrid ("2026-11-24T06:50"): «Actualizado hoy a las 6:50», «ayer a las…», «el lun 22 nov a las…»
  function updatedText(s) {
    var m = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2})/.exec(s || '');
    if (!m) return tr('Actualizado');
    var h = (+m[2]) + ':' + m[3];
    if (m[1] === TODAY) return tr('Actualizado hoy a las {h}', { h: h });
    if (m[1] === addDays(TODAY, -1)) return tr('Actualizado ayer a las {h}', { h: h });
    return tr('Actualizado el {d} a las {h}', { d: fmtD(m[1]), h: h });
  }
  function spanDays(e) { return Math.round((fromIso(e.end) - fromIso(e.start)) / 864e5); }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
  function slug(s) { return norm(s).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  // tc: título limpio (sin «Entradas…», fechas entre paréntesis ni MAYÚSCULAS); e.title queda intacto para evFile()
  function title(e) { return e.tc || e.title_es || e.title; }
  function safeUrl(u) { return /^https?:\/\//i.test(u || '') ? u : ''; }
  // Página propia del plan (site/e/), con el mismo nombre de archivo que genera planes/static.py
  function evFile(e) { var s = slug(e.title).slice(0, 60).replace(/^-|-$/g, ''); return 'e/' + (s ? s + '-' : '') + e.id + '.html'; }

  // ---------- detalles por bloques
  var chunkState = {}, allRequested = false, rerenderT = null;
  function applyChunk(v, n, rows) {
    if (v !== DATA.v) { staleReload(); return; }
    var base = n * CHUNK;
    for (var k = 0; k < rows.length; k++) {
      var e = EVENTS[base + k], r = rows[k]; if (!e) break;
      e.description = r[0] || ''; e.url = safeUrl(r[1]); e.tickets_url = safeUrl(r[2]); e.image = safeUrl(r[3]); e.address = r[4] || ''; e._d = true;
    }
    chunkState[n] = 'ok';
    hydrate(n);
    if (state.q) { clearTimeout(rerenderT); rerenderT = setTimeout(rerender, 150); } // la búsqueda también mira la descripción
  }
  // La web se actualiza a diario: si esta pestaña tiene datos de ayer y el bloque es de hoy, se recarga una vez.
  function staleReload() {
    try { if (sessionStorage.getItem('planika_reload') === DATA.v) return; sessionStorage.setItem('planika_reload', DATA.v); } catch (e) { return; }
    location.reload();
  }
  function loadChunk(n) {
    if (chunkState[n] || n < 0 || n >= NCHUNKS) return;
    chunkState[n] = 'loading';
    var s = document.createElement('script'); s.async = true; s.src = 'data/d/' + n + '.js?v=' + encodeURIComponent(DATA.v);
    s.onerror = function () { delete chunkState[n]; s.remove(); };
    document.head.appendChild(s);
  }
  function need(list) { for (var k = 0; k < list.length; k++) if (!list[k]._d) loadChunk(Math.floor(list[k].i / CHUNK)); }
  function loadAll() { if (allRequested) return; allRequested = true; for (var n = 0; n < NCHUNKS; n++) loadChunk(n); }
  // Sustituye las tarjetas "ligeras" ya pintadas por las completas cuando llega su bloque
  function hydrate(n) {
    document.querySelectorAll('article.card[data-c="' + n + '"]').forEach(function (el) {
      var e = BY_ID[el.dataset.id]; if (!e) return;
      var t = document.createElement('template'); t.innerHTML = card(e, { i: +el.dataset.pop, noOngoing: el.dataset.no === '1' });
      el.replaceWith(t.content.firstChild);
    });
  }
  function nextSession(e) {
    var from = state.from && state.from > TODAY ? state.from : TODAY;
    if (!e.sessions) return e.start;
    if (state.days.length) { var sd = firstSelDay(e); if (sd) return sd; }
    for (var i = 0; i < e.sessions.length; i++) if (e.sessions[i] >= from) return e.sessions[i];
    return e.sessions[e.sessions.length - 1];
  }
  function isPermanent(e) { return e.subtype === 'Permanente'; }
  function whenText(e) {
    if (isPermanent(e)) return tr('Visita permanente');
    if (e.sessions) {
      var n = nextSession(e); var rest = e.sessions.filter(function (d) { return d > n; }).length;
      return fmtD(n) + (e.time ? ' · ' + e.time : '') + (rest ? ' (' + tr('+{n} fechas', { n: rest }) + ')' : '');
    }
    if (e.end !== e.start && e.start < TODAY) return tr('Hasta el {d}', { d: fmtD(e.end) }) + (e.time ? ' · ' + e.time : '');
    var s = fmtD(e.start);
    if (e.end && e.end !== e.start) return s + ' – ' + fmtD(e.end);
    return e.time ? s + ' · ' + e.time : s;
  }
  function priceNum(e) {
    if (e.free) return 0;
    var m = String(e.price || '').replace(',', '.').match(/\d+(\.\d+)?/g);
    if (!m) return null;
    return Math.min.apply(null, m.map(Number));
  }
  function dist(e) {
    if (!state.geo || e.lat == null || e.lon == null) return null;
    var R = 6371, dLat = (e.lat - state.geo.lat) * Math.PI / 180, dLon = (e.lon - state.geo.lon) * Math.PI / 180;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(state.geo.lat * Math.PI / 180) * Math.cos(e.lat * Math.PI / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }
  function toast(msg) {
    var t = $('toast'), dlg = document.querySelector('dialog[open]');
    (dlg || document.body).appendChild(t);  // con una ventana abierta, el aviso va dentro para que se vea encima
    t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(function () { t.hidden = true; }, 2600);
  }
  function loadFavs() { try { return new Set(JSON.parse(localStorage.getItem('planika_favs') || '[]')); } catch (e) { return new Set(); } }
  function saveFavs() { try { localStorage.setItem('planika_favs', JSON.stringify(Array.from(favSet))); } catch (e) { /* sin almacenamiento */ } $('favCount').textContent = favSet.size ? favSet.size : ''; }

  // ---------- estado en la URL (enlaces compartibles con filtros)
  function readURL() {
    var p = new URLSearchParams(location.search);
    state.q = p.get('q') || ''; state.ccaa = p.get('ccaa') || ''; state.prov = p.get('prov') || ''; state.city = p.get('city') || '';
    state.from = p.get('from') || ''; state.to = p.get('to') || ''; state.free = p.get('free') === '1'; state.tickets = p.get('tickets') === '1';
    state.tod = p.get('tod') || ''; state.aud = p.get('aud') || ''; state.pmax = p.get('pmax') || ''; state.favs = p.get('favs') === '1';
    (p.get('cat') || '').split(',').filter(Boolean).forEach(function (c) { state.cats[c] = true; });
    state.days = (p.get('dias') || '').split(',').filter(function (d) { return /^\d{4}-\d{2}-\d{2}$/.test(d) && d >= TODAY; }).sort()
      .filter(function (d, i, a) { return a.indexOf(d) === i; });
    if (state.days.length) { state.from = ''; state.to = ''; }
    if (p.get('view')) state.view = p.get('view');
    return p.get('e');
  }
  function writeURL() {
    var p = new URLSearchParams();
    if (state.q) p.set('q', state.q); if (state.ccaa) p.set('ccaa', state.ccaa); if (state.prov) p.set('prov', state.prov); if (state.city) p.set('city', state.city);
    if (state.from) p.set('from', state.from); if (state.to) p.set('to', state.to); if (state.free) p.set('free', '1'); if (state.tickets) p.set('tickets', '1');
    if (state.tod) p.set('tod', state.tod); if (state.aud) p.set('aud', state.aud); if (state.pmax) p.set('pmax', state.pmax); if (state.favs) p.set('favs', '1');
    var cats = Object.keys(state.cats).filter(function (k) { return state.cats[k]; }); if (cats.length) p.set('cat', cats.join(','));
    if (state.days.length) p.set('dias', state.days.join(','));
    if (state.view !== 'list') p.set('view', state.view);
    var qs = p.toString();
    try { history.replaceState(null, '', location.pathname + (qs ? '?' + qs : '')); } catch (e) { /* file:// */ }
  }

  // ---------- filtros
  var provCountAll = null;
  function provCounts() {
    if (!provCountAll) { provCountAll = {}; EVENTS.forEach(function (e) { if (e.province_code) provCountAll[e.province_code] = (provCountAll[e.province_code] || 0) + 1; }); }
    return provCountAll;
  }
  function populate() {
    var ccaas = {};
    EVENTS.forEach(function (e) { if (e.ccaa) ccaas[e.ccaa] = (ccaas[e.ccaa] || 0) + 1; });
    var selC = $('ccaa');
    Object.keys(ccaas).sort(function (a, b) { return a.localeCompare(b, 'es'); }).forEach(function (c) {
      var o = document.createElement('option'); o.value = c; o.textContent = c + ' (' + ccaas[c] + ')'; selC.appendChild(o);
    });
    selC.value = state.ccaa;
    fillProvinces();
    fillWhere(ccaas);
    fillCities();
    var nCat = {}; var nFree = 0;
    EVENTS.forEach(function (e) {
      nCat[e.category] = (nCat[e.category] || 0) + 1; if (e.xm && e.category !== 'navidad') nCat.navidad = (nCat.navidad || 0) + 1;
      if (e.free && !isPermanent(e)) nFree++;
    });
    $('what').querySelectorAll('a.chip').forEach(function (a) {
      var n = a.dataset.free ? nFree : (nCat[a.dataset.cat] || 0);
      if (!n && a.dataset.cat) { a.hidden = true; return; }  // p. ej. Navidad fuera de temporada
      a.insertAdjacentHTML('beforeend', ' <small>' + num(n) + '</small>');
    });
    var chips = $('cats');
    DATA.categories.forEach(function (c) {
      var n = EVENTS.filter(function (e) { return e.category === c.key || (c.key === 'navidad' && e.xm); }).length;
      if (!n) return;
      var b = document.createElement('button'); b.type = 'button'; b.className = 'chip' + (state.cats[c.key] ? ' on' : ''); b.dataset.cat = c.key;
      b.innerHTML = c.icon + ' ' + esc(tr(c.name)) + ' <small>' + n + '</small>';
      b.addEventListener('click', function () { state.cats[c.key] = !state.cats[c.key]; b.classList.toggle('on', !!state.cats[c.key]); refresh(); });
      chips.appendChild(b);
    });
    $('meta').textContent = updatedText(DATA.updated_at) + ' · ' + tr('{n} planes del {a} al {b}', { n: num(EVENTS.length), a: fmtDay.format(fromIso(DATA.from)), b: fmtDay.format(fromIso(DATA.to)) });
    var pc = provCounts();
    $('seoLinks').innerHTML = DATA.provinces.filter(function (p) { return pc[p.code]; }).sort(function (a, b) { return a.name.localeCompare(b.name, 'es'); })
      .map(function (p) { return '<a href="p/' + slug(p.name) + '.html">' + esc(p.name) + '</a>'; }).join(' · ') + '<br>' +
      DATA.categories.map(function (c) { return '<a href="t/' + c.key + '.html">' + c.icon + ' ' + esc(tr(c.name)) + '</a>'; }).join(' · ');
    $('q').value = state.q; $('from').value = state.from; $('to').value = state.to; $('free').checked = state.free; $('tickets').checked = state.tickets;
    $('tod').value = state.tod; $('aud').value = state.aud; $('pmax').value = state.pmax; $('favs').checked = state.favs; $('radius').value = String(state.radius);
    saveFavs();
  }
  function fillProvinces() {
    var pc = provCounts(); var sel = $('prov'); var cur = state.prov;
    sel.innerHTML = '<option value="">' + tr('Todas') + '</option>';
    DATA.provinces.filter(function (p) { return (!state.ccaa || p.ccaa === state.ccaa) && pc[p.code]; })
      .sort(function (a, b) { return a.name.localeCompare(b.name, 'es'); })
      .forEach(function (p) { var o = document.createElement('option'); o.value = p.code; o.textContent = p.name + ' (' + pc[p.code] + ')'; sel.appendChild(o); });
    sel.value = cur; if (sel.value !== cur) { state.prov = ''; }
  }
  // "Dónde": se escribe y se sugieren los lugares con planes que empiezan por lo escrito (comunidades, provincias y
  // localidades), sin distinguir mayúsculas ni tildes. También vale el otro nombre oficial (Gasteiz, Iruña, Alacant…)
  // o el nombre sin artículo ni «Comunidad de» (Coruña, Rioja, Valenciana…), pero esos van detrás.
  var PLACES = [];
  var STRIP = /^(a|o|el|la|las|los|les|l'|comunidad foral de|comunidad de|comunitat|region de|principado de|illes|islas|ciudad autonoma de|ciudad de) +/;
  // Otros nombres de uso corriente (castellano o lengua cooficial) de las provincias y comunidades.
  var ALIAS = { 'alava': ['araba'], 'alicante': ['alacant'], 'illes balears': ['baleares', 'islas baleares'], 'castellon': ['castello'],
    'a coruna': ['la coruna'], 'girona': ['gerona'], 'gipuzkoa': ['guipuzcoa'], 'lleida': ['lerida'], 'navarra': ['nafarroa'],
    'ourense': ['orense'], 'bizkaia': ['vizcaya'], 'pais vasco': ['euskadi'], 'cataluna': ['catalunya'],
    'comunitat valenciana': ['comunidad valenciana'], 'galicia': ['galiza'], 'donostia / san sebastian': ['san sebastian'] };
  function placeKeys(name) {
    var n = norm(name), keys = [n].concat(ALIAS[n] || []);
    n.split(/\s*[\/\-]\s*/).slice(1).forEach(function (k) { if (k) keys.push(k); });
    var b = n.replace(STRIP, ''); if (b !== n) keys.push(b);
    return keys;
  }
  function fillWhere(ccaas) {
    var pc = provCounts(); var list = [];
    Object.keys(ccaas).forEach(function (c) {
      var provs = DATA.provinces.filter(function (p) { return p.ccaa === c && pc[p.code]; });
      if (provs.length > 1) list.push({ t: 'c', v: c, name: c, kind: tr('Comunidad'), n: ccaas[c] });
    });
    DATA.provinces.forEach(function (p) { if (pc[p.code]) list.push({ t: 'p', v: p.code, name: p.name, kind: tr('Provincia'), n: pc[p.code] }); });
    var cities = {};
    EVENTS.forEach(function (e) {
      if (!e.city || !e.province_code) return;
      var k = e.province_code + '|' + norm(e.city);
      var c = cities[k] || (cities[k] = { n: 0, names: {}, prov: e.province_code });
      c.n++; c.names[e.city] = (c.names[e.city] || 0) + 1;
    });
    Object.keys(cities).forEach(function (k) {
      var c = cities[k];
      var name = Object.keys(c.names).sort(function (a, b) { return c.names[b] - c.names[a]; })[0];
      list.push({ t: 'l', v: name, prov: c.prov, name: name, kind: tr('en {x}', { x: (PROV[c.prov] || {}).name || '' }), n: c.n });
    });
    list.forEach(function (p) { p.keys = placeKeys(p.name); });
    PLACES = list.sort(function (a, b) { return b.n - a.n || a.name.localeCompare(b.name, 'es'); });
    syncWhere();
  }
  function matchPlaces(text) {
    var q = norm(text).trim();
    if (!q) return null;
    var exact = [], first = [], other = [];
    PLACES.forEach(function (p) {
      if (p.keys[0] === q) exact.push(p);
      else if (p.keys[0].indexOf(q) === 0) first.push(p);
      else if (p.keys.some(function (k, i) { return i && k.indexOf(q) === 0; })) other.push(p);
    });
    return exact.concat(first, other);  // dentro de cada grupo, primero los que tienen más planes
  }
  function placeLabel() {
    if (state.city) return state.city;
    if (state.prov) return (PROV[state.prov] || {}).name || '';
    return state.ccaa || '';
  }
  function syncWhere() { $('where').value = placeLabel(); $('whereClear').hidden = !$('where').value; }
  var SUGG = [], ACTIVE = -1;
  function boldPrefix(name, text) {
    var q = norm(text).trim(), n = norm(name);
    return n.indexOf(q) === 0 && q ? '<b>' + esc(name.slice(0, q.length)) + '</b>' + esc(name.slice(q.length)) : esc(name);
  }
  function showPlaces(text) {
    var ul = $('whereList'), m = matchPlaces(text);
    // Sin texto: «Toda España» y los lugares con más planes.
    SUGG = m === null ? [{ t: 'all', name: tr('Toda España'), kind: tr('Sin filtro de lugar'), n: EVENTS.length }]
      .concat(PLACES.filter(function (p) { return p.t !== 'c'; }).slice(0, 8)) : m;
    ACTIVE = m && m.length ? 0 : -1;
    ul.innerHTML = SUGG.length ? SUGG.map(function (p, i) {
      return '<li role="option" id="wh' + i + '" data-i="' + i + '" aria-selected="' + (i === ACTIVE) + '">' +
        '<span>' + boldPrefix(p.name, text) + '</span><span class="k">' + esc(p.kind) + ' · ' + num(p.n) + '</span></li>';
    }).join('') : '<li class="none">' + tr('Ningún lugar con planes empieza por «{x}»', { x: esc(text.trim()) }) + '</li>';
    ul.hidden = false; $('where').setAttribute('aria-expanded', 'true');
    $('where').setAttribute('aria-activedescendant', ACTIVE >= 0 ? 'wh' + ACTIVE : '');
    ul.scrollTop = 0;
  }
  function closePlaces() {
    $('whereList').hidden = true; $('where').setAttribute('aria-expanded', 'false'); $('where').removeAttribute('aria-activedescendant');
    SUGG = []; ACTIVE = -1;
  }
  function moveActive(d) {
    if (!SUGG.length) return;
    ACTIVE = (ACTIVE + d + SUGG.length) % SUGG.length;
    $('whereList').querySelectorAll('li[role="option"]').forEach(function (li, i) { li.setAttribute('aria-selected', i === ACTIVE ? 'true' : 'false'); });
    var li = $('wh' + ACTIVE); if (li) li.scrollIntoView({ block: 'nearest' });
    $('where').setAttribute('aria-activedescendant', 'wh' + ACTIVE);
  }
  function pickPlace(p) {
    state.ccaa = ''; state.prov = ''; state.city = '';
    if (p && p.t === 'c') state.ccaa = p.v;
    else if (p && p.t === 'p') state.prov = p.v;
    else if (p && p.t === 'l') { state.prov = p.prov; state.city = p.v; }
    $('ccaa').value = state.ccaa; fillProvinces(); $('prov').value = state.prov;
    CITY_KEY = norm(state.city); fillCities(); syncWhere(); closePlaces(); refresh();
  }
  // "Ciudad": aparece al elegir provincia o comunidad, con las localidades que tienen planes allí.
  var CITY_KEY = '';
  function fillCities() {
    var sel = $('city'); var counts = {}; var names = {};
    sel.innerHTML = '<option value="">' + tr('Todas') + '</option>';
    if (state.prov || state.ccaa) {
      EVENTS.forEach(function (e) {
        if (!e.city || (state.prov && e.province_code !== state.prov) || (state.ccaa && e.ccaa !== state.ccaa)) return;
        var k = norm(e.city); counts[k] = (counts[k] || 0) + 1;
        names[k] = names[k] || {}; names[k][e.city] = (names[k][e.city] || 0) + 1;
      });
    }
    var keys = Object.keys(counts).map(function (k) {
      var best = Object.keys(names[k]).sort(function (a, b) { return names[k][b] - names[k][a]; })[0];
      return { key: k, name: best, n: counts[k] };
    }).sort(function (a, b) { return a.name.localeCompare(b.name, 'es'); });
    keys.forEach(function (c) { var o = document.createElement('option'); o.value = c.name; o.textContent = c.name + ' (' + num(c.n) + ')'; sel.appendChild(o); });
    $('cityField').hidden = keys.length < 2 || !!state.city;  // con localidad elegida, ya se ve en «Dónde»
    var cur = keys.filter(function (c) { return c.key === norm(state.city); })[0];
    if (!cur) { state.city = ''; CITY_KEY = ''; sel.value = ''; } else { state.city = cur.name; CITY_KEY = cur.key; sel.value = cur.name; }
  }
  var WHAT_CATS = {};
  // Filtros de "Búsqueda avanzada" activos (para el contador y para abrirla si llegan en el enlace).
  function advCount() {
    var quickOn = !!$('quick').querySelector('button.on');
    var extraCats = Object.keys(state.cats).filter(function (k) { return state.cats[k] && !WHAT_CATS[k]; }).length;
    return (!quickOn && (state.from || state.to) ? 1 : 0) + (state.tickets ? 1 : 0) + (state.tod ? 1 : 0) + (state.aud ? 1 : 0) +
      (state.pmax ? 1 : 0) + (state.geo ? 1 : 0) + (state.favs ? 1 : 0) + extraCats;
  }
  function anyFilter() {
    var quickAll = $('quick').querySelector('button.on[data-range="all"]');
    return !!(state.q || state.ccaa || state.prov || state.city || state.free || anyCat() || advCount() || state.days.length || state.planOnly || (!quickAll && (state.from || state.to)));
  }
  function syncUI() {
    $('what').querySelectorAll('a.chip').forEach(function (a) {
      a.classList.toggle('on', a.dataset.free ? state.free : !!state.cats[a.dataset.cat]);
      a.setAttribute('aria-pressed', a.classList.contains('on') ? 'true' : 'false');
    });
    $('cats').querySelectorAll('.chip').forEach(function (b) { b.classList.toggle('on', !!state.cats[b.dataset.cat]); });
    var n = advCount(); $('advN').hidden = !n; $('advN').textContent = n;
    $('clearAll').hidden = !anyFilter();
  }
  // Número de planes bien visible y, debajo, los filtros activos en palabras (en el móvil el panel queda arriba).
  function setCount(n, small, extra) {
    $('count').innerHTML = '<strong>' + num(n) + '</strong> ' + tr(n === 1 ? 'plan' : 'planes') +
      (small ? ' <small>' + esc(small) + '</small>' : '');
    var ctx = filterSummary(); if (extra) ctx = ctx ? ctx + ' · ' + extra : extra;
    $('countCtx').textContent = ctx;
  }
  function filterSummary() {
    var parts = [];
    if (state.q) parts.push('«' + state.q + '»');
    var catNames = {}; DATA.categories.forEach(function (c) { catNames[c.key] = tr(c.name); });
    var cats = Object.keys(state.cats).filter(function (k) { return state.cats[k]; }).map(function (k) { return catNames[k] || k; });
    if (state.free) parts.push(tr('Gratis'));
    parts = parts.concat(cats);
    var ALL = tr('toda España'), where = ALL;
    if (state.prov) { var pv = DATA.provinces.filter(function (p) { return p.code === state.prov; })[0]; if (pv) where = pv.name; }
    if (state.city) where = state.city + (where !== ALL && where !== state.city ? ' (' + where + ')' : '');
    else if (state.ccaa) where = state.ccaa;
    parts.push(tr(parts.length ? 'en {x}' : 'En {x}', { x: where }));
    var q = $('quick').querySelector('button.on');
    var labels = { today: tr('hoy'), weekend: tr('este fin de semana'), '7': tr('en los próximos 7 días'), '30': tr('en los próximos 30 días') };
    if (state.days.length) parts.push(daysLabel(4));
    else if (q && labels[q.dataset.range]) parts.push(labels[q.dataset.range]);
    else if (!q && (state.from || state.to)) {
      parts.push((state.from ? tr('del {d}', { d: fmtDay.format(fromIso(state.from)) }) : tr('desde hoy')) + (state.to ? ' ' + tr('al {d}', { d: fmtDay.format(fromIso(state.to)) }) : ''));
    }
    var tod = { manana: 'por la mañana', tarde: 'por la tarde', noche: 'por la noche' }[state.tod]; if (tod) parts.push(tr(tod));
    if (state.aud === 'familiar') parts.push(tr('infantil y familiar')); else if (state.aud === 'adultos') parts.push(tr('para adultos'));
    if (state.pmax) parts.push(tr('hasta {n} €', { n: state.pmax }));
    if (state.tickets) parts.push(tr('con venta de entradas'));
    if (state.geo) parts.push(tr('a menos de {n} km', { n: state.radius }));
    if (state.favs) parts.push(tr('solo favoritos'));
    if (state.planOnly) parts.push(tr('solo tu plan'));
    return parts.join(' · ');
  }
  function anyCat() { for (var k in state.cats) if (state.cats[k]) return true; return false; }
  function onDay(e, d) {
    if (isPermanent(e)) return false;
    return e.sessions ? e.sessions.indexOf(d) >= 0 : (e.start <= d && e.end >= d);
  }
  // Primer día elegido en el calendario en que se puede ir al plan ('' si ninguno)
  function firstSelDay(e) {
    for (var i = 0; i < state.days.length; i++) if (onDay(e, state.days[i])) return state.days[i];
    return '';
  }
  // «sáb 5 dic, mar 8 dic y 2 más»
  function daysLabel(max) {
    var d = state.days, shown = d.slice(0, max).map(function (x) { return fmtD(x).replace(',', ''); });
    return shown.join(', ') + (d.length > max ? ' ' + tr('y {n} más', { n: d.length - max }) : '');
  }
  function inDates(e) {
    // Sin un día concreto: se pueden visitar dentro de cualquier filtro de fechas.
    if (isPermanent(e)) return true;
    if (state.days.length) return !!firstSelDay(e);
    if (!state.from && !state.to) return true;
    if (e.sessions) return e.sessions.some(function (d) { return (!state.from || d >= state.from) && (!state.to || d <= state.to); });
    if (state.from && e.end < state.from) return false;
    if (state.to && e.start > state.to) return false;
    return true;
  }
  function matches(e, ignoreDates) {
    if (state.ccaa && e.ccaa !== state.ccaa) return false;
    if (state.prov && e.province_code !== state.prov) return false;
    if (state.city && norm(e.city) !== CITY_KEY) return false;
    if (state.free && !e.free) return false;
    if (state.tickets && !e.tk) return false;
    if (state.favs && !favSet.has(e.id)) return false;
    if (state.planOnly && !inPlan(e.id)) return false;
    if (anyCat() && !state.cats[e.category] && !(state.cats.navidad && e.xm)) return false;
    if (state.tod) {
      if (!e.time) return false;
      var h = +e.time.slice(0, 2);
      if (state.tod === 'manana' && h >= 14) return false;
      if (state.tod === 'tarde' && (h < 14 || h >= 20)) return false;
      if (state.tod === 'noche' && h < 20) return false;
    }
    if (state.aud === 'familiar' && e.category !== 'infantil' && !/nin|infan|famil|haur|nens/.test(norm(e.audience || ''))) return false;
    if (state.aud === 'adultos' && e.category === 'infantil') return false;
    if (state.pmax !== '') { var pn = priceNum(e); if (pn === null || pn > +state.pmax) return false; }
    if (state.geo) { var d = dist(e); if (d === null || d > state.radius) return false; }
    if (!ignoreDates && !inDates(e)) return false;
    if (state.q) {
      var hay = norm(e.title + ' ' + (e.title_es || '') + ' ' + e.venue + ' ' + e.city + ' ' + e.province + ' ' + e.subtype + ' ' + e.description);
      var terms = norm(state.q).split(/\s+/).filter(Boolean);
      for (var i = 0; i < terms.length; i++) if (hay.indexOf(terms[i]) < 0) return false;
    }
    return true;
  }
  function filtered(ignoreDates) { return EVENTS.filter(function (e) { return matches(e, ignoreDates); }); }
  function sortKey(e) {
    if (isPermanent(e)) return '9999-12-31|99|' + e.title;
    var from = state.from && state.from > TODAY ? state.from : TODAY;
    var s = state.days.length ? (firstSelDay(e) || nextSession(e)) : nextSession(e);
    if (state.days.length) from = s;
    return (s > from ? s : from) + '|' + pad(Math.min(99, e.sessions ? 0 : spanDays(e))) + '|' + (e.time || '99');
  }
  function sorted(list) {
    if (state.geo) return list.slice().sort(function (a, b) { return dist(a) - dist(b); });
    var out = list.map(function (e) { return [sortKey(e), e]; }).sort(function (a, b) { return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0; }).map(function (x) { return x[1]; });
    // Destacados (pagados por el organizador): arriba de la lista que encajan con los filtros, como mucho 3, con su etiqueta
    var top = out.filter(function (e) { return e.ft; }).slice(0, 3);
    return top.length ? top.concat(out.filter(function (e) { return top.indexOf(e) < 0; })) : out;
  }

  // ---------- tarjetas
  // Color pop de la tarjeta (amarillo, rosa, turquesa, lila): rota por posición en la lista.
  function popOf(id) { var h = 0, s = String(id); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h % 4; }
  function card(e, opts) {
    opts = opts || {};
    var pop = opts.i != null ? opts.i % 4 : popOf(e.id);
    var c = CATS[e.category] || { icon: '✨', name: 'Otros planes' };
    var ongoing = !e.sessions && !isPermanent(e) && e.start < TODAY && e.end >= TODAY;
    var permBadge = isPermanent(e) ? '<span class="badge">' + tr('Permanente') + '</span>' : '';
    var img = e.image ? '<img src="' + esc(e.image) + '" alt="" loading="lazy" onerror="this.remove()">' : '';
    var where = [e.venue, e.city, e.province && e.province !== e.city ? e.province : ''].filter(Boolean).join(' · ');
    var price = e.free ? '<span class="badge free">' + tr('Gratis') + '</span>' : (e.price ? '<span class="badge">' + esc(e.price) + '</span>' : '');
    var tickets = e.tickets_url ? '<a class="btn primary" href="' + esc(e.tickets_url) + '" target="_blank" rel="noopener">🎫 ' + tr('Entradas') + '</a>' : '';
    var info = e.url && e.url !== e.tickets_url ? '<a class="btn" href="' + esc(e.url) + '" target="_blank" rel="noopener">' + tr('Más info') + ' ↗</a>' : '';
    var d = dist(e);
    var sess = '';
    if (e.sessions) {
      var up = e.sessions.filter(function (x) { return x >= TODAY; });
      sess = '<div class="sessions">' + tr('Fechas:') + ' ' + up.slice(0, 6).map(function (x) { return fmtShort.format(fromIso(x)); }).join(', ') + (up.length > 6 ? ' ' + tr('y {n} más', { n: up.length - 6 }) : '') + '</div>';
    }
    var fav = '<button type="button" class="fav corner' + (favSet.has(e.id) ? ' on' : '') + '" data-fav="' + e.id + '" title="' + tr('Guardar en favoritos') + '" aria-label="' + tr('Guardar en favoritos') + '">' + (favSet.has(e.id) ? '★' : '☆') + '</button>';
    return '<article class="card pop' + pop + '" data-id="' + e.id + '" data-c="' + Math.floor(e.i / CHUNK) + '" data-pop="' + pop + '"' + (opts.noOngoing ? ' data-no="1"' : '') + '>' + fav + img + '<div class="body">' +
      '<div class="badges">' + (e.ft ? '<span class="badge featured">⭐ ' + tr('Destacado') + '</span>' : '') + '<span class="badge">' + c.icon + ' ' + esc(tr(c.name)) + '</span>' + price + permBadge + (ongoing && !opts.noOngoing ? '<span class="badge ongoing">' + tr('En curso') + '</span>' : '') + (d !== null ? '<span class="badge dist">' + tr('a {n} km', { n: d < 10 ? d.toFixed(1) : Math.round(d) }) + '</span>' : '') + '</div>' +
      // El título lleva a la ficha del plan en Planika (enlace rastreable); la web oficial sigue en "Entradas" y "Más info".
      '<h3><a href="' + esc(evFile(e)) + '">' + esc(title(e)) + '</a></h3>' +
      (e.title_es ? '<div class="where">' + esc(e.title) + '</div>' : '') +
      '<div class="when">📅 ' + esc(whenText(e)) + '</div>' + sess +
      (where ? '<div class="where">📍 ' + esc(where) + '</div>' : '') +
      (e.description ? '<p class="desc">' + esc(e.description) + '</p>' : '') +
      '<div class="actions">' + tickets + info + '<button type="button" class="btn addcal" data-id="' + e.id + '">＋ ' + tr('Calendario') + '</button>' +
      '<button type="button" class="btn share" data-share="' + e.id + '" title="' + tr('Compartir este plan') + '">↗ ' + tr('Compartir') + '</button>' + planBtn(e.id) + '</div>' +
      ((e.source || (e.subtype && !isPermanent(e))) ? '<div class="src">' + (e.source ? tr('Fuente:') + ' ' + esc(e.source) : '') + (e.subtype && !isPermanent(e) ? (e.source ? ' · ' : '') + esc(e.subtype) : '') + '</div>' : '') +
      '</div></article>';
  }
  function renderList() {
    var list = sorted(filtered());
    var el = $('list');
    setCount(list.length, list.length !== EVENTS.length ? tr('de {n}', { n: num(EVENTS.length) }) : '', '');
    if (!list.length) { el.innerHTML = '<div class="empty">' + tr('No hay planes con esos filtros. Prueba a ampliar las fechas o quitar algún filtro.') + '</div>'; $('more').hidden = true; return; }
    var page = list.slice(0, state.shown);
    need(page);
    el.innerHTML = page.map(function (e, i) { return card(e, { i: i }); }).join('');
    $('more').hidden = state.shown >= list.length;
    $('more').textContent = tr('Mostrar más ({a} de {b} restantes)', { a: Math.min(PAGE, list.length - state.shown), b: list.length - state.shown });
  }

  // ---------- calendario
  function renderCalendar() {
    var m = state.month || fromIso(TODAY); m = new Date(m.getFullYear(), m.getMonth(), 1); state.month = m;
    $('monthTitle').textContent = cap(fmtMonth.format(m));
    var list = filtered(true);
    var starts = {}, ongoing = {};
    var first = isoDate(m), last = isoDate(new Date(m.getFullYear(), m.getMonth() + 1, 0));
    list.forEach(function (e) {
      if (isPermanent(e)) return;
      if (e.sessions) { e.sessions.forEach(function (d) { if (d >= first && d <= last) starts[d] = (starts[d] || 0) + 1; }); return; }
      if (e.end < first || e.start > last) return;
      if (e.start >= first) starts[e.start] = (starts[e.start] || 0) + 1;
      if (e.end !== e.start && spanDays(e) <= LONG_DAYS) {
        var d = e.start > first ? addDays(e.start, 1) : first;
        var stop = e.end < last ? e.end : last;
        while (d <= stop) { ongoing[d] = (ongoing[d] || 0) + 1; d = addDays(d, 1); }
      }
    });
    var html = ['L', 'M', 'X', 'J', 'V', 'S', 'D'].map(function (d) { return '<div class="dow">' + d + '</div>'; }).join('');
    var dow = (m.getDay() + 6) % 7;
    var cur = new Date(m); cur.setDate(cur.getDate() - dow);
    for (var i = 0; i < 42; i++) {
      var ds = isoDate(cur); var out = cur.getMonth() !== m.getMonth();
      var s = starts[ds] || 0, o = ongoing[ds] || 0;
      var sel = state.days.indexOf(ds) >= 0, past = ds < TODAY;
      html += '<button type="button" class="day' + (out ? ' out' : '') + (past ? ' past' : '') + (s || o ? ' has' : '') + (ds === TODAY ? ' today' : '') + (sel ? ' sel' : '') + '" data-day="' + ds + '"' +
        (out || past ? ' tabindex="-1"' : ' aria-pressed="' + sel + '"') + '>' +
        '<span class="n">' + cur.getDate() + '</span>' + (s ? '<span class="starts">' + s + '</span>' : '') + (o ? '<span class="ongoing">+' + o + ' ' + tr('en curso') + '</span>' : '') + '</button>';
      cur.setDate(cur.getDate() + 1);
      if (i === 34 && cur.getMonth() !== m.getMonth()) break;
    }
    $('calGrid').innerHTML = html;
    var n = filtered().length;  // con los días elegidos, el contador dice cuántos planes hay esos días
    setCount(n, n !== EVENTS.length ? tr('de {n}', { n: num(EVENTS.length) }) : '', '');
    renderDay();
  }
  // Panel bajo el calendario: los planes de los días elegidos, por día. Un plan que dura varios días o que tiene
  // sesiones en varios de ellos sale una sola vez (en el primero).
  function renderDay() {
    var p = $('dayPanel');
    var days = state.days;
    if (!days.length) { p.hidden = true; return; }
    var one = days.length === 1, limit = one ? 120 : 40;
    var list = filtered(true).filter(function (e) { return !!firstSelDay(e); });
    var byDay = {}, on = [], longOnes = 0;
    list.forEach(function (e) {
      var d = firstSelDay(e);
      if (e.sessions || e.start === d) (byDay[d] = byDay[d] || []).push(e);
      else if (spanDays(e) <= LONG_DAYS) on.push(e);
      else longOnes++;
    });
    on.sort(function (a, b) { return a.end < b.end ? -1 : 1; });
    var total = list.length - longOnes;
    var h = '<h3>' + (one ? cap(fmtLong.format(fromIso(days[0]))) : tr('{n} días elegidos: {x}', { n: days.length, x: esc(daysLabel(6)) })) + ' · ' +
      num(total) + ' ' + tr(total === 1 ? 'plan' : 'planes') + '</h3>' +
      '<div class="day-actions"><button type="button" class="btn primary" data-goview="list">' + tr('Ver en la lista') + '</button>' +
      '<button type="button" class="btn" data-goview="map">' + tr('Ver en el mapa') + '</button>' +
      '<button type="button" class="btn" data-cleardays="1">✕ ' + tr(one ? 'Quitar día' : 'Quitar días') + '</button></div>';
    if (!total) h += '<p class="empty">' + tr(one ? 'Nada registrado ese día con los filtros actuales.' : 'Nada registrado esos días con los filtros actuales.') + '</p>';
    var k = 0;
    days.forEach(function (d) {
      var st = sorted(byDay[d] || []);
      if (!st.length) return;
      h += '<h4>' + (one ? tr('Este día') : esc(cap(fmtDayName.format(fromIso(d))))) + ' (' + st.length + ')</h4><div class="mini">' +
        st.slice(0, limit).map(function (e) { return card(e, { noOngoing: true, i: k++ }); }).join('') +
        (st.length > limit ? '<p class="empty">' + tr('… y {n} más. Pulsa «Ver en la lista» para verlos todos.', { n: st.length - limit }) + '</p>' : '') + '</div>';
      need(st.slice(0, limit));
    });
    if (on.length) {
      h += '<h4>' + tr('En curso') + ' (' + on.length + ')</h4><div class="mini">' + on.slice(0, 60).map(function (e) { return card(e, { noOngoing: true, i: k++ }); }).join('') +
        (on.length > 60 ? '<p class="empty">' + tr('… y {n} más. Pulsa «Ver en la lista» para verlos todos.', { n: on.length - 60 }) + '</p>' : '') + '</div>';
      need(on.slice(0, 60));
    }
    // La lista y el contador suman también estos, que el panel no enseña: se dice para que las cifras cuadren
    var perms = filtered(true).filter(isPermanent).length;
    var extra = [longOnes ? tr(longOnes === 1 ? '{n} plan de larga duración (exposiciones, temporadas…)' : '{n} planes de larga duración (exposiciones, temporadas…)', { n: longOnes }) : '',
                 perms ? tr(perms === 1 ? '{n} visita permanente' : '{n} visitas permanentes', { n: perms }) : ''].filter(Boolean).join(' ' + tr('y') + ' ');
    if (extra) h += '<p class="hint">' + tr('Además, {x}.', { x: extra }) + ' <button type="button" class="linklike" data-goview="list">' + tr('Verlos en la lista') + '</button></p>';
    p.innerHTML = h; p.hidden = false;
  }
  // Toque en un día del calendario: lo añade o lo quita de los elegidos (días sueltos, no hace falta que sean seguidos)
  function toggleDay(d) {
    var i = state.days.indexOf(d);
    if (i >= 0) state.days.splice(i, 1); else { state.days.push(d); state.days.sort(); }
    if (state.days.length) { state.from = ''; state.to = ''; $('from').value = ''; $('to').value = ''; }
    syncQuick();
    refresh();
  }
  function clearDays() { state.days = []; syncQuick(); }
  // Botón «Fechas…» de la barra rápida: con días elegidos dice «3 días» y queda marcado
  function syncQuick() {
    var b = $('quick').querySelector('[data-range="dates"]');
    if (state.days.length) {
      $('quick').querySelectorAll('button').forEach(function (x) { x.classList.remove('on'); });
      b.classList.add('on'); b.textContent = '📅 ' + (state.days.length === 1 ? tr('1 día') : tr('{n} días', { n: state.days.length }));
    } else {
      b.classList.remove('on'); b.textContent = tr('Fechas…');
    }
  }

  // ---------- mapa
  // Leaflet se descarga solo cuando se abre el mapa por primera vez:
  // quien nunca lo abre no paga sus ~150 KB en la carga inicial.
  var leafletState = '';
  function loadLeaflet() {
    if (typeof L !== 'undefined' || leafletState) return;
    leafletState = 'loading';
    ['https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
     'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.min.css',
     'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.Default.min.css'].forEach(function (href) {
      var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; document.head.appendChild(l);
    });
    var fail = function () { leafletState = 'error'; if (state.view === 'map') renderMap(); };
    var s1 = document.createElement('script');
    s1.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
    s1.onload = function () {
      var s2 = document.createElement('script');
      s2.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.min.js';
      s2.onload = function () { leafletState = 'ok'; if (state.view === 'map') renderMap(); };
      s2.onerror = fail;
      document.head.appendChild(s2);
    };
    s1.onerror = fail;
    document.head.appendChild(s1);
  }
  var map = null, cluster = null, youMarker = null;
  function ensureMap() {
    if (map || typeof L === 'undefined') return !!map;
    map = L.map('map', { scrollWheelZoom: true }).setView([40.2, -3.7], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(map);
    cluster = L.markerClusterGroup({ chunkedLoading: true, maxClusterRadius: 50 });
    map.addLayer(cluster);
    return true;
  }
  function renderMap() {
    if (typeof L === 'undefined' && leafletState !== 'error') {
      loadLeaflet();
      $('map').innerHTML = '<p class="empty">' + tr('Cargando el mapa…') + '</p>'; renderCoverage(); return;
    }
    if (!ensureMap()) { $('map').innerHTML = '<p class="empty">' + tr('El mapa no ha podido cargarse (sin conexión a la librería de mapas).') + '</p>'; renderCoverage(); return; }
    var list = filtered();
    cluster.clearLayers();
    var markers = [];
    list.forEach(function (e) {
      if (e.lat == null || e.lon == null) return;
      var mk = L.marker([e.lat, e.lon]);
      mk.bindPopup('<strong>' + esc(title(e)) + '</strong><br>' + esc(whenText(e)) + '<br>' + esc([e.venue, e.city].filter(Boolean).join(' · ')) + '<br><a href="#" data-open="' + e.id + '">' + tr('Ver ficha') + '</a>');
      markers.push(mk);
    });
    cluster.addLayers(markers);
    if (state.geo) {
      if (youMarker) map.removeLayer(youMarker);
      youMarker = L.circleMarker([state.geo.lat, state.geo.lon], { radius: 8, color: '#2563eb', fillOpacity: .8 }).addTo(map).bindPopup(tr('Tu ubicación'));
      map.setView([state.geo.lat, state.geo.lon], state.radius <= 10 ? 12 : state.radius <= 25 ? 11 : state.radius <= 50 ? 10 : 9);
    } else if (state.prov && CENTROIDS[state.prov]) {
      map.setView(CENTROIDS[state.prov], 9);
    }
    setCount(markers.length, tr('en el mapa'), tr('De {n}, solo los que tienen ubicación', { n: num(list.length) }));
    setTimeout(function () { map.invalidateSize(); }, 50);
    renderCoverage();
  }
  function renderCoverage() {
    var counts = {}; var max = 1;
    EVENTS.forEach(function (e) { if (matches(e) && e.province_code) { counts[e.province_code] = (counts[e.province_code] || 0) + 1; } });
    DATA.provinces.forEach(function (p) { if ((counts[p.code] || 0) > max) max = counts[p.code]; });
    $('coverage').innerHTML = DATA.provinces.slice().sort(function (a, b) { return (counts[b.code] || 0) - (counts[a.code] || 0) || a.name.localeCompare(b.name, 'es'); })
      .map(function (p) { var n = counts[p.code] || 0; return '<div class="row' + (n ? '' : ' zero') + '"><span>' + esc(p.name) + '</span><span class="bar"><i style="width:' + Math.round(100 * n / max) + '%"></i></span><span class="n">' + (n ? num(n) : tr('sin datos')) + '</span></div>'; }).join('');
  }

  // ---------- ficha (modal) y compartir
  function openModal(id) {
    var e = BY_ID[id];
    if (!e) { toast(tr('Ese plan ya no está en la agenda')); return; }
    need([e]);
    $('modalBody').innerHTML = card(e);
    var dlg = $('modal');
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute('open', '');
  }
  function closeModal() { var dlg = $('modal'); if (dlg.close) dlg.close(); else dlg.removeAttribute('open'); }
  function shareLink(e) {
    var url = new URL(evFile(e), location.href.split('?')[0]).href;
    var text = title(e) + ' · ' + whenText(e) + (e.city ? ' · ' + e.city : '');
    if (navigator.share) { navigator.share({ title: 'Planika: ' + title(e), text: text, url: url }).catch(function () {}); return; }
    copy(url, tr('Enlace del plan copiado'));
  }
  function copy(text, msg) {
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () { toast(msg); }, function () { prompt(tr('Copia el enlace:'), text); });
    else prompt(tr('Copia el enlace:'), text);
  }

  // ---------- añadir al calendario
  function calTimes(e) {
    if (isPermanent(e)) {
      return { allDay: true, start: TODAY.replace(/-/g, ''), end: addDays(TODAY, 1).replace(/-/g, '') };
    }
    var start0 = nextSession(e), end0 = e.sessions ? start0 : e.end;
    var allDay = !e.time;
    var start, end;
    if (allDay) { start = start0.replace(/-/g, ''); end = addDays(end0, 1).replace(/-/g, ''); }
    else {
      var t = e.time.replace(':', '') + '00';
      start = start0.replace(/-/g, '') + 'T' + t;
      var hh = +e.time.slice(0, 2) + 2; var endDay = start0;
      if (hh >= 24) { hh -= 24; endDay = addDays(start0, 1); }
      end = endDay.replace(/-/g, '') + 'T' + pad(hh) + e.time.slice(3) + '00';
    }
    return { allDay: allDay, start: start, end: end };
  }
  function details(e) {
    var parts = [];
    if (isPermanent(e)) parts.push(tr('Visita permanente, sin una fecha única. Este aviso es un recordatorio de un día.'));
    if (e.description) parts.push(e.description);
    if (e.sessions) parts.push(tr('Otras fechas:') + ' ' + e.sessions.join(', '));
    if (e.price) parts.push(tr('Precio:') + ' ' + e.price); else if (e.free) parts.push(tr('Entrada gratuita'));
    if (e.tickets_url) parts.push(tr('Entradas:') + ' ' + e.tickets_url);
    if (e.url && e.url !== e.tickets_url) parts.push(tr('Más información:') + ' ' + e.url);
    parts.push((e.source ? tr('Fuente:') + ' ' + e.source + ' · ' : '') + tr('vía Planika'));
    return parts.join('\n');
  }
  function location_(e) { return [e.venue, e.address, e.city, e.province].filter(Boolean).join(', '); }
  function isoLocal(s) { return s.length === 8 ? s.slice(0, 4) + '-' + s.slice(4, 6) + '-' + s.slice(6, 8) : s.slice(0, 4) + '-' + s.slice(4, 6) + '-' + s.slice(6, 8) + 'T' + s.slice(9, 11) + ':' + s.slice(11, 13) + ':00'; }
  function links(e) {
    var t = calTimes(e), enc = encodeURIComponent, tt = title(e), det = details(e), loc = location_(e);
    var google = 'https://calendar.google.com/calendar/render?action=TEMPLATE&text=' + enc(tt) + '&dates=' + t.start + '/' + t.end + '&details=' + enc(det) + '&location=' + enc(loc) + '&ctz=Europe/Madrid';
    var ol = '&subject=' + enc(tt) + '&startdt=' + enc(isoLocal(t.start)) + '&enddt=' + enc(isoLocal(t.end)) + '&body=' + enc(det) + '&location=' + enc(loc) + (t.allDay ? '&allday=true' : '');
    return { google: google, outlook: 'https://outlook.live.com/calendar/0/action/compose?rru=addevent' + ol, office: 'https://outlook.office.com/calendar/0/action/compose?rru=addevent' + ol,
      yahoo: 'https://calendar.yahoo.com/?v=60&title=' + enc(tt) + '&st=' + t.start + (t.allDay ? '&dur=allday' : '&et=' + t.end) + '&desc=' + enc(det) + '&in_loc=' + enc(loc) };
  }
  // Aviso en el móvil: 2 horas antes; si es de todo el día, a las 9:00 de ese día
  function icsAlarm(allDay, what) {
    return ['BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + what, 'TRIGGER:' + (allDay ? 'PT9H' : '-PT2H'), 'END:VALARM'];
  }
  function icsText(e) {
    var t = calTimes(e);
    var f = function (s) { return String(s).replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/[,;]/g, function (c) { return '\\' + c; }); };
    var stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Planika//planikaapp.com//ES', 'CALSCALE:GREGORIAN', 'BEGIN:VEVENT',
      'UID:' + e.id + '@planikaapp.com', 'DTSTAMP:' + stamp,
      t.allDay ? 'DTSTART;VALUE=DATE:' + t.start : 'DTSTART;TZID=Europe/Madrid:' + t.start,
      t.allDay ? 'DTEND;VALUE=DATE:' + t.end : 'DTEND;TZID=Europe/Madrid:' + t.end,
      'SUMMARY:' + f(title(e)), 'DESCRIPTION:' + f(details(e)), 'LOCATION:' + f(location_(e))];
    if (e.url || e.tickets_url) lines.push('URL:' + (e.tickets_url || e.url));
    if (e.lat != null && e.lon != null) lines.push('GEO:' + e.lat + ';' + e.lon);
    lines = lines.concat(icsAlarm(t.allDay, f(title(e))));
    lines.push('END:VEVENT', 'END:VCALENDAR');
    return lines.join('\r\n');
  }
  function downloadIcs(e) {
    var blob = new Blob([icsText(e)], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = title(e).replace(/[^\w\dáéíóúñü ]+/gi, '').trim().slice(0, 60).replace(/\s+/g, '_') + '.ics';
    document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  var menu = $('menu');
  // Qué dispositivo es: en iPhone y Android lo mejor es el archivo .ics (todo de una vez, con aviso; Google Calendar
  // para Android lo abre desde octubre de 2025); en el ordenador, primero Google Calendar.
  var DEVICE = (function () {
    var ua = navigator.userAgent || '';
    if (/Android/i.test(ua)) return 'android';
    if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return 'ios';
    return 'desktop';
  })();
  function openMenu(btn, e) {
    var l = links(e), mobile = DEVICE !== 'desktop';
    var ics = '<button type="button" data-act="ics">' + (mobile ? '📱 ' + tr('Calendario del móvil (.ics)') : 'Apple Calendar / iCal (.ics)') + ' 🔔</button>';
    var google = '<a href="' + l.google + '" target="_blank" rel="noopener">Google Calendar</a>';
    menu.innerHTML = (mobile ? ics + google : google + ics) +
      '<a href="' + l.outlook + '" target="_blank" rel="noopener">Outlook.com</a>' +
      '<a href="' + l.office + '" target="_blank" rel="noopener">Microsoft 365</a>' +
      '<a href="' + l.yahoo + '" target="_blank" rel="noopener">Yahoo Calendar</a>';
    menu.querySelector('[data-act="ics"]').addEventListener('click', function () { downloadIcs(e); closeMenu(); });
    menu.hidden = false;
    var r = btn.getBoundingClientRect();
    var left = Math.min(r.left + window.scrollX, window.scrollX + document.documentElement.clientWidth - menu.offsetWidth - 8);
    menu.style.left = left + 'px'; menu.style.top = (r.bottom + window.scrollY + 6) + 'px';
  }
  function closeMenu() { menu.hidden = true; }

  // ---------- eventos de UI
  function byId(id) { return BY_ID[id]; }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('.addcal');
    if (b) { ev.stopPropagation(); var e = byId(b.dataset.id); if (e && !e._d) { need([e]); toast(tr('Cargando el plan… vuelve a pulsar en un momento')); return; } if (e) openMenu(b, e); return; }
    if (!ev.target.closest('#menu')) closeMenu();
    var f = ev.target.closest('[data-fav]');
    if (f) { var id = f.dataset.fav; if (favSet.has(id)) favSet.delete(id); else favSet.add(id); saveFavs();
      document.querySelectorAll('[data-fav="' + id + '"]').forEach(function (x) { x.classList.toggle('on', favSet.has(id)); x.textContent = favSet.has(id) ? '★' : '☆'; });
      if (state.favs) refresh(); return; }
    var s = ev.target.closest('[data-share]');
    if (s) { var e2 = byId(s.dataset.share); if (e2) shareLink(e2); return; }
    var pb = ev.target.closest('[data-plan]');
    if (pb) { togglePlan(pb.dataset.plan); return; }
    var o = ev.target.closest('[data-open]');
    if (o) { ev.preventDefault(); openModal(o.dataset.open); return; }
    var gv = ev.target.closest('[data-goview]');
    if (gv) { var to = gv.dataset.goview === 'map' ? 'mapView' : 'list'; setView(gv.dataset.goview); window.scrollTo({ top: $(to).offsetTop - 80, behavior: 'smooth' }); return; }
    if (ev.target.closest('[data-cleardays]')) { clearDays(); refresh(); return; }
    var d = ev.target.closest('.day');
    if (d && !d.classList.contains('out') && !d.classList.contains('past')) toggleDay(d.dataset.day);
  });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') { closeMenu(); } });
  $('modalClose').addEventListener('click', closeModal);
  $('modal').addEventListener('click', function (ev) { if (ev.target === $('modal')) closeModal(); });

  function rerender() { if (state.view === 'list') renderList(); else if (state.view === 'cal') renderCalendar(); else renderMap(); }
  function refresh() { state.shown = PAGE; writeURL(); if (state.q) loadAll(); syncUI(); rerender(); }
  function setView(v) {
    state.view = v;
    $('view').querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.view === v); });
    $('calendar').hidden = v !== 'cal'; $('list').hidden = v !== 'list'; $('more').hidden = v !== 'list'; $('mapView').hidden = v !== 'map';
    refresh();
  }
  function clearQuick() { $('quick').querySelectorAll('button').forEach(function (b) { b.classList.remove('on'); }); }
  function setRange(key) {
    clearDays();
    $('quick').querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.range === key); });
    var from = TODAY, to = '';
    if (key === 'all') from = '';
    else if (key === 'today') to = TODAY;
    else if (key === 'weekend') {
      var d = fromIso(TODAY); var dow = (d.getDay() + 6) % 7; // 0 = lunes
      var sat = addDays(TODAY, dow <= 5 ? 5 - dow : 0); var sun = addDays(sat, 1);
      from = dow >= 4 ? TODAY : sat; to = sun;
    } else to = addDays(TODAY, +key);
    state.from = from; state.to = to; $('from').value = from; $('to').value = to;
    refresh();
  }
  var qt;
  $('q').addEventListener('input', function () { clearTimeout(qt); qt = setTimeout(function () { state.q = $('q').value.trim(); refresh(); }, 180); });
  $('ccaa').addEventListener('change', function () { state.ccaa = this.value; fillProvinces(); refresh(); });
  var wh = $('where');
  // En el móvil, el campo sube arriba de la pantalla para que la lista quepa encima del teclado.
  var SMALL = window.matchMedia ? window.matchMedia('(max-width: 640px)') : { matches: false };
  wh.addEventListener('focus', function () {
    if (SMALL.matches) setTimeout(function () { wh.closest('.field').scrollIntoView({ block: 'start', behavior: 'smooth' }); }, 250);
  });
  wh.addEventListener('focus', function () { var el = this; setTimeout(function () { try { el.setSelectionRange(0, el.value.length); } catch (e) { /* */ } }, 0); showPlaces(''); });
  wh.addEventListener('input', function () { $('whereClear').hidden = !this.value; showPlaces(this.value); });
  wh.addEventListener('keydown', function (ev) {
    if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
      ev.preventDefault(); if ($('whereList').hidden) showPlaces(this.value); else moveActive(ev.key === 'ArrowDown' ? 1 : -1);
    } else if (ev.key === 'Enter') {
      ev.preventDefault();
      if (!this.value.trim()) pickPlace(null);
      else if (SUGG.length) pickPlace(SUGG[ACTIVE >= 0 ? ACTIVE : 0].t === 'all' ? null : SUGG[ACTIVE >= 0 ? ACTIVE : 0]);
      this.blur();
    } else if (ev.key === 'Escape') { closePlaces(); syncWhere(); this.blur(); }
  });
  // Al salir sin elegir: si se ha borrado todo es «Toda España»; si no, vuelve el lugar que había.
  wh.addEventListener('blur', function () {
    setTimeout(function () {
      if (document.activeElement === wh) return;
      if (!wh.value.trim() && placeLabel()) pickPlace(null); else { closePlaces(); syncWhere(); }
    }, 150);
  });
  $('whereList').addEventListener('mousedown', function (ev) { ev.preventDefault(); });  // que el campo no pierda el foco
  $('whereList').addEventListener('click', function (ev) {
    var li = ev.target.closest('li[data-i]'); if (!li) return;
    var p = SUGG[+li.dataset.i]; pickPlace(p && p.t !== 'all' ? p : null); wh.blur();
  });
  $('whereClear').addEventListener('click', function () { pickPlace(null); wh.focus(); });
  $('city').addEventListener('change', function () { state.city = this.value; CITY_KEY = norm(this.value); fillCities(); syncWhere(); refresh(); });
  $('what').querySelectorAll('a.chip').forEach(function (a) { if (a.dataset.cat) WHAT_CATS[a.dataset.cat] = true; });
  $('what').addEventListener('click', function (ev) {
    var a = ev.target.closest('a.chip');
    if (a) {
      // Con modificadores (abrir en otra pestaña) se respeta el enlace a la página del tema.
      if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
      ev.preventDefault();
      if (a.dataset.free) { state.free = !state.free; $('free').checked = state.free; } else state.cats[a.dataset.cat] = !state.cats[a.dataset.cat];
      refresh(); return;
    }
    if (ev.target.closest('#moreTypes')) { $('adv').open = true; $('cats').scrollIntoView({ behavior: 'smooth', block: 'center' }); }
  });
  $('clearAll').addEventListener('click', function () {
    state.planOnly = false;
    state.q = ''; state.ccaa = ''; state.prov = ''; state.city = ''; state.free = false; state.tickets = false; state.cats = {};
    state.tod = ''; state.aud = ''; state.pmax = ''; state.favs = false;
    if (state.geo) { state.geo = null; $('geoBtn').textContent = '📍 ' + tr('Activar'); $('geoBtn').classList.remove('on'); }
    $('q').value = ''; $('ccaa').value = ''; fillProvinces(); syncWhere(); fillCities(); $('free').checked = false; $('tickets').checked = false;
    $('tod').value = ''; $('aud').value = ''; $('pmax').value = ''; $('favs').checked = false;
    setRange('all');
  });
  $('prov').addEventListener('change', function () { state.prov = this.value; refresh(); });
  $('from').addEventListener('change', function () { state.from = this.value; clearDays(); clearQuick(); refresh(); });
  $('to').addEventListener('change', function () { state.to = this.value; clearDays(); clearQuick(); refresh(); });
  ['free', 'tickets', 'favs'].forEach(function (id) { $(id).addEventListener('change', function () { state[id] = this.checked; refresh(); }); });
  ['tod', 'aud', 'pmax'].forEach(function (id) { $(id).addEventListener('change', function () { state[id] = this.value; refresh(); }); });
  $('pmax').addEventListener('input', function () { clearTimeout(qt); var v = this.value; qt = setTimeout(function () { state.pmax = v; refresh(); }, 300); });
  $('radius').addEventListener('change', function () { state.radius = +this.value; if (state.geo) refresh(); });
  $('geoBtn').addEventListener('click', function () {
    if (state.geo) { state.geo = null; this.textContent = '📍 ' + tr('Activar'); this.classList.remove('on'); refresh(); return; }
    if (!navigator.geolocation) { toast(tr('Tu navegador no permite obtener la ubicación')); return; }
    var btn = this; btn.textContent = '⏳ ' + tr('Buscando…');
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.geo = { lat: pos.coords.latitude, lon: pos.coords.longitude }; btn.textContent = '📍 ' + tr('Activado'); btn.classList.add('on'); refresh();
    }, function () { btn.textContent = '📍 ' + tr('Activar'); toast(tr('No se ha podido obtener tu ubicación')); }, { timeout: 10000, maximumAge: 300000 });
  });
  $('quick').addEventListener('click', function (ev) {
    var b = ev.target.closest('button'); if (!b) return;
    if (b.dataset.range === 'dates') {
      if (state.days.length) { setView('cal'); window.scrollTo({ top: $('calendar').offsetTop - 80, behavior: 'smooth' }); return; }
      $('adv').open = true; $('from').focus(); return;
    }
    setRange(b.dataset.range);
  });
  $('view').addEventListener('click', function (ev) { var b = ev.target.closest('button'); if (b) setView(b.dataset.view); });
  $('more').addEventListener('click', function () { state.shown += PAGE; renderList(); });
  $('prevM').addEventListener('click', function () { state.month = new Date(state.month.getFullYear(), state.month.getMonth() - 1, 1); renderCalendar(); });
  $('nextM').addEventListener('click', function () { state.month = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 1); renderCalendar(); });
  $('todayM').addEventListener('click', function () { state.month = fromIso(TODAY); renderCalendar(); });

  // ---------- app instalable (PWA) y sin conexión
  function track(name, params) { try { if (window.gtag) window.gtag('event', name, params || {}); } catch (e) { /* sin analítica */ } }
  var standalone = (window.matchMedia && matchMedia('(display-mode: standalone)').matches) || navigator.standalone === true;
  var ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var mobile = ios || /android/i.test(navigator.userAgent) || (window.matchMedia && matchMedia('(pointer: coarse)').matches);
  var installEv = null;
  if (!standalone) {
    // Chrome, Edge y Samsung Internet avisan cuando se puede instalar (Chrome, solo tras un toque y 30 s en la web):
    // entonces el botón abre su ventana de instalación. En el móvil el botón sale siempre; mientras el navegador no
    // avise (o en iPhone, que no avisa nunca), explica cómo instalarla desde su menú.
    window.addEventListener('beforeinstallprompt', function (ev) { ev.preventDefault(); installEv = ev; $('installWrap').hidden = false; });
    if (mobile) $('installWrap').hidden = false;
  } else {
    track('pwa_open');
  }
  $('installBtn').addEventListener('click', function () {
    track('pwa_install_click', { method: installEv ? 'prompt' : (ios ? 'ios' : 'menu') });
    if (installEv) {
      installEv.prompt();
      installEv.userChoice.then(function (c) { track('pwa_install_choice', { outcome: c.outcome }); if (c.outcome === 'accepted') $('installWrap').hidden = true; });
      installEv = null;
      return;
    }
    $('installIos').hidden = $('installIosSteps').hidden = $('installIosApp').hidden = !ios; $('installOther').hidden = ios;
    if ($('installHelp').showModal) $('installHelp').showModal(); else $('installHelp').setAttribute('open', '');
  });
  $('installHelpClose').addEventListener('click', function () { $('installHelp').close(); });
  window.addEventListener('appinstalled', function () { $('installWrap').hidden = true; track('pwa_installed'); toast(tr('¡Planika instalada! Ya la tienes en tu pantalla de inicio')); });
  function netState() { $('offline').hidden = navigator.onLine !== false; }
  window.addEventListener('online', netState); window.addEventListener('offline', netState); netState();
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js').catch(function () { /* sin service worker */ }); });
  }

  // ---------- menú lateral
  var sideMenu = $('sidemenu'), sideVeil = $('menuVeil'), menuBtn = $('menuBtn');  // (menu ya es el menú «⋯»)
  function openSide() {
    var n = loadFavs().size;
    $('menuFavCount').textContent = n ? String(n) : '';
    sideMenu.hidden = false; sideVeil.hidden = false; document.body.classList.add('menu-open');
    requestAnimationFrame(function () { sideMenu.classList.add('open'); });
    menuBtn.setAttribute('aria-expanded', 'true');
    $('menuClose').focus();
    track('menu_open');
  }
  function closeSide() {
    sideMenu.classList.remove('open'); sideVeil.hidden = true; document.body.classList.remove('menu-open');
    menuBtn.setAttribute('aria-expanded', 'false');
    setTimeout(function () { if (!sideMenu.classList.contains('open')) sideMenu.hidden = true; }, 230);
    menuBtn.focus();
  }
  menuBtn.addEventListener('click', openSide);
  $('menuClose').addEventListener('click', closeSide);
  sideVeil.addEventListener('click', closeSide);
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && !sideMenu.hidden) closeSide(); });
  // Las opciones de la propia app no recargan la página: cambian la vista o el filtro y bajan a la lista
  sideMenu.addEventListener('click', function (ev) {
    var a = ev.target.closest('[data-menu]');
    if (!a) return;
    ev.preventDefault();
    var act = a.dataset.menu;
    closeSide();
    if (act === 'plan') { openPlans(); track('menu_plan'); return; }
    if (act === 'favs') { state.favs = true; $('favs').checked = true; refresh(); setView('list'); }
    else if (act === 'cal' || act === 'map') setView(act);
    else if (act === 'near') { $('geoBtn').click(); }
    var target = act === 'map' ? 'mapView' : act === 'cal' ? 'calendar' : act === 'near' ? 'near' : 'list';
    setTimeout(function () { window.scrollTo({ top: $(target).offsetTop - 80, behavior: 'smooth' }); }, 60);
    track('menu_' + act);
  });

  // ---------- mis planes
  // Varios planes tuyos («Sábado en Bilbao», «Navidad con los primos»…). Cada uno lleva planes de la agenda (con el
  // día elegido) y notas propias, ordenados por hora. Se guardan en el móvil (como los favoritos), sin cuentas ni
  // servidor, y cada uno viaja entero en su enlace para compartir (?miplan=…).
  var MAX_PLANS = 20;
  var PLAN_Q = location.search;  // al arrancar, writeURL() reescribe la URL con los filtros: se guarda antes
  var store = loadPlans(), sharedPlan = null, planMode = 'one', pickFor = null, pickThenOpen = false;
  var plan = byPlanId(store.a);  // el plan activo: el último que abriste o al que añadiste algo
  function newId() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function cleanPlan(p) {
    p = p && typeof p === 'object' ? p : {};
    var ok = function (d) { return typeof d === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(d); };
    var q = {
      id: typeof p.id === 'string' && /^[\w-]{1,24}$/.test(p.id) ? p.id : newId(),
      n: String(p.n || '').slice(0, 60),
      i: (Array.isArray(p.i) ? p.i : []).filter(function (x) { return Array.isArray(x) && typeof x[0] === 'string' && ok(x[1]); }).slice(0, 40),
      o: (Array.isArray(p.o) ? p.o : []).filter(function (x) { return x && ok(x.d) && typeof x.x === 'string'; })
        .map(function (x) { return { d: x.d, t: /^\d{2}:\d{2}$/.test(x.t || '') ? x.t : '', x: x.x.slice(0, 80) }; }).slice(0, 20)
    };
    // Plan compartido en vivo: id del servidor (va en el enlace), versión y huella de lo último sincronizado
    if (typeof p.s === 'string' && /^[A-Za-z0-9_-]{22}$/.test(p.s)) { q.s = p.s; q.v = Math.max(0, parseInt(p.v, 10) || 0); q.h = String(p.h || '').slice(0, 16); }
    return q;
  }
  function loadPlans() {
    var s = null;
    try { s = JSON.parse(localStorage.getItem('planika_plans') || 'null'); } catch (e) { s = null; }
    if (!s || !Array.isArray(s.p)) {
      // Antes había un solo plan («planika_plan»): pasa a ser el primero de «Mis planes»
      var old = null;
      try { old = JSON.parse(localStorage.getItem('planika_plan') || 'null'); } catch (e) { old = null; }
      old = cleanPlan(old);
      s = { a: old.id, p: old.i.length || old.o.length || old.n ? [old] : [] };
    }
    var seen = {}, ps = s.p.map(cleanPlan).slice(0, MAX_PLANS);
    ps.forEach(function (p) { if (seen[p.id]) p.id = newId(); seen[p.id] = 1; });
    return { a: seen[s.a] ? s.a : ps[0] ? ps[0].id : '', p: ps };
  }
  function byPlanId(id) { return store.p.filter(function (p) { return p.id === id; })[0] || null; }
  function setActive(p) { plan = p; store.a = p ? p.id : ''; }
  function planSize(p) { return p.i.length + p.o.length; }
  function planTitle(p) { return p.n || tr('Plan sin nombre'); }
  function planDays(p) {
    var d = {};
    p = p || plan;
    if (!p) return [];
    p.i.forEach(function (x) { d[x[1]] = 1; }); p.o.forEach(function (x) { d[x.d] = 1; });
    return Object.keys(d).sort();
  }
  // Un plan es «pasado» cuando ya pasaron todos sus días; no se borra nunca solo, va a «Pasados»
  function isPast(p) { var d = planDays(p); return !!d.length && d[d.length - 1] < TODAY; }
  function livePlans() { return store.p.filter(function (p) { return !isPast(p); }); }
  function sortPlans(ps) {  // por el primer día; los vacíos, al final
    return ps.slice().sort(function (a, b) { var x = planDays(a)[0] || '9', y = planDays(b)[0] || '9'; return x < y ? -1 : x > y ? 1 : 0; });
  }
  // Los planes vacíos y sin nombre no se guardan, salvo el que tienes abierto (el de «＋ Nuevo plan»)
  function prune() { store.p = store.p.filter(function (p) { return p === plan || planSize(p) || p.n.trim(); }); }
  function makeRoom() {
    prune();
    if (store.p.length < MAX_PLANS) return true;
    toast(tr('Ya tienes {n} planes: borra alguno para crear otro', { n: MAX_PLANS }));
    return false;
  }
  function addPlan(p) { store.p.push(p); return p; }
  function persist() { try { localStorage.setItem('planika_plans', JSON.stringify(store)); } catch (e) { /* sin almacenamiento */ } }
  function savePlan() {
    prune();
    persist();
    liveSoon();
    var full = store.p.filter(function (p) { return planSize(p) && !isPast(p); }).length, cur = plan && planSize(plan) && !isPast(plan) ? plan : null;
    $('planPill').hidden = !full;
    $('planPillT').textContent = cur ? (cur.n || tr('Mi plan')) : tr('Mis planes');
    $('planPillN').textContent = cur ? planSize(cur) : full;
    document.body.classList.toggle('has-plan', !!full);
    $('menuPlanCount').textContent = full ? String(full) : '';
  }
  function has(p, id) { return p.i.some(function (x) { return x[0] === id; }); }
  function plansWith(id) { return store.p.filter(function (p) { return has(p, id); }).length; }
  function inPlan(id) { return !!plan && has(plan, id); }  // el filtro «solo tu plan» del mapa: el plan activo
  function planLabel(id) {
    var n = plansWith(id);
    return n > 1 ? '✓ ' + tr('En {n} planes', { n: n }) : n ? '✓ ' + tr('En tu plan') : '＋ ' + tr('Mi plan');
  }
  function planBtn(id) {
    var on = plansWith(id) > 0;
    return '<button type="button" class="btn addplan' + (on ? ' on' : '') + '" data-plan="' + id + '" aria-pressed="' + on + '">' + planLabel(id) + '</button>';
  }
  function syncPlanBtns(id) {
    var on = plansWith(id) > 0, label = planLabel(id);
    document.querySelectorAll('[data-plan="' + id + '"]').forEach(function (b) { b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); b.textContent = label; });
  }
  // Día del plan en que se irá: el primero de los días elegidos o del plan en que se puede; si no, la próxima fecha
  function pickDay(e, p) {
    var cands = state.days.concat(planDays(p));
    for (var i = 0; i < cands.length; i++) if (cands[i] >= TODAY && (isPermanent(e) || onDay(e, cands[i]))) return cands[i];
    if (isPermanent(e)) return cands[0] || TODAY;
    if (e.sessions) return nextSession(e);
    return e.start > TODAY ? e.start : TODAY;
  }
  function addTo(p, id) { if (BY_ID[id] && !has(p, id)) p.i.push([id, pickDay(BY_ID[id], p)]); }
  // «＋ Mi plan»: con un solo plan (o ninguno) se añade directamente; con varios, se pregunta a cuál
  function togglePlan(id, thenOpen) {
    if (!byId(id)) return;
    var live = livePlans();
    if (live.length > 1) { openPick(id, thenOpen); return; }
    var p = live[0];
    if (!p) { if (!makeRoom()) return; p = addPlan(cleanPlan(null)); }
    toggleIn(p, id);
    if (thenOpen) openPlanId(p.id);
  }
  function toggleIn(p, id) {
    var many = store.p.length > 1;
    setActive(p);
    if (has(p, id)) {
      p.i = p.i.filter(function (x) { return x[0] !== id; });
      toast(many ? tr('Quitado de «{p}»', { p: planTitle(p) }) : tr('Quitado de tu plan'));
    } else {
      addTo(p, id);
      var d = fmtD(p.i[p.i.length - 1][1]).replace(',', '');
      toast(many ? tr('Añadido a «{p}» ({d})', { p: planTitle(p), d: d }) : tr('Añadido a tu plan ({d})', { d: d }));
      track('plan_add');
    }
    savePlan(); syncPlanBtns(id);
    if ($('planDlg').open) redraw();
  }
  // Elegir plan: primero el último que usaste, luego por fecha. Si ya está en uno, al tocarlo se quita.
  function planMeta(p) {
    var d = planDays(p), bits = [], ni = p.i.length, no = p.o.length;
    if (d.length) bits.push(fmtD(d[0]).replace(',', '') + (d.length > 1 ? ' – ' + fmtD(d[d.length - 1]).replace(',', '') : ''));
    if (ni) bits.push(ni === 1 ? tr('1 plan') : tr('{n} planes', { n: ni }));
    if (no) bits.push(no === 1 ? tr('1 nota') : tr('{n} notas', { n: no }));
    if (!ni && !no) bits.push(tr('Vacío'));
    if (p.s) bits.push('👥 ' + tr('Compartido'));
    return bits.join(' · ');
  }
  function planRow(p, cls, attr, sub, on) {
    return '<button type="button" class="plans-row ' + cls + (on ? ' on' : '') + '" ' + attr + '="' + p.id + '"><span class="pr-t"><b>' +
      (on ? '✓ ' : '') + esc(planTitle(p)) + '</b><span>' + esc(sub) + '</span></span><span class="pr-go" aria-hidden="true">' + (on ? '✕' : '›') + '</span></button>';
  }
  function openPick(id, thenOpen) {
    var e = BY_ID[id];
    if (!e) return;
    pickFor = id; pickThenOpen = !!thenOpen;
    var live = sortPlans(livePlans());
    if (plan && live.indexOf(plan) > 0) { live.splice(live.indexOf(plan), 1); live.unshift(plan); }
    $('pickEv').textContent = title(e);
    $('pickList').innerHTML = live.map(function (p, k) {
      var on = has(p, id);
      return planRow(p, 'pop' + (k % 4), 'data-pick', on ? tr('Ya está: tócalo para quitarlo') : planMeta(p), on);
    }).join('');
    if (!$('pickDlg').open) $('pickDlg').showModal();
    track('plan_pick_open');
  }
  $('pickList').addEventListener('click', function (ev) {
    var b = ev.target.closest('[data-pick]'), p = b && byPlanId(b.dataset.pick), id = pickFor;
    if (!p || !id) return;
    $('pickDlg').close();
    toggleIn(p, id);
    if (pickThenOpen) openPlanId(p.id);
  });
  $('pickNew').addEventListener('click', function () {
    var id = pickFor;
    if (!id || !makeRoom()) return;
    var p = addPlan(cleanPlan(null));
    $('pickDlg').close();
    setActive(p); addTo(p, id); savePlan(); syncPlanBtns(id); track('plan_new', { from: 'pick' });
    openPlanId(p.id, true);
  });
  $('pickClose').addEventListener('click', function () { $('pickDlg').close(); });
  $('pickDlg').addEventListener('click', function (ev) { if (ev.target === $('pickDlg')) $('pickDlg').close(); });
  $('pickDlg').addEventListener('close', function () { pickFor = null; });
  // La ventana tiene dos vistas: la lista «Mis planes» y un plan abierto
  function showMode(m) {
    planMode = m;
    $('plansView').hidden = m !== 'list'; $('planView').hidden = m === 'list';
    $('planDlg').setAttribute('aria-labelledby', m === 'list' ? 'plansTitle' : 'planName');
    $('planCal').hidden = true;
    syncAppHint();
    clearInterval(livePoll);
    livePoll = setInterval(function () { if ($('planDlg').open) livePull(); else clearInterval(livePoll); }, 20000);
    if (!$('planDlg').open) $('planDlg').showModal();
    $('planDlg').scrollTop = 0;
  }
  function redraw() { if (planMode === 'list') renderPlans(); else renderPlan(); }
  function syncAppHint() { $('planAppHint').hidden = !(FROM_LINK && planMode === 'one'); }
  function renderPlans() {
    var live = sortPlans(livePlans()), past = store.p.filter(isPast).sort(function (a, b) {
      var x = planDays(a).pop(), y = planDays(b).pop(); return x < y ? 1 : x > y ? -1 : 0;
    });
    $('plansList').innerHTML = live.length ? live.map(function (p, k) { return planRow(p, 'pop' + (k % 4), 'data-open-plan', planMeta(p)); }).join('')
      : '<div class="empty">' + tr('Aún no tienes ningún plan. Crea uno o pulsa «＋ Mi plan» en cualquier plan de la agenda.') + '</div>';
    $('plansPast').hidden = !past.length;
    $('plansPastSum').textContent = tr('Pasados ({n})', { n: past.length });
    $('plansPastList').innerHTML = past.map(function (p) { return planRow(p, 'past', 'data-open-plan', planMeta(p)); }).join('');
  }
  function openPlans() { sharedPlan = null; showMode('list'); renderPlans(); track('plans_open'); livePullSoon(); }
  function openPlanId(id, focusName) {
    var p = byPlanId(id);
    if (!p) { openPlans(); return; }
    sharedPlan = null; setActive(p); savePlan();
    showMode('one'); renderPlan();
    if (focusName) $('planName').focus();
    track('plan_open');
    livePullSoon();
  }
  function openPlan() { if (plan && !isPast(plan) && planSize(plan)) openPlanId(plan.id); else openPlans(); }
  // Mismo plan (nombre, planes y notas): para no guardar dos veces el que te reenvían o tu propio enlace
  function samePlan(q) {
    if (q.s) return store.p.filter(function (p) { return p.s === q.s; })[0] || null;
    var sig = JSON.stringify([q.n, q.i, q.o]);
    return store.p.filter(function (p) { return JSON.stringify([p.n, p.i, p.o]) === sig; })[0] || null;
  }
  $('plansView').addEventListener('click', function (ev) { var b = ev.target.closest('[data-open-plan]'); if (b) openPlanId(b.dataset.openPlan); });
  $('plansNew').addEventListener('click', function () {
    if (!makeRoom()) return;
    var p = addPlan(cleanPlan(null));
    track('plan_new', { from: 'list' });
    openPlanId(p.id, true);
  });
  $('planBack').addEventListener('click', openPlans);
  function km(a, b) {
    var R = 6371, rad = Math.PI / 180, dLat = (b.lat - a.lat) * rad, dLon = (b.lon - a.lon) * rad;
    var h = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }
  // Coordenadas aproximadas: cuando una fuente no da la sala exacta, el plan lleva el centro de la ciudad, y ese
  // mismo punto lo comparten muchas salas distintas. Ahí no se calcula el paseo (saldría «en el mismo sitio»).
  var approxPts = null;
  function approxPoint(e) {
    if (!approxPts) {
      var v = {};
      EVENTS.forEach(function (x) { if (x.lat == null) return; var k = x.lat + ',' + x.lon; (v[k] = v[k] || {})[x.venue || '?'] = 1; });
      approxPts = {};
      Object.keys(v).forEach(function (k) { if (Object.keys(v[k]).length > 3) approxPts[k] = 1; });
    }
    return !!approxPts[e.lat + ',' + e.lon];
  }
  function walkable(a, b) {
    if (a.lat == null || b.lat == null) return false;
    if (a.lat === b.lat && a.lon === b.lon) return !!a.venue && a.venue === b.venue;
    return !approxPoint(a) && !approxPoint(b);
  }
  function mins(t) { return t ? +t.slice(0, 2) * 60 + +t.slice(3, 5) : null; }
  // Filas del plan por día: planes y notas, por hora (lo que no tiene hora va primero, «todo el día»)
  function planRows(p) {
    var rows = [];
    p.i.forEach(function (x) { var e = BY_ID[x[0]]; rows.push({ d: x[1], t: e ? e.time : '', e: e, id: x[0] }); });
    p.o.forEach(function (x, k) { rows.push({ d: x.d, t: x.t, note: x.x, k: k }); });
    rows.sort(function (a, b) { return a.d < b.d ? -1 : a.d > b.d ? 1 : (a.t || '') < (b.t || '') ? -1 : (a.t || '') > (b.t || '') ? 1 : 0; });
    return rows;
  }
  function renderPlan() {
    var p = sharedPlan || plan, shared = !!sharedPlan;
    var rows = planRows(p), h = '', lastDay = '', prev = null, pop = 0;  // pop: los mismos 4 colores que las tarjetas, en orden
    $('planName').value = p.n; $('planName').readOnly = shared;
    $('planShared').hidden = !shared;
    $('planLive').hidden = !p.s;
    $('planLive').textContent = '👥 ' + (shared ? tr('Es un plan en vivo: guárdalo y verás los cambios que hagan los demás.')
      : tr('Plan compartido: quien tenga el enlace lo ve y lo edita, y los cambios les llegan a todos.'));
    if (!rows.length) {
      h = '<div class="empty">' + tr('Tu plan está vacío. Pulsa «＋ Mi plan» en cualquier plan de la lista o de su ficha y aparecerá aquí, ordenado por hora.') + '</div>';
    }
    rows.forEach(function (r) {
      if (r.d !== lastDay) {
        h += '<h3 class="plan-day">' + esc(cap(fmtDayName.format(fromIso(r.d)))) + '</h3>';
        lastDay = r.d; prev = null;
      }
      if (prev && prev.e && r.e && walkable(prev.e, r.e)) {
        var k = km(prev.e, r.e) * 1.3, walk = Math.round(k / 4.8 * 60);
        h += '<div class="plan-walk">' + (k < 0.15 ? (prev.e.venue && prev.e.venue === r.e.venue ? '📍 ' + tr('En el mismo sitio') : '🚶 ' + tr('Al lado: 1 o 2 min a pie')) : walk <= 40 ? '🚶 ' + tr('unos {n} min a pie', { n: Math.max(1, walk) }) : '🚌 ' + tr('a {n} km: mejor en transporte', { n: k < 10 ? k.toFixed(1) : Math.round(k) })) + '</div>';
      }
      // Aviso de solape entre planes de la agenda (no con las notas): menos de hora y media entre uno y otro
      if (prev && prev.e && r.e && mins(r.t) != null && mins(prev.t) != null && mins(r.t) - mins(prev.t) < 90) {
        var gap = mins(r.t) - mins(prev.t);
        h += '<div class="plan-warn">⚠ ' + (gap <= 0 ? tr('Empieza a la vez que el anterior') : tr('Empieza solo {n} min después del anterior', { n: gap })) + '</div>';
      }
      if (r.note != null) {
        h += '<div class="plan-item note"><span class="tm">' + (r.t || '—') + '</span><div><b>' + esc(r.note) + '</b><span>📌 ' + tr('Nota') + '</span></div>' +
          (shared ? '' : '<button type="button" class="plan-x" data-plan-note="' + r.k + '" aria-label="' + tr('Quitar nota') + '">✕</button>') + '</div>';
      } else if (!r.e) {
        h += '<div class="plan-item gone"><span class="tm">—</span><div><b>' + tr('Este plan ya no está en la agenda') + '</b><span>' + tr('Puede que se haya cancelado o que ya haya pasado') + '</span></div>' +
          (shared ? '' : '<button type="button" class="plan-x" data-plan-del="' + r.id + '" aria-label="' + tr('Quitar') + '">✕</button>') + '</div>';
      } else {
        var e = r.e, where = [e.venue, e.city].filter(Boolean).join(' · ');
        var price = e.free ? tr('Gratis') : e.price;
        h += '<div class="plan-item pop' + (pop++ % 4) + '"><span class="tm">' + (r.t || tr('Todo el día')) + '</span><div><a href="' + esc(evFile(e)) + '"><b>' + esc(title(e)) + '</b></a>' +
          '<span>' + esc([where, price].filter(Boolean).join(' · ')) + '</span></div>' +
          (shared ? '' : '<button type="button" class="plan-x" data-plan-del="' + e.id + '" aria-label="' + tr('Quitar del plan') + '">✕</button>') + '</div>';
      }
      prev = r;
    });
    $('planList').innerHTML = h;
    $('planNoteForm').hidden = shared || !rows.length;
    $('planActions').hidden = shared;
    var days = planDays();
    $('planNoteDay').innerHTML = days.map(function (d) { return '<option value="' + d + '">' + esc(fmtD(d).replace(',', '')) + '</option>'; }).join('');
    $('planNoteDay').hidden = days.length < 2;
  }
  function planURL(p) {
    var json = JSON.stringify({ n: p.n, i: p.i, o: p.o });
    var b64 = btoa(unescape(encodeURIComponent(json))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    return location.href.split('?')[0].split('#')[0] + '?miplan=' + b64;
  }
  function planText(p) {
    var lines = ['🗓 ' + (p.n || tr('Mi plan')) + ' (Planika)'], last = '';
    planRows(p).forEach(function (r) {
      if (r.d !== last) { lines.push('', cap(fmtDayName.format(fromIso(r.d)))); last = r.d; }
      var what = r.note != null ? r.note : r.e ? title(r.e) + (r.e.venue || r.e.city ? ' (' + (r.e.venue || r.e.city) + ')' : '') : tr('Plan que ya no está');
      lines.push('· ' + (r.t || tr('Todo el día')) + ' ' + what);
    });
    return lines.join('\n');
  }
  function liveEnsure(p) {
    if (!p.s) { p.s = liveId(); p.v = 0; p.h = ''; persist(); track('plan_live_new'); if ($('planDlg').open && !sharedPlan) renderPlan(); }
    livePush();  // se crea en el servidor mientras eliges con quién compartirlo
    return liveURL(p);
  }
  function sharePlan() {
    var url = liveEnsure(plan), text = planText(plan);
    track('plan_share');
    if (navigator.share) { navigator.share({ title: plan.n || tr('Mi plan'), text: text, url: url }).catch(function () {}); return; }
    window.open('https://wa.me/?text=' + encodeURIComponent(text + '\n\n' + tr('Ábrelo en Planika:') + ' ' + url), '_blank', 'noopener');
  }
  // Notas propias como citas del calendario: a su hora (1 h) o de todo el día
  function noteTimes(r) {
    var d = r.d.replace(/-/g, '');
    if (!r.t) return { allDay: true, start: d, end: addDays(r.d, 1).replace(/-/g, '') };
    var hh = +r.t.slice(0, 2) + 1, endDay = r.d;
    if (hh >= 24) { hh -= 24; endDay = addDays(r.d, 1); }
    return { allDay: false, start: d + 'T' + r.t.replace(':', '') + '00', end: endDay.replace(/-/g, '') + 'T' + pad(hh) + r.t.slice(3) + '00' };
  }
  function planEvent(r) { return Object.assign({}, r.e, { start: r.d, end: r.d, sessions: null, subtype: '' }); }  // el día elegido en el plan
  function noteDetails() { return tr('Nota de tu plan') + (plan.n ? ' «' + plan.n + '»' : '') + ' · Planika'; }
  function calRows() { return planRows(plan).filter(function (r) { return r.e || r.note != null; }); }
  // Todo el plan (planes de la agenda y notas) en un .ics: iPhone, Apple Calendar y Outlook lo añaden de una vez
  function planIcs() {
    var rows = calRows();
    if (!rows.length) { toast(tr('Añade algo a tu plan primero')); return; }
    var f = function (x) { return String(x).replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/[,;]/g, function (c) { return '\\' + c; }); };
    var stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    var all = rows.map(function (r) {
      if (r.e) { var t = icsText(planEvent(r)); return t.slice(t.indexOf('BEGIN:VEVENT'), t.indexOf('END:VCALENDAR')); }
      var nt = noteTimes(r);
      return ['BEGIN:VEVENT', 'UID:nota-' + r.d + '-' + (r.t || '').replace(':', '') + '-' + slug(r.note).slice(0, 30) + '@planikaapp.com', 'DTSTAMP:' + stamp,
        nt.allDay ? 'DTSTART;VALUE=DATE:' + nt.start : 'DTSTART;TZID=Europe/Madrid:' + nt.start,
        nt.allDay ? 'DTEND;VALUE=DATE:' + nt.end : 'DTEND;TZID=Europe/Madrid:' + nt.end,
        'SUMMARY:' + f(r.note), 'DESCRIPTION:' + f(noteDetails())].concat(icsAlarm(nt.allDay, f(r.note)), ['END:VEVENT', '']).join('\r\n');
    }).join('');
    var txt = 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Planika//planikaapp.com//ES\r\nCALSCALE:GREGORIAN\r\n' + all + 'END:VCALENDAR';
    var blob = new Blob([txt], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = ((plan.n || 'mi plan').replace(/[^\w\dáéíóúñü ]+/gi, '').trim() || 'mi_plan').replace(/\s+/g, '_') + '.ics';
    document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    track('plan_ics', { n: rows.length });
  }
  // «A mi calendario»: todo el plan de una vez (.ics) o, para Google Calendar, que no deja añadir varios a la vez,
  // un botón por plan y por nota
  function gcalNote(r) {
    var nt = noteTimes(r), enc = encodeURIComponent;
    return 'https://calendar.google.com/calendar/render?action=TEMPLATE&text=' + enc(r.note) + '&dates=' + nt.start + '/' + nt.end +
      '&details=' + enc(noteDetails()) + '&ctz=Europe/Madrid';
  }
  function renderPlanCal() {
    var rows = calRows(), box = $('planCal');
    if (!rows.length) { box.hidden = true; toast(tr('Añade algo a tu plan primero')); return; }
    need(rows.filter(function (r) { return r.e; }).map(function (r) { return r.e; }));
    var last = '', mobile = DEVICE !== 'desktop';
    // En el móvil, primero todo el plan de una vez (.ics); en el ordenador, primero Google Calendar
    var ics = '<div class="plan-cal-sec"><p class="plan-cal-h">📱 ' + tr('Todo el plan de una vez: iPhone, Android, Apple Calendar y Outlook') + '</p>' +
      '<button type="button" class="btn' + (mobile ? ' primary' : '') + '" data-plan-ics="1">📅 ' + tr('Descargar el plan (.ics)') + '</button>' +
      (DEVICE === 'android' ? '<p class="plan-cal-note">👉 ' + tr('En Android: abre el archivo descargado y elige Google Calendar') + '</p>' : '') +
      '<p class="plan-cal-note">🔔 ' + tr('Con aviso 2 horas antes de cada plan') + '</p></div>';
    var gcal = '<div class="plan-cal-sec"><p class="plan-cal-h">' + (mobile ? tr('O con Google Calendar, un toque por plan') : tr('Con Google Calendar, un toque por plan')) + '</p><div class="plan-gcal">' +
      rows.map(function (r) {
        var head = r.d !== last ? '<p class="plan-gcal-day">' + esc(cap(fmtDayName.format(fromIso(r.d)))) + '</p>' : '';
        last = r.d;
        var url = r.e ? links(planEvent(r)).google : gcalNote(r);
        var what = r.e ? title(r.e) : r.note;
        return head + '<a class="btn" href="' + esc(url) + '" target="_blank" rel="noopener" data-gcal="1">＋ ' + (r.t ? r.t + ' · ' : '') + esc(what) + '</a>';
      }).join('') + '</div></div>';
    box.innerHTML = mobile ? ics + gcal : gcal + ics;
    box.hidden = false;
    box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  $('planCal').addEventListener('click', function (ev) {
    if (ev.target.closest('[data-plan-ics]')) { planIcs(); track('plan_ics_' + DEVICE); return; }
    if (ev.target.closest('[data-gcal]')) track('plan_gcal');
  });
  // ---------- planes compartidos en vivo
  // Al compartir un plan se guarda en el servidor (Supabase, en la UE) con un id secreto que va en el enlace
  // (?plan=…): quien lo tenga lo ve y, si lo guarda, lo edita; los cambios les llegan a todos (se traen al abrir
  // Planika o volver a ella, al abrir Mis planes y cada 20 s con la ventana del plan abierta). Sin cuentas. Si dos
  // personas lo cambian a la vez, se queda el último cambio. Se borran 6 meses después del último cambio.
  var LIVE_API = 'https://rqjrrdtdscvcimwzrwxj.supabase.co/rest/v1/rpc/';
  var LIVE_KEY = 'sb_publishable_1gASlwY1wubC872dD5SJMw_4txaahRF';  // clave pública: solo llama a las funciones de planes compartidos
  var liveT = null, liveBusy = false, livePoll = null, lastPull = 0;
  function liveCall(fn, body) {
    return fetch(LIVE_API + fn, { method: 'POST', headers: { apikey: LIVE_KEY, 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (r) { if (!r.ok) { var e = new Error('live ' + r.status); e.status = r.status; throw e; } return r.json(); });
  }
  function liveBody(p) { return { n: p.n, i: p.i, o: p.o }; }
  function liveHash(p) {
    var s = JSON.stringify(liveBody(p)), h = 5381;
    for (var k = 0; k < s.length; k++) h = (h * 33 + s.charCodeAt(k)) | 0;
    return (h >>> 0).toString(36);
  }
  function liveId() {
    var b = new Uint8Array(16), s = '';
    crypto.getRandomValues(b);
    for (var k = 0; k < b.length; k++) s += String.fromCharCode(b[k]);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function liveURL(p) { return location.href.split('?')[0].split('#')[0] + '?plan=' + p.s; }
  function liveDirty(p) { return !!p.s && (!p.v || p.h !== liveHash(p)); }
  function liveSoon() { clearTimeout(liveT); if (store.p.some(liveDirty)) liveT = setTimeout(livePush, 1200); }
  function livePush() {
    var todo = store.p.filter(liveDirty);
    if (!todo.length) return Promise.resolve();
    if (liveBusy) { liveSoon(); return Promise.resolve(); }
    liveBusy = true;
    return Promise.all(todo.map(function (p) {
      var h = liveHash(p), body = liveBody(p);
      var req = p.v ? liveCall('shared_plan_save', { p_id: p.s, p_plan: body }) : liveCall('shared_plan_create', { p_id: p.s, p_plan: body });
      return req.then(function (rows) {
        if (!rows.length) { p.v = 0; return; }  // ya no estaba en el servidor (6 meses sin cambios): se vuelve a crear con el mismo enlace
        p.v = rows[0].plan_version; p.h = h;
      }, function (e) {
        if (!p.v && e.status === 409) p.v = 1;  // ya se había creado (se perdió la respuesta): la próxima vez se guarda
      });
    })).then(function () { liveBusy = false; persist(); if (store.p.some(function (p) { return liveDirty(p) && p.v; })) liveSoon(); });
  }
  function livePull() {
    var mine = store.p.filter(function (p) { return p.s && p.v; }).slice(0, 20);
    if (!mine.length || document.hidden) return Promise.resolve();
    lastPull = Date.now();
    return livePush().then(function () {
      return liveCall('shared_plan_get', { p_ids: mine.map(function (p) { return p.s; }) });
    }).then(function (rows) {
      var changed = [];
      rows.forEach(function (r) {
        var p = store.p.filter(function (x) { return x.s === r.plan_id; })[0];
        if (!p || liveDirty(p) || r.plan_version <= p.v) return;  // con cambios tuyos sin subir, se queda lo tuyo
        var q = cleanPlan(r.plan), ids = p.i.map(function (x) { return x[0]; });
        p.n = q.n; p.i = q.i; p.o = q.o; p.v = r.plan_version; p.h = liveHash(p);
        ids.concat(p.i.map(function (x) { return x[0]; })).forEach(syncPlanBtns);
        changed.push(p);
      });
      if (!changed.length) return;
      savePlan();
      if ($('planDlg').open && !sharedPlan) redraw();
      toast(tr('«{p}» se ha actualizado', { p: planTitle(changed[0]) }));
    }).catch(function () { /* sin conexión: se intentará más tarde */ });
  }
  function livePullSoon() { if (Date.now() - lastPull > 5000) livePull(); }
  function openLivePlan(s) {
    var mine = store.p.filter(function (p) { return p.s === s; })[0];
    if (mine) { openPlanId(mine.id); livePull(); return true; }
    liveCall('shared_plan_get', { p_ids: [s] }).then(function (rows) {
      if (!rows.length) { toast(tr('Ese plan compartido ya no existe')); return; }
      var q = cleanPlan(rows[0].plan);
      q.s = s; q.v = rows[0].plan_version; q.h = liveHash(q);
      sharedPlan = q; showMode('one'); renderPlan();
      track('plan_live_open');
    }).catch(function () { toast(tr('No se ha podido cargar el plan compartido. Prueba en un rato.')); });
    return true;
  }
  document.addEventListener('visibilitychange', function () { if (document.hidden) livePush(); else livePullSoon(); });
  window.addEventListener('online', function () { livePush().then(livePull); });

  // ?miplan=… (plan compartido: se enseña y se puede guardar como uno más) y ?add=<id> (botón «＋ Mi plan» de las fichas)
  function openSharedPlan(b64) {
    try {
      var b = b64.replace(/-/g, '+').replace(/_/g, '/');
      var q = cleanPlan(JSON.parse(decodeURIComponent(escape(atob(b))))), mine = samePlan(q);
      if (mine) openPlanId(mine.id);
      else { sharedPlan = q; showMode('one'); renderPlan(); }
      track('plan_shared_open');
      return true;
    } catch (e) { toast(tr('Ese enlace de plan no se puede leer')); return false; }
  }
  // Enlace de Planika que te mandan (WhatsApp…): plan compartido (?miplan=), ficha de un plan (/e/…-<id>.html) o
  // «＋ Mi plan» (?add=). La app de la pantalla de inicio del iPhone no comparte datos con Safari, y los enlaces se
  // abren en Safari: por eso se pueden pegar en «Mis planes». En Android llegan también con «Compartir» (share_target).
  function sharedLink(text) {
    var urls = String(text || '').match(/https?:\/\/[^\s<>"']+/g) || [];
    for (var i = 0; i < urls.length; i++) {
      var u;
      try { u = new URL(urls[i]); } catch (e) { continue; }
      if (!/(^|\.)planikaapp\.com$|^localhost$|^127\.0\.0\.1$/.test(u.hostname)) continue;
      if (/^[A-Za-z0-9_-]{22}$/.test(u.searchParams.get('plan') || '')) return { live: u.searchParams.get('plan') };
      if (u.searchParams.get('miplan')) return { miplan: u.searchParams.get('miplan') };
      if (u.searchParams.get('add')) return { add: u.searchParams.get('add') };
      var f = u.pathname.match(/\/e\/(?:[^\/]*-)?([A-Za-z0-9_]+)\.html$/);
      if (f) return { add: f[1] };
    }
    return null;
  }
  function openShared(l) {
    if (l.live) return openLivePlan(l.live);
    if (l.miplan) return openSharedPlan(l.miplan);
    if (BY_ID[l.add]) { togglePlanAdd(l.add); return true; }
    toast(tr('Este plan ya no está en la agenda'));
    return false;
  }
  function planFromURL() {
    var p = new URLSearchParams(PLAN_Q);
    if (/^[A-Za-z0-9_-]{22}$/.test(p.get('plan') || '')) openLivePlan(p.get('plan'));
    if (p.get('miplan')) openSharedPlan(p.get('miplan'));
    if (p.get('add') && BY_ID[p.get('add')]) togglePlanAdd(p.get('add'));
    if (p.get('su') || p.get('sx')) {  // Android: «Compartir» → Planika
      var l = sharedLink([p.get('su'), p.get('sx'), p.get('st')].join(' '));
      if (l) { track('plan_share_target'); openShared(l); } else toast(tr('Ese enlace no es de un plan de Planika'));
    }
  }
  // En Safari del iPhone, si se llega con un enlace de plan: aviso para llevarlo a la app de la pantalla de inicio
  var FROM_LINK = ios && !standalone && /[?&](miplan|add|plan)=/.test(PLAN_Q);
  function linkToCopy() { return location.origin + location.pathname + PLAN_Q; }
  $('planAppCopy').addEventListener('click', function () { copy(linkToCopy(), tr('Enlace copiado')); track('plan_app_hint_copy'); });
  $('plansPaste').addEventListener('click', function () {
    var show = function () { $('plansPasteForm').hidden = false; $('plansPasteErr').hidden = true; $('plansPasteInput').focus(); };
    if (navigator.clipboard && navigator.clipboard.readText) {
      navigator.clipboard.readText().then(function (t) {
        var l = sharedLink(t);
        if (l) { track('plan_paste', { how: 'clipboard' }); openShared(l); } else show();
      }, show);
    } else show();
  });
  $('plansPasteForm').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var l = sharedLink($('plansPasteInput').value);
    if (!l) { $('plansPasteErr').hidden = false; $('plansPasteInput').focus(); return; }
    $('plansPasteInput').value = ''; $('plansPasteForm').hidden = true;
    track('plan_paste', { how: 'field' });
    openShared(l);
  });
  // Desde la ficha se viene a añadir: si ya está en tu plan, no se quita, se abre
  function togglePlanAdd(id) {
    var live = livePlans();
    if (live.length > 1) { openPick(id, true); return; }
    var p = live[0];
    if (!p) { if (!makeRoom()) return; p = addPlan(cleanPlan(null)); }
    if (!has(p, id)) { setActive(p); addTo(p, id); savePlan(); syncPlanBtns(id); track('plan_add'); }
    openPlanId(p.id);
  }
  $('planPill').addEventListener('click', openPlan);
  $('planClose').addEventListener('click', function () { $('planDlg').close(); });
  $('planDlg').addEventListener('click', function (ev) { if (ev.target === $('planDlg')) $('planDlg').close(); });
  $('planDlg').addEventListener('close', function () { sharedPlan = null; savePlan(); });
  $('planName').addEventListener('input', function () { if (!sharedPlan && plan) { plan.n = this.value.slice(0, 60); savePlan(); } });
  $('planList').addEventListener('click', function (ev) {
    var d = ev.target.closest('[data-plan-del]');
    if (d) { var id = d.dataset.planDel; plan.i = plan.i.filter(function (x) { return x[0] !== id; }); savePlan(); syncPlanBtns(id); renderPlan(); return; }
    var n = ev.target.closest('[data-plan-note]');
    if (n) { plan.o.splice(+n.dataset.planNote, 1); savePlan(); renderPlan(); }
  });
  $('planNoteForm').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var x = $('planNoteText').value.trim();
    if (!x) { $('planNoteText').focus(); return; }
    plan.o.push({ d: $('planNoteDay').value || planDays()[0] || TODAY, t: $('planNoteTime').value || '', x: x.slice(0, 80) });
    $('planNoteText').value = ''; $('planNoteTime').value = '';
    savePlan(); renderPlan();
  });
  $('planShare').addEventListener('click', sharePlan);
  $('planCopy').addEventListener('click', function () { copy(liveEnsure(plan), tr('Enlace de tu plan copiado')); });
  $('planIcs').addEventListener('click', function () { if (!$('planCal').hidden) { $('planCal').hidden = true; return; } renderPlanCal(); track('plan_cal_open'); });
  $('planAdd').addEventListener('click', function () { $('planDlg').close(); setView('list'); window.scrollTo({ top: $('list').offsetTop - 80, behavior: 'smooth' }); });
  $('planMap').addEventListener('click', function () {
    $('planDlg').close(); state.planOnly = true; setView('map');
    toast(store.p.length > 1 ? tr('En el mapa solo salen los planes de «{p}»', { p: planTitle(plan) }) : tr('En el mapa solo salen los planes de tu plan'));
    window.scrollTo({ top: $('mapView').offsetTop - 80, behavior: 'smooth' });
  });
  $('planDup').addEventListener('click', function () {
    if (!plan || !makeRoom()) return;
    var p = cleanPlan(JSON.parse(JSON.stringify(plan)));
    p.id = newId(); p.n = tr('{p} (copia)', { p: plan.n || tr('Mi plan') }).slice(0, 60);
    delete p.s; delete p.v; delete p.h;
    addPlan(p); p.i.forEach(function (x) { syncPlanBtns(x[0]); });
    track('plan_dup');
    openPlanId(p.id, true);
  });
  $('planDel').addEventListener('click', function () {
    var p = plan;
    if (!p || ((planSize(p) || p.s) && !confirm(p.s ? tr('¿Borrar «{p}» de tu móvil? Quien tenga el enlace lo seguirá teniendo.', { p: planTitle(p) })
      : tr('¿Borrar el plan «{p}»?', { p: planTitle(p) })))) return;
    store.p = store.p.filter(function (x) { return x !== p; });
    setActive(sortPlans(livePlans())[0] || null);
    if (state.planOnly) { state.planOnly = false; refresh(); }
    savePlan(); p.i.forEach(function (x) { syncPlanBtns(x[0]); });
    track('plan_delete');
    openPlans();
  });
  $('planSave').addEventListener('click', function () {
    if (!sharedPlan) return;
    var p = samePlan(sharedPlan);
    if (!p) {
      if (!makeRoom()) return;
      p = addPlan(cleanPlan(sharedPlan)); p.id = newId();
      track(p.s ? 'plan_live_save' : 'plan_shared_save');
    }
    openPlanId(p.id); p.i.forEach(function (x) { syncPlanBtns(x[0]); });
    toast(tr('Guardado en Mis planes'));
  });
  savePlan();

  // ---------- arranque
  var openId = readURL();
  window.PLANIKA_D = applyChunk;
  (window.PLANIKA_Q || []).forEach(function (a) { applyChunk(a[0], a[1], a[2]); });
  window.PLANIKA_Q = [];
  populate();
  if (state.days.length) { syncQuick(); state.month = fromIso(state.days[0]); refresh(); }
  else if (state.from || state.to) { clearQuick(); refresh(); } else setRange('all');
  if (advCount()) $('adv').open = true;
  if (state.view !== 'list') setView(state.view);
  if (openId) openModal(openId);
  planFromURL();
  livePull();  // planes compartidos en vivo: trae lo que hayan cambiado los demás
})();
