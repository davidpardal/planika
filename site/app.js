/* Planika: filtros, lista, calendario, mapa, favoritos, compartir y "añadir al calendario". */
(function () {
  'use strict';
  // Los datos llegan en dos partes: data/core.js (lo justo para filtrar, ordenar, calendario y mapa) y
  // data/d/<n>.js (descripción, enlaces e imagen, en bloques que se piden solo cuando hay que pintar esas tarjetas).
  var DATA = window.PLANES_CORE || { events: [], categories: [], provinces: [], sources: [], srcNames: [], chunk: 250, v: '' };
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
      lat: r[10] == null ? null : r[10], lon: r[11] == null ? null : r[11], price: r[12] || '', free: !!(r[13] & 1), tk: !!(r[13] & 2), xm: !!(r[13] & 4),
      audience: r[14] || '', source: DATA.srcNames[r[15]] || '', sessions: r[16] || null, title_es: r[17] || '',
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
                favs: false, geo: null, radius: 25, view: 'list', shown: PAGE, month: null, selDay: null };
  var favSet = loadFavs();

  // ---------- utilidades
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoDate(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function fromIso(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function addDays(s, n) { var d = fromIso(s); d.setDate(d.getDate() + n); return isoDate(d); }
  var TODAY = isoDate(new Date());
  var thisYear = TODAY.slice(0, 4);
  var fmtDay = new Intl.DateTimeFormat('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
  var fmtShort = new Intl.DateTimeFormat('es-ES', { day: 'numeric', month: 'short' });
  var fmtLong = new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  var fmtMonth = new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric' });
  function fmtD(s) { return fmtDay.format(fromIso(s)) + (s.slice(0, 4) !== thisYear ? ' ' + s.slice(0, 4) : ''); }
  function spanDays(e) { return Math.round((fromIso(e.end) - fromIso(e.start)) / 864e5); }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
  function slug(s) { return norm(s).replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''); }
  function title(e) { return e.title_es || e.title; }
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
    for (var i = 0; i < e.sessions.length; i++) if (e.sessions[i] >= from) return e.sessions[i];
    return e.sessions[e.sessions.length - 1];
  }
  function isPermanent(e) { return e.subtype === 'Permanente'; }
  function whenText(e) {
    if (isPermanent(e)) return 'Visita permanente';
    if (e.sessions) {
      var n = nextSession(e); var rest = e.sessions.filter(function (d) { return d > n; }).length;
      return fmtD(n) + (e.time ? ' · ' + e.time : '') + (rest ? ' (+' + rest + ' fechas)' : '');
    }
    if (e.end !== e.start && e.start < TODAY) return 'Hasta el ' + fmtD(e.end) + (e.time ? ' · ' + e.time : '');
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
  function toast(msg) { var t = $('toast'); t.textContent = msg; t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(function () { t.hidden = true; }, 2600); }
  function loadFavs() { try { return new Set(JSON.parse(localStorage.getItem('planika_favs') || '[]')); } catch (e) { return new Set(); } }
  function saveFavs() { try { localStorage.setItem('planika_favs', JSON.stringify(Array.from(favSet))); } catch (e) { /* sin almacenamiento */ } $('favCount').textContent = favSet.size ? favSet.size : ''; }

  // ---------- estado en la URL (enlaces compartibles con filtros)
  function readURL() {
    var p = new URLSearchParams(location.search);
    state.q = p.get('q') || ''; state.ccaa = p.get('ccaa') || ''; state.prov = p.get('prov') || ''; state.city = p.get('city') || '';
    state.from = p.get('from') || ''; state.to = p.get('to') || ''; state.free = p.get('free') === '1'; state.tickets = p.get('tickets') === '1';
    state.tod = p.get('tod') || ''; state.aud = p.get('aud') || ''; state.pmax = p.get('pmax') || ''; state.favs = p.get('favs') === '1';
    (p.get('cat') || '').split(',').filter(Boolean).forEach(function (c) { state.cats[c] = true; });
    if (p.get('view')) state.view = p.get('view');
    return p.get('e');
  }
  function writeURL() {
    var p = new URLSearchParams();
    if (state.q) p.set('q', state.q); if (state.ccaa) p.set('ccaa', state.ccaa); if (state.prov) p.set('prov', state.prov); if (state.city) p.set('city', state.city);
    if (state.from) p.set('from', state.from); if (state.to) p.set('to', state.to); if (state.free) p.set('free', '1'); if (state.tickets) p.set('tickets', '1');
    if (state.tod) p.set('tod', state.tod); if (state.aud) p.set('aud', state.aud); if (state.pmax) p.set('pmax', state.pmax); if (state.favs) p.set('favs', '1');
    var cats = Object.keys(state.cats).filter(function (k) { return state.cats[k]; }); if (cats.length) p.set('cat', cats.join(','));
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
      a.insertAdjacentHTML('beforeend', ' <small>' + n.toLocaleString('es-ES') + '</small>');
    });
    var chips = $('cats');
    DATA.categories.forEach(function (c) {
      var n = EVENTS.filter(function (e) { return e.category === c.key || (c.key === 'navidad' && e.xm); }).length;
      if (!n) return;
      var b = document.createElement('button'); b.type = 'button'; b.className = 'chip' + (state.cats[c.key] ? ' on' : ''); b.dataset.cat = c.key;
      b.innerHTML = c.icon + ' ' + esc(c.name) + ' <small>' + n + '</small>';
      b.addEventListener('click', function () { state.cats[c.key] = !state.cats[c.key]; b.classList.toggle('on', !!state.cats[c.key]); refresh(); });
      chips.appendChild(b);
    });
    $('meta').textContent = 'Actualizado el ' + (DATA.updated_at || '').replace('T', ' a las ') + ' · ' + EVENTS.length.toLocaleString('es-ES') + ' planes del ' + fmtDay.format(fromIso(DATA.from)) + ' al ' + fmtDay.format(fromIso(DATA.to));
    var pc = provCounts();
    $('seoLinks').innerHTML = DATA.provinces.filter(function (p) { return pc[p.code]; }).sort(function (a, b) { return a.name.localeCompare(b.name, 'es'); })
      .map(function (p) { return '<a href="p/' + slug(p.name) + '.html">' + esc(p.name) + '</a>'; }).join(' · ') + '<br>' +
      DATA.categories.map(function (c) { return '<a href="t/' + c.key + '.html">' + c.icon + ' ' + esc(c.name) + '</a>'; }).join(' · ');
    $('q').value = state.q; $('from').value = state.from; $('to').value = state.to; $('free').checked = state.free; $('tickets').checked = state.tickets;
    $('tod').value = state.tod; $('aud').value = state.aud; $('pmax').value = state.pmax; $('favs').checked = state.favs; $('radius').value = String(state.radius);
    saveFavs();
  }
  function fillProvinces() {
    var pc = provCounts(); var sel = $('prov'); var cur = state.prov;
    sel.innerHTML = '<option value="">Todas</option>';
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
      if (provs.length > 1) list.push({ t: 'c', v: c, name: c, kind: 'Comunidad', n: ccaas[c] });
    });
    DATA.provinces.forEach(function (p) { if (pc[p.code]) list.push({ t: 'p', v: p.code, name: p.name, kind: 'Provincia', n: pc[p.code] }); });
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
      list.push({ t: 'l', v: name, prov: c.prov, name: name, kind: 'en ' + ((PROV[c.prov] || {}).name || ''), n: c.n });
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
    SUGG = m === null ? [{ t: 'all', name: 'Toda España', kind: 'Sin filtro de lugar', n: EVENTS.length }]
      .concat(PLACES.filter(function (p) { return p.t !== 'c'; }).slice(0, 8)) : m;
    ACTIVE = m && m.length ? 0 : -1;
    ul.innerHTML = SUGG.length ? SUGG.map(function (p, i) {
      return '<li role="option" id="wh' + i + '" data-i="' + i + '" aria-selected="' + (i === ACTIVE) + '">' +
        '<span>' + boldPrefix(p.name, text) + '</span><span class="k">' + esc(p.kind) + ' · ' + p.n.toLocaleString('es-ES') + '</span></li>';
    }).join('') : '<li class="none">Ningún lugar con planes empieza por «' + esc(text.trim()) + '»</li>';
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
    sel.innerHTML = '<option value="">Todas</option>';
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
    keys.forEach(function (c) { var o = document.createElement('option'); o.value = c.name; o.textContent = c.name + ' (' + c.n.toLocaleString('es-ES') + ')'; sel.appendChild(o); });
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
    return !!(state.q || state.ccaa || state.prov || state.city || state.free || anyCat() || advCount() || (!quickAll && (state.from || state.to)));
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
    $('count').innerHTML = '<strong>' + n.toLocaleString('es-ES') + '</strong> ' + (n === 1 ? 'plan' : 'planes') +
      (small ? ' <small>' + esc(small) + '</small>' : '');
    var ctx = filterSummary(); if (extra) ctx = ctx ? ctx + ' · ' + extra : extra;
    $('countCtx').textContent = ctx;
  }
  function filterSummary() {
    var parts = [];
    if (state.q) parts.push('«' + state.q + '»');
    var catNames = {}; DATA.categories.forEach(function (c) { catNames[c.key] = c.name; });
    var cats = Object.keys(state.cats).filter(function (k) { return state.cats[k]; }).map(function (k) { return catNames[k] || k; });
    if (state.free) parts.push('Gratis');
    parts = parts.concat(cats);
    var where = 'toda España';
    if (state.prov) { var pv = DATA.provinces.filter(function (p) { return p.code === state.prov; })[0]; if (pv) where = pv.name; }
    if (state.city) where = state.city + (where !== 'toda España' && where !== state.city ? ' (' + where + ')' : '');
    else if (state.ccaa) where = state.ccaa;
    parts.push((parts.length ? 'en ' : 'En ') + where);
    var q = $('quick').querySelector('button.on');
    var labels = { today: 'hoy', weekend: 'este fin de semana', '7': 'en los próximos 7 días', '30': 'en los próximos 30 días' };
    if (q && labels[q.dataset.range]) parts.push(labels[q.dataset.range]);
    else if (!q && (state.from || state.to)) {
      parts.push((state.from ? 'del ' + fmtDay.format(fromIso(state.from)) : 'desde hoy') + (state.to ? ' al ' + fmtDay.format(fromIso(state.to)) : ''));
    }
    var tod = { manana: 'por la mañana', tarde: 'por la tarde', noche: 'por la noche' }[state.tod]; if (tod) parts.push(tod);
    if (state.aud === 'familiar') parts.push('infantil y familiar'); else if (state.aud === 'adultos') parts.push('para adultos');
    if (state.pmax) parts.push('hasta ' + state.pmax + ' €');
    if (state.tickets) parts.push('con venta de entradas');
    if (state.geo) parts.push('a menos de ' + state.radius + ' km');
    if (state.favs) parts.push('solo favoritos');
    return parts.join(' · ');
  }
  function anyCat() { for (var k in state.cats) if (state.cats[k]) return true; return false; }
  function inDates(e) {
    // Sin un día concreto: se pueden visitar dentro de cualquier filtro de fechas.
    if (isPermanent(e)) return true;
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
    var s = nextSession(e);
    return (s > from ? s : from) + '|' + pad(Math.min(99, e.sessions ? 0 : spanDays(e))) + '|' + (e.time || '99');
  }
  function sorted(list) {
    if (state.geo) return list.slice().sort(function (a, b) { return dist(a) - dist(b); });
    return list.map(function (e) { return [sortKey(e), e]; }).sort(function (a, b) { return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0; }).map(function (x) { return x[1]; });
  }

  // ---------- tarjetas
  // Color pop de la tarjeta (amarillo, rosa, turquesa, lila): rota por posición en la lista.
  function popOf(id) { var h = 0, s = String(id); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h % 4; }
  function card(e, opts) {
    opts = opts || {};
    var pop = opts.i != null ? opts.i % 4 : popOf(e.id);
    var c = CATS[e.category] || { icon: '✨', name: 'Otros' };
    var ongoing = !e.sessions && !isPermanent(e) && e.start < TODAY && e.end >= TODAY;
    var permBadge = isPermanent(e) ? '<span class="badge">Permanente</span>' : '';
    var img = e.image ? '<img src="' + esc(e.image) + '" alt="" loading="lazy" onerror="this.remove()">' : '';
    var where = [e.venue, e.city, e.province && e.province !== e.city ? e.province : ''].filter(Boolean).join(' · ');
    var price = e.free ? '<span class="badge free">Gratis</span>' : (e.price ? '<span class="badge">' + esc(e.price) + '</span>' : '');
    var tickets = e.tickets_url ? '<a class="btn primary" href="' + esc(e.tickets_url) + '" target="_blank" rel="noopener">🎫 Entradas</a>' : '';
    var info = e.url && e.url !== e.tickets_url ? '<a class="btn" href="' + esc(e.url) + '" target="_blank" rel="noopener">Más info ↗</a>' : '';
    var d = dist(e);
    var sess = '';
    if (e.sessions) {
      var up = e.sessions.filter(function (x) { return x >= TODAY; });
      sess = '<div class="sessions">Fechas: ' + up.slice(0, 6).map(function (x) { return fmtShort.format(fromIso(x)); }).join(', ') + (up.length > 6 ? ' y ' + (up.length - 6) + ' más' : '') + '</div>';
    }
    var fav = '<button type="button" class="fav corner' + (favSet.has(e.id) ? ' on' : '') + '" data-fav="' + e.id + '" title="Guardar en favoritos" aria-label="Guardar en favoritos">' + (favSet.has(e.id) ? '★' : '☆') + '</button>';
    return '<article class="card pop' + pop + '" data-id="' + e.id + '" data-c="' + Math.floor(e.i / CHUNK) + '" data-pop="' + pop + '"' + (opts.noOngoing ? ' data-no="1"' : '') + '>' + fav + img + '<div class="body">' +
      '<div class="badges"><span class="badge">' + c.icon + ' ' + esc(c.name) + '</span>' + price + permBadge + (ongoing && !opts.noOngoing ? '<span class="badge ongoing">En curso</span>' : '') + (d !== null ? '<span class="badge dist">a ' + (d < 10 ? d.toFixed(1) : Math.round(d)) + ' km</span>' : '') + '</div>' +
      // El título lleva a la ficha del plan en Planika (enlace rastreable); la web oficial sigue en "Entradas" y "Más info".
      '<h3><a href="' + esc(evFile(e)) + '">' + esc(title(e)) + '</a></h3>' +
      (e.title_es ? '<div class="where">' + esc(e.title) + '</div>' : '') +
      '<div class="when">📅 ' + esc(whenText(e)) + '</div>' + sess +
      (where ? '<div class="where">📍 ' + esc(where) + '</div>' : '') +
      (e.description ? '<p class="desc">' + esc(e.description) + '</p>' : '') +
      '<div class="actions">' + tickets + info + '<button type="button" class="btn addcal" data-id="' + e.id + '">＋ Calendario</button>' +
      '<button type="button" class="btn share" data-share="' + e.id + '" title="Compartir este plan">↗ Compartir</button></div>' +
      ((e.source || (e.subtype && !isPermanent(e))) ? '<div class="src">' + (e.source ? 'Fuente: ' + esc(e.source) : '') + (e.subtype && !isPermanent(e) ? (e.source ? ' · ' : '') + esc(e.subtype) : '') + '</div>' : '') +
      '</div></article>';
  }
  function renderList() {
    var list = sorted(filtered());
    var el = $('list');
    setCount(list.length, list.length !== EVENTS.length ? 'de ' + EVENTS.length.toLocaleString('es-ES') : '', '');
    if (!list.length) { el.innerHTML = '<div class="empty">No hay planes con esos filtros. Prueba a ampliar las fechas o quitar algún filtro.</div>'; $('more').hidden = true; return; }
    var page = list.slice(0, state.shown);
    need(page);
    el.innerHTML = page.map(function (e, i) { return card(e, { i: i }); }).join('');
    $('more').hidden = state.shown >= list.length;
    $('more').textContent = 'Mostrar más (' + Math.min(PAGE, list.length - state.shown) + ' de ' + (list.length - state.shown) + ' restantes)';
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
      html += '<button type="button" class="day' + (out ? ' out' : '') + (s || o ? ' has' : '') + (ds === TODAY ? ' today' : '') + (ds === state.selDay ? ' sel' : '') + '" data-day="' + ds + '"' + (out ? ' tabindex="-1"' : '') + '>' +
        '<span class="n">' + cur.getDate() + '</span>' + (s ? '<span class="starts">' + s + '</span>' : '') + (o ? '<span class="ongoing">+' + o + ' en curso</span>' : '') + '</button>';
      cur.setDate(cur.getDate() + 1);
      if (i === 34 && cur.getMonth() !== m.getMonth()) break;
    }
    $('calGrid').innerHTML = html;
    renderDay();
  }
  function onDay(e, d) {
    if (isPermanent(e)) return false;
    return e.sessions ? e.sessions.indexOf(d) >= 0 : (e.start <= d && e.end >= d);
  }
  function renderDay() {
    var p = $('dayPanel');
    if (!state.selDay) { p.hidden = true; return; }
    var d = state.selDay;
    var list = filtered(true).filter(function (e) { return onDay(e, d); });
    var st = sorted(list.filter(function (e) { return e.sessions || e.start === d; }));
    var on = list.filter(function (e) { return !e.sessions && e.start !== d && spanDays(e) <= LONG_DAYS; }).sort(function (a, b) { return a.end < b.end ? -1 : 1; });
    var longOnes = list.length - st.length - on.length;
    var h = '<h3>' + cap(fmtLong.format(fromIso(d))) + ' · ' + (st.length + on.length) + ' planes</h3>';
    if (!st.length && !on.length) h += '<p class="empty">Nada registrado ese día con los filtros actuales.</p>';
    if (st.length) h += '<h4>Este día (' + st.length + ')</h4><div class="mini">' + st.slice(0, 120).map(function (e, i) { return card(e, { noOngoing: true, i: i }); }).join('') + (st.length > 120 ? '<p class="empty">… y ' + (st.length - 120) + ' más. Afina los filtros o usa la vista de lista.</p>' : '') + '</div>';
    if (on.length) h += '<h4>En curso (' + on.length + ')</h4><div class="mini">' + on.slice(0, 60).map(function (e, i) { return card(e, { noOngoing: true, i: i + 2 }); }).join('') + (on.length > 60 ? '<p class="empty">… y ' + (on.length - 60) + ' más. Usa la vista de lista para verlos todos.</p>' : '') + '</div>';
    if (longOnes > 0) h += '<p class="hint">Además hay ' + longOnes + ' planes de larga duración activos ese día (exposiciones, temporadas…) que no se cuentan en el calendario. <button type="button" class="linklike" data-golist="' + d + '">Verlos en la lista</button></p>';
    need(st.slice(0, 120)); need(on.slice(0, 60));
    p.innerHTML = h; p.hidden = false;
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
      $('map').innerHTML = '<p class="empty">Cargando el mapa…</p>'; renderCoverage(); return;
    }
    if (!ensureMap()) { $('map').innerHTML = '<p class="empty">El mapa no ha podido cargarse (sin conexión a la librería de mapas).</p>'; renderCoverage(); return; }
    var list = filtered();
    cluster.clearLayers();
    var markers = [];
    list.forEach(function (e) {
      if (e.lat == null || e.lon == null) return;
      var mk = L.marker([e.lat, e.lon]);
      mk.bindPopup('<strong>' + esc(title(e)) + '</strong><br>' + esc(whenText(e)) + '<br>' + esc([e.venue, e.city].filter(Boolean).join(' · ')) + '<br><a href="#" data-open="' + e.id + '">Ver ficha</a>');
      markers.push(mk);
    });
    cluster.addLayers(markers);
    if (state.geo) {
      if (youMarker) map.removeLayer(youMarker);
      youMarker = L.circleMarker([state.geo.lat, state.geo.lon], { radius: 8, color: '#2563eb', fillOpacity: .8 }).addTo(map).bindPopup('Tu ubicación');
      map.setView([state.geo.lat, state.geo.lon], state.radius <= 10 ? 12 : state.radius <= 25 ? 11 : state.radius <= 50 ? 10 : 9);
    } else if (state.prov && CENTROIDS[state.prov]) {
      map.setView(CENTROIDS[state.prov], 9);
    }
    setCount(markers.length, 'en el mapa', 'De ' + list.length.toLocaleString('es-ES') + ', solo los que tienen ubicación');
    setTimeout(function () { map.invalidateSize(); }, 50);
    renderCoverage();
  }
  function renderCoverage() {
    var counts = {}; var max = 1;
    EVENTS.forEach(function (e) { if (matches(e) && e.province_code) { counts[e.province_code] = (counts[e.province_code] || 0) + 1; } });
    DATA.provinces.forEach(function (p) { if ((counts[p.code] || 0) > max) max = counts[p.code]; });
    $('coverage').innerHTML = DATA.provinces.slice().sort(function (a, b) { return (counts[b.code] || 0) - (counts[a.code] || 0) || a.name.localeCompare(b.name, 'es'); })
      .map(function (p) { var n = counts[p.code] || 0; return '<div class="row' + (n ? '' : ' zero') + '"><span>' + esc(p.name) + '</span><span class="bar"><i style="width:' + Math.round(100 * n / max) + '%"></i></span><span class="n">' + (n ? n.toLocaleString('es-ES') : 'sin datos') + '</span></div>'; }).join('');
  }

  // ---------- ficha (modal) y compartir
  function openModal(id) {
    var e = BY_ID[id];
    if (!e) { toast('Ese plan ya no está en la agenda'); return; }
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
    copy(url, 'Enlace del plan copiado');
  }
  function copy(text, msg) {
    if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () { toast(msg); }, function () { prompt('Copia el enlace:', text); });
    else prompt('Copia el enlace:', text);
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
    if (isPermanent(e)) parts.push('Visita permanente, sin una fecha única. Este aviso es un recordatorio de un día.');
    if (e.description) parts.push(e.description);
    if (e.sessions) parts.push('Otras fechas: ' + e.sessions.join(', '));
    if (e.price) parts.push('Precio: ' + e.price); else if (e.free) parts.push('Entrada gratuita');
    if (e.tickets_url) parts.push('Entradas: ' + e.tickets_url);
    if (e.url && e.url !== e.tickets_url) parts.push('Más información: ' + e.url);
    parts.push((e.source ? 'Fuente: ' + e.source + ' · ' : '') + 'vía Planika');
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
  function openMenu(btn, e) {
    var l = links(e);
    menu.innerHTML = '<a href="' + l.google + '" target="_blank" rel="noopener">Google Calendar</a>' +
      '<button type="button" data-act="ics">Apple Calendar / iCal (.ics)</button>' +
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
    if (b) { ev.stopPropagation(); var e = byId(b.dataset.id); if (e && !e._d) { need([e]); toast('Cargando el plan… vuelve a pulsar en un momento'); return; } if (e) openMenu(b, e); return; }
    if (!ev.target.closest('#menu')) closeMenu();
    var f = ev.target.closest('[data-fav]');
    if (f) { var id = f.dataset.fav; if (favSet.has(id)) favSet.delete(id); else favSet.add(id); saveFavs();
      document.querySelectorAll('[data-fav="' + id + '"]').forEach(function (x) { x.classList.toggle('on', favSet.has(id)); x.textContent = favSet.has(id) ? '★' : '☆'; });
      favChanged(id, favSet.has(id));
      if (state.favs) refresh(); return; }
    var s = ev.target.closest('[data-share]');
    if (s) { var e2 = byId(s.dataset.share); if (e2) shareLink(e2); return; }
    var o = ev.target.closest('[data-open]');
    if (o) { ev.preventDefault(); openModal(o.dataset.open); return; }
    var gl = ev.target.closest('[data-golist]');
    if (gl) { state.from = gl.dataset.golist; state.to = gl.dataset.golist; $('from').value = state.from; $('to').value = state.to; $('quick').querySelectorAll('button').forEach(function (x) { x.classList.remove('on'); }); setView('list'); window.scrollTo({ top: $('list').offsetTop - 80, behavior: 'smooth' }); return; }
    var d = ev.target.closest('.day');
    if (d && !d.classList.contains('out')) { state.selDay = state.selDay === d.dataset.day ? null : d.dataset.day; renderCalendar(); }
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
    state.q = ''; state.ccaa = ''; state.prov = ''; state.city = ''; state.free = false; state.tickets = false; state.cats = {};
    state.tod = ''; state.aud = ''; state.pmax = ''; state.favs = false;
    if (state.geo) { state.geo = null; $('geoBtn').textContent = '📍 Activar'; $('geoBtn').classList.remove('on'); }
    $('q').value = ''; $('ccaa').value = ''; fillProvinces(); syncWhere(); fillCities(); $('free').checked = false; $('tickets').checked = false;
    $('tod').value = ''; $('aud').value = ''; $('pmax').value = ''; $('favs').checked = false;
    setRange('all');
  });
  $('prov').addEventListener('change', function () { state.prov = this.value; refresh(); });
  $('from').addEventListener('change', function () { state.from = this.value; clearQuick(); refresh(); });
  $('to').addEventListener('change', function () { state.to = this.value; clearQuick(); refresh(); });
  ['free', 'tickets', 'favs'].forEach(function (id) { $(id).addEventListener('change', function () { state[id] = this.checked; refresh(); }); });
  ['tod', 'aud', 'pmax'].forEach(function (id) { $(id).addEventListener('change', function () { state[id] = this.value; refresh(); }); });
  $('pmax').addEventListener('input', function () { clearTimeout(qt); var v = this.value; qt = setTimeout(function () { state.pmax = v; refresh(); }, 300); });
  $('radius').addEventListener('change', function () { state.radius = +this.value; if (state.geo) refresh(); });
  $('geoBtn').addEventListener('click', function () {
    if (state.geo) { state.geo = null; this.textContent = '📍 Activar'; this.classList.remove('on'); refresh(); return; }
    if (!navigator.geolocation) { toast('Tu navegador no permite obtener la ubicación'); return; }
    var btn = this; btn.textContent = '⏳ Buscando…';
    navigator.geolocation.getCurrentPosition(function (pos) {
      state.geo = { lat: pos.coords.latitude, lon: pos.coords.longitude }; btn.textContent = '📍 Activado'; btn.classList.add('on'); refresh();
    }, function () { btn.textContent = '📍 Activar'; toast('No se ha podido obtener tu ubicación'); }, { timeout: 10000, maximumAge: 300000 });
  });
  $('quick').addEventListener('click', function (ev) {
    var b = ev.target.closest('button'); if (!b) return;
    if (b.dataset.range === 'dates') { $('adv').open = true; $('from').focus(); return; }
    setRange(b.dataset.range);
  });
  $('view').addEventListener('click', function (ev) { var b = ev.target.closest('button'); if (b) setView(b.dataset.view); });
  $('more').addEventListener('click', function () { state.shown += PAGE; renderList(); });
  $('prevM').addEventListener('click', function () { state.month = new Date(state.month.getFullYear(), state.month.getMonth() - 1, 1); state.selDay = null; renderCalendar(); });
  $('nextM').addEventListener('click', function () { state.month = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 1); state.selDay = null; renderCalendar(); });
  $('todayM').addEventListener('click', function () { state.month = fromIso(TODAY); state.selDay = TODAY; renderCalendar(); });

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
  window.addEventListener('appinstalled', function () { $('installWrap').hidden = true; track('pwa_installed'); toast('¡Planika instalada! Ya la tienes en tu pantalla de inicio'); });
  function netState() { $('offline').hidden = navigator.onLine !== false; }
  window.addEventListener('online', netState); window.addEventListener('offline', netState); netState();
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js').catch(function () { /* sin service worker */ }); });
  }

  // ---------- cuentas (opcionales): favoritos y «mi ciudad» en todos tus dispositivos
  // Supabase (Auth + Postgres en la región de la UE), sin librerías: se habla directamente con su API.
  // La clave es la «publishable», pública por diseño: lo que cada persona puede leer o escribir lo deciden
  // las políticas RLS de la base de datos (solo sus propias filas). Sin sesión, todo sigue como siempre:
  // los favoritos viven en este navegador (planika_favs).
  var SB_URL = 'https://rqjrrdtdscvcimwzrwxj.supabase.co';
  var SB_KEY = 'sb_publishable_1gASlwY1wubC872dD5SJMw_4txaahRF';
  var ACCOUNTS_PUBLIC = false;  // mientras sea false, las cuentas solo se ven con ?cuentas=1 (pruebas)
  var GOOGLE_LOGIN = true;      // «Continuar con Google» (proveedor Google configurado en Supabase)
  var EMAIL_LOGIN = true;       // código (y enlace) por email: necesita SMTP propio (Brevo) configurado en Supabase
  var IN_APP = /Instagram|FBAN|FBAV|FB_IAB|musical_ly|BytedanceWebview|Line\/|Twitter/i.test(navigator.userAgent);  // Google no deja entrar desde ahí
  var K_SESSION = 'planika_sesion', K_OPS = 'planika_fav_ops', K_PLACE = 'planika_lugar', K_ON = 'planika_cuentas', K_ASK = 'planika_pide';
  var ASK_TTL = 2 * 3600e3;  // el enlace caduca en 1 h; lo pedido en este navegador se recuerda 2 h como mucho
  function lsGet(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } }
  function lsSet(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* sin almacenamiento */ } }
  (function () { var c = new URLSearchParams(location.search).get('cuentas'); if (c === '1') lsSet(K_ON, 1); else if (c === '0') lsSet(K_ON, null); })();
  var accountsOn = ACCOUNTS_PUBLIC || !!lsGet(K_ON);
  var session = lsGet(K_SESSION);
  var pending = lsGet(K_OPS) || {};      // favoritos cambiados aún sin confirmar en la cuenta: id -> 1 (añadir) | 0 (quitar)
  var myPlace = session ? (lsGet(K_PLACE) || '') : '';
  var lastPull = 0;
  (function () { var a = lsGet(K_ASK); if (a && !(Date.now() - a.t < ASK_TTL)) lsSet(K_ASK, null); })();

  function b64json(part) {
    var b = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(b, function (c) { return c.charCodeAt(0); })));
  }
  function tokenInfo(t) { try { return b64json(String(t).split('.')[1]) || {}; } catch (e) { return {}; } }
  function setSession(s) {
    if (s && s.access_token) {
      var p = tokenInfo(s.access_token);
      var exp = +s.expires_at || +p.exp || (Math.floor(Date.now() / 1000) + (+s.expires_in || 3600));
      session = { access_token: s.access_token, refresh_token: s.refresh_token, expires_at: exp, id: p.sub || (s.user && s.user.id) || '', email: p.email || (s.user && s.user.email) || '' };
    } else session = null;
    lsSet(K_SESSION, session);
  }
  function httpError(r, j) {
    var e = new Error((j && (j.msg || j.error_description || j.message)) || ('HTTP ' + r.status));
    e.status = r.status; e.code = j && (j.error_code || j.code); return e;
  }
  function readJSON(r) { return r.text().then(function (t) { var j = null; try { j = t ? JSON.parse(t) : null; } catch (e) { /* no es JSON */ } if (!r.ok) throw httpError(r, j); return j; }); }
  function authPost(path, body, token) {
    var h = { apikey: SB_KEY, 'Content-Type': 'application/json' };
    if (token) h.Authorization = 'Bearer ' + token;
    return fetch(SB_URL + '/auth/v1/' + path, { method: 'POST', headers: h, body: JSON.stringify(body || {}) }).then(readJSON);
  }
  var refreshing = null;
  function freshToken(force) {
    var s = lsGet(K_SESSION);  // otra pestaña pudo renovarla ya
    if (!s) { if (session) signedOut(); return Promise.reject(new Error('sin sesión')); }
    session = s;
    if (!force && s.expires_at - 60 > Date.now() / 1000) return Promise.resolve(s.access_token);
    if (!refreshing) {
      refreshing = authPost('token?grant_type=refresh_token', { refresh_token: s.refresh_token })
        .then(function (j) { refreshing = null; setSession(j); return j.access_token; },
          function (err) { refreshing = null; if (err.status >= 400 && err.status < 500) { signedOut(); toast('Tu sesión ha caducado: vuelve a entrar'); } throw err; });
    }
    return refreshing;
  }
  function api(method, path, body, prefer, retried) {
    return freshToken(retried === 'force').then(function (tok) {
      var h = { apikey: SB_KEY, Authorization: 'Bearer ' + tok };
      if (body !== undefined) h['Content-Type'] = 'application/json';
      if (prefer) h.Prefer = prefer;
      return fetch(SB_URL + path, { method: method, headers: h, body: body === undefined ? undefined : JSON.stringify(body) });
    }).then(function (r) {
      if (r.status === 401 && !retried) return api(method, path, body, prefer, 'force');
      return readJSON(r);
    });
  }
  function pgList(ids) { return '(' + ids.map(function (id) { return '"' + String(id).replace(/["\\]/g, '\\$&') + '"'; }).join(',') + ')'; }

  // Favoritos: este navegador guarda una copia y la cola de cambios pendientes; la cuenta manda.
  var flushing = null, flushAgain = false;
  function flushFavs() {
    if (!session) return Promise.resolve();
    if (flushing) { flushAgain = true; return flushing; }
    var sent = {}, adds = [], dels = [];
    Object.keys(pending).forEach(function (id) { sent[id] = pending[id]; (pending[id] ? adds : dels).push(id); });
    adds = adds.filter(function (id) { return id.length && id.length <= 64; });
    if (!adds.length && !dels.length) { pending = {}; lsSet(K_OPS, null); return Promise.resolve(); }
    var jobs = [];
    for (var i = 0; i < adds.length; i += 500) jobs.push(api('POST', '/rest/v1/favorites', adds.slice(i, i + 500).map(function (id) { return { event_id: id }; }), 'resolution=ignore-duplicates,return=minimal'));
    for (var j = 0; j < dels.length; j += 100) jobs.push(api('DELETE', '/rest/v1/favorites?event_id=in.' + encodeURIComponent(pgList(dels.slice(j, j + 100)))));
    flushing = Promise.all(jobs).then(function () {
      Object.keys(sent).forEach(function (id) { if (pending[id] === sent[id]) delete pending[id]; });
      lsSet(K_OPS, Object.keys(pending).length ? pending : null);
    }).then(function () { flushing = null; if (flushAgain) { flushAgain = false; return flushFavs(); } },
      function (err) { flushing = null; flushAgain = false; throw err; });
    return flushing;
  }
  function pullFavs() {
    var got = [];
    function page(off) {
      return api('GET', '/rest/v1/favorites?select=event_id&order=created_at.asc,event_id.asc&limit=1000&offset=' + off).then(function (rows) {
        rows = rows || []; rows.forEach(function (r) { got.push(r.event_id); });
        return rows.length === 1000 ? page(off + 1000) : null;
      });
    }
    return page(0).then(function () {
      if (!session) return;
      var s = new Set(got);
      Object.keys(pending).forEach(function (id) { if (pending[id]) s.add(id); else s.delete(id); });
      favSet = s; saveFavs(); repaintFavs(); lastPull = Date.now();
    });
  }
  function repaintFavs() {
    document.querySelectorAll('[data-fav]').forEach(function (x) { var on = favSet.has(x.dataset.fav); x.classList.toggle('on', on); x.textContent = on ? '★' : '☆'; });
    if (state.favs) refresh();
    if ($('accFavN')) $('accFavN').textContent = favSet.size.toLocaleString('es-ES');
  }
  function favChanged(id, on) {
    if (!session) {
      if (accountsOn && on && !lsGet('planika_aviso_cuenta')) { lsSet('planika_aviso_cuenta', 1); toast('Guardado en este dispositivo. Entra en tu cuenta para tenerlo en todos'); }
      return;
    }
    pending[id] = on ? 1 : 0; lsSet(K_OPS, pending);
    flushFavs().catch(function () { /* se reintenta al volver la conexión o al abrir Planika */ });
  }
  function syncAll() {
    if (!session) return Promise.resolve(false);
    return flushFavs().then(pullFavs).then(pullPlace).then(function () { return true; }, function (err) {
      if (session && err && err.status) accMsg('No se han podido sincronizar tus favoritos ahora. Lo intentaremos más tarde.', true);
      return false;
    });
  }

  // «Mi ciudad»: comunidad|provincia|localidad, como el filtro «Dónde».
  function placeNow() { return state.ccaa || state.prov || state.city ? [state.ccaa, state.prov, state.city].join('|') : ''; }
  function placeName(code) {
    var p = (code || '').split('|');
    return p[2] || (p[1] && (PROV[p[1]] || {}).name) || p[0] || '';
  }
  function setPlaceState(code) { var p = (code || '').split('|'); state.ccaa = p[0] || ''; state.prov = p[1] || ''; state.city = p[2] || ''; }
  function applyPlace(code) {
    setPlaceState(code);
    $('ccaa').value = state.ccaa; fillProvinces(); $('prov').value = state.prov;
    CITY_KEY = norm(state.city); fillCities(); syncWhere(); refresh();
  }
  function pullPlace() {
    return api('GET', '/rest/v1/profiles?select=place').then(function (rows) {
      if (!session) return;
      var place = (rows && rows[0] && rows[0].place) || '';
      var was = myPlace; myPlace = place; lsSet(K_PLACE, place || null);
      if (place && place !== was && !placeNow() && !state.favs && !$('modal').open) applyPlace(place);
      paintAccount();
    });
  }
  function savePlace(code) {
    accMsg('');
    return api('POST', '/rest/v1/profiles', { place: code || null, updated_at: new Date().toISOString() }, 'resolution=merge-duplicates,return=minimal')
      .then(function () { myPlace = code || ''; lsSet(K_PLACE, myPlace || null); paintAccount(); accMsg(code ? 'Guardado: tu ciudad es ' + placeName(code) + '.' : 'Ciudad quitada.'); track('account_place', { set: code ? 1 : 0 }); })
      .catch(function () { accMsg('No se ha podido guardar. Prueba otra vez en un momento.', true); });
  }

  // Entrar, salir y borrar la cuenta
  function signedIn(s, how) {
    var who = tokenInfo(s.access_token);
    var other = session && who.sub && session.id !== who.sub;  // cambio de cuenta: lo de este dispositivo es de la otra
    if (other) signedOut();
    setSession(s); lsSet(K_ASK, null);
    if (!other) favSet.forEach(function (id) { if (!(id in pending)) pending[id] = 1; });  // lo que ya tenías aquí pasa a tu cuenta
    lsSet(K_OPS, Object.keys(pending).length ? pending : null); lsSet(K_ON, 1); accountsOn = true;
    track('login', { method: how });
    paintAccount();
    return syncAll().then(function (ok) {
      if (!session) return;
      toast(!ok ? 'Has entrado. Tus favoritos se sincronizarán en cuanto haya conexión' : favSet.size ? 'Has entrado: tus favoritos ya están en tu cuenta' : 'Has entrado en Planika');
    });
  }
  function signedOut() {
    session = null; pending = {}; myPlace = '';
    lsSet(K_SESSION, null); lsSet(K_OPS, null); lsSet(K_PLACE, null); lsSet(K_ASK, null);
    paintAccount();
  }
  function readAuthReturn() {
    var h = new URLSearchParams(location.hash.replace(/^#/, ''));
    var q = new URLSearchParams(location.search);
    var tok = h.get('access_token');
    var err = h.get('error_code') || h.get('error') || q.get('error_code') || q.get('error');
    if (!tok && !err) return null;
    try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { /* file:// */ }
    lsSet(K_ON, 1); accountsOn = true;
    if (tok) return { access_token: tok, refresh_token: h.get('refresh_token'), expires_in: h.get('expires_in'), expires_at: h.get('expires_at') };
    return { error: err };
  }
  function authErrorText(err) {
    var c = (err && (err.code || err.error)) || '';
    if (err && err.status === 429 || /rate_limit/.test(c)) return 'Has pedido varios enlaces seguidos. Espera un minuto y vuelve a probar.';
    if (/otp_expired|expired/.test(c)) return 'El enlace o el código ha caducado o ya se usó. Pide uno nuevo.';
    if (/access_denied/.test(c)) return 'No has llegado a entrar. Puedes volver a probar cuando quieras.';
    if (/email_address_invalid|validation/.test(c)) return 'Revisa el email: no parece válido.';
    if (/not_authorized/.test(c)) return 'Todavía no podemos enviar códigos a ese email. De momento, entra con Google.';
    if (err && err.status === 403) return 'El código no es correcto o ha caducado.';
    return 'No se ha podido completar. Comprueba tu conexión y vuelve a probar.';
  }

  // Ventana «Tu cuenta»
  var sentTo = '';
  function accMsg(text, isErr) { var m = $('accMsg'); m.textContent = text || ''; m.hidden = !text; m.classList.toggle('err', !!isErr); }
  function accShow(which) {
    $('accOut').hidden = which !== 'out'; $('accSent').hidden = which !== 'sent'; $('accConfirm').hidden = which !== 'confirm';
    $('accIn').hidden = which !== 'in'; $('accDelAsk').hidden = true;
  }
  function paintAccount() {
    $('accountWrap').hidden = !accountsOn;
    $('accountLabel').textContent = session ? 'Mi cuenta' : 'Entrar';
    $('accountNote').textContent = session ? '★ Favoritos sincronizados' : 'Tus favoritos y tu ciudad en todos tus dispositivos';
    $('accGoogleWrap').hidden = !GOOGLE_LOGIN || IN_APP; $('accInApp').hidden = !GOOGLE_LOGIN || !IN_APP;
    $('accForm').hidden = !EMAIL_LOGIN; $('accOr').hidden = !EMAIL_LOGIN || !GOOGLE_LOGIN || IN_APP;
    if (!session) { if ($('accIn').hidden === false) accShow('out'); return; }
    $('accWho').textContent = session.email || 'tu email';
    $('accFavN').textContent = favSet.size.toLocaleString('es-ES');
    $('accPlace').textContent = myPlace ? 'Tu ciudad: ' + placeName(myPlace) + '.' : 'Aún no has elegido tu ciudad.';
    var now = placeNow();
    $('accPlaceSet').textContent = now ? (now === myPlace ? '✓ ' + placeName(now) : 'Usar «' + placeName(now) + '»') : 'Elige antes un lugar en «Dónde»';
    $('accPlaceSet').disabled = !now || now === myPlace;
    $('accPlaceDel').hidden = !myPlace;
  }
  function openAccount() {
    accMsg(''); accShow(session ? 'in' : (sentTo ? 'sent' : 'out')); paintAccount();
    if ($('account').showModal) $('account').showModal(); else $('account').setAttribute('open', '');
    if (session && Date.now() - lastPull > 30000) syncAll().then(paintAccount);
  }
  $('accountBtn').addEventListener('click', openAccount);
  $('accountClose').addEventListener('click', function () { $('account').close(); });
  $('accForm').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var email = $('accEmail').value.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { accMsg('Escribe un email válido, por ejemplo nombre@gmail.com.', true); return; }
    var btn = $('accSend'); btn.disabled = true; btn.textContent = 'Enviando…'; accMsg('');
    authPost('otp?redirect_to=' + encodeURIComponent(location.origin + '/'), { email: email, create_user: true })
      .then(function () { sentTo = email; lsSet(K_ASK, { email: email, t: Date.now() }); $('accSentTo').textContent = email; $('accCode').value = ''; accShow('sent'); try { $('accCode').focus(); } catch (e) { /* sin foco */ } track('login_code_sent'); },
        function (err) { accMsg(authErrorText(err), true); })
      .then(function () { btn.disabled = false; btn.textContent = 'Enviarme un código'; });
  });
  $('accCodeForm').addEventListener('submit', function (ev) {
    ev.preventDefault();
    var code = $('accCode').value.replace(/\D/g, '');
    if (code.length < 6) { accMsg('El código tiene al menos 6 cifras.', true); return; }
    accMsg('Comprobando…');
    authPost('verify', { type: 'email', email: sentTo, token: code })
      .then(function (s) { sentTo = ''; accMsg(''); accShow('in'); return signedIn(s, 'code'); },
        function (err) { accMsg(err.status === 403 || /otp_expired/.test(err.code || '') ? 'El código no es correcto o ha caducado. Usa el del último correo o pide uno nuevo.' : authErrorText(err), true); });
  });
  $('accBack').addEventListener('click', function () { sentTo = ''; accMsg(''); accShow('out'); $('accEmail').focus(); });
  $('accGoogle').addEventListener('click', function () {
    lsSet(K_ASK, { google: 1, t: Date.now() }); track('login_start', { method: 'google' });
    location.href = SB_URL + '/auth/v1/authorize?provider=google&redirect_to=' + encodeURIComponent(location.origin + '/');
  });
  $('accPlaceSet').addEventListener('click', function () { var now = placeNow(); if (now) savePlace(now); });
  $('accPlaceDel').addEventListener('click', function () { savePlace(''); });
  $('accLogout').addEventListener('click', function () {
    var tok = session && session.access_token;
    flushFavs().catch(function () { /* sin conexión: los cambios se quedan en este dispositivo */ }).then(function () {
      if (tok) authPost('logout?scope=local', {}, tok).catch(function () { /* la sesión caduca sola */ });
      signedOut(); accShow('out'); accMsg('Has salido. Tus favoritos siguen en este dispositivo.'); track('logout');
    });
  });
  // Vuelta del enlace del email. Si no se pidió desde este navegador (o es de otro email), se pregunta antes de
  // entrar: así nadie puede colarte su sesión con un enlace preparado y quedarse con tus favoritos.
  var backWaiting = null;
  function onAuthBack(back) {
    if (!back.access_token) { openAccount(); accMsg(authErrorText({ code: back.error }), true); return; }
    var who = tokenInfo(back.access_token), email = String(who.email || '').toLowerCase();
    var asked = lsGet(K_ASK);
    var fresh = asked && Date.now() - asked.t < ASK_TTL;
    var how = who.app_metadata && who.app_metadata.provider === 'google' ? 'google' : 'link';
    if ((fresh && (asked.google ? how === 'google' : email && asked.email === email)) || (session && who.sub && session.id === who.sub)) { sentTo = ''; signedIn(back, how); return; }
    backWaiting = back; sentTo = '';
    openAccount(); accShow('confirm'); $('accConfirmWho').textContent = email || 'otra cuenta';
  }
  $('accConfirmYes').addEventListener('click', function () { var b = backWaiting; backWaiting = null; if (!b) return; accShow('in'); signedIn(b, 'confirmado'); });
  $('accConfirmNo').addEventListener('click', function () {
    var b = backWaiting; backWaiting = null;
    if (b) authPost('logout?scope=local', {}, b.access_token).catch(function () { /* caduca sola */ });
    accShow(session ? 'in' : 'out'); paintAccount(); accMsg('No has entrado. Si no pediste el enlace, puedes ignorar el correo.');
  });
  $('accDel').addEventListener('click', function () { $('accDelAsk').hidden = false; $('accDelYes').focus(); });
  $('accDelNo').addEventListener('click', function () { $('accDelAsk').hidden = true; });
  $('accDelYes').addEventListener('click', function () {
    var btn = this; btn.disabled = true; accMsg('Borrando tu cuenta…');
    api('POST', '/rest/v1/rpc/delete_my_account', {})
      .then(function () { signedOut(); accShow('out'); accMsg('Cuenta borrada. Hemos eliminado tu email, tus favoritos guardados en la cuenta y tu ciudad.'); track('account_deleted'); },
        function () { accMsg('No se ha podido borrar ahora. Comprueba tu conexión y vuelve a probar.', true); })
      .then(function () { btn.disabled = false; });
  });
  window.addEventListener('storage', function (ev) {
    if (ev.key === K_SESSION) { session = lsGet(K_SESSION); if (!session) { pending = {}; myPlace = ''; } paintAccount(); }
    else if (ev.key === 'planika_favs') { favSet = loadFavs(); repaintFavs(); }
  });
  window.addEventListener('online', function () { if (session) syncAll(); });
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'visible' && session && Date.now() - lastPull > 300000) syncAll(); });

  // ---------- arranque
  var authBack = readAuthReturn();  // vuelta del enlace del email (antes de que writeURL limpie la dirección)
  var openId = readURL();
  if (session && myPlace && !state.ccaa && !state.prov && !state.city && !state.q && !state.favs && !openId) setPlaceState(myPlace);
  window.PLANIKA_D = applyChunk;
  (window.PLANIKA_Q || []).forEach(function (a) { applyChunk(a[0], a[1], a[2]); });
  window.PLANIKA_Q = [];
  populate();
  if (state.from || state.to) { clearQuick(); refresh(); } else setRange('all');
  if (advCount()) $('adv').open = true;
  if (state.view !== 'list') setView(state.view);
  if (openId) openModal(openId);
  paintAccount();
  if (authBack) onAuthBack(authBack); else if (session) syncAll();
  // Si el enlace se abre en una pestaña que ya tenía Planika, solo cambia el #: no se recarga la página.
  window.addEventListener('hashchange', function () { var back = readAuthReturn(); if (back) onAuthBack(back); });
})();
