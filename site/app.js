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
  // "Dónde": un solo desplegable con las provincias agrupadas por comunidad (valores "c:<comunidad>" y "p:<código>").
  function fillWhere(ccaas) {
    var pc = provCounts(); var sel = $('where');
    Object.keys(ccaas).sort(function (a, b) { return a.localeCompare(b, 'es'); }).forEach(function (c) {
      var provs = DATA.provinces.filter(function (p) { return p.ccaa === c && pc[p.code]; })
        .sort(function (a, b) { return a.name.localeCompare(b.name, 'es'); });
      if (!provs.length) return;
      var g = document.createElement('optgroup'); g.label = c;
      if (provs.length > 1) { var o = document.createElement('option'); o.value = 'c:' + c; o.textContent = c + ', toda la comunidad (' + ccaas[c].toLocaleString('es-ES') + ')'; g.appendChild(o); }
      provs.forEach(function (p) { var o = document.createElement('option'); o.value = 'p:' + p.code; o.textContent = p.name + ' (' + pc[p.code].toLocaleString('es-ES') + ')'; g.appendChild(o); });
      sel.appendChild(g);
    });
    syncWhere();
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
    $('cityField').hidden = keys.length < 2;
    var cur = keys.filter(function (c) { return c.key === norm(state.city); })[0];
    if (!cur) { state.city = ''; CITY_KEY = ''; sel.value = ''; } else { state.city = cur.name; CITY_KEY = cur.key; sel.value = cur.name; }
  }
  function syncWhere() {
    var sel = $('where'); var v = state.prov ? 'p:' + state.prov : (state.ccaa ? 'c:' + state.ccaa : '');
    sel.value = v; if (sel.value !== v) sel.value = '';
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
    return '<article class="card pop' + pop + '" data-id="' + e.id + '" data-c="' + Math.floor(e.i / CHUNK) + '" data-pop="' + pop + '"' + (opts.noOngoing ? ' data-no="1"' : '') + '>' + img + '<div class="body">' +
      '<div class="badges"><span class="badge">' + c.icon + ' ' + esc(c.name) + '</span>' + price + permBadge + (ongoing && !opts.noOngoing ? '<span class="badge ongoing">En curso</span>' : '') + (d !== null ? '<span class="badge dist">a ' + (d < 10 ? d.toFixed(1) : Math.round(d)) + ' km</span>' : '') + '</div>' +
      // El título lleva a la ficha del plan en Planika (enlace rastreable); la web oficial sigue en "Entradas" y "Más info".
      '<h3><a href="' + esc(evFile(e)) + '">' + esc(title(e)) + '</a></h3>' +
      (e.title_es ? '<div class="where">' + esc(e.title) + '</div>' : '') +
      '<div class="when">📅 ' + esc(whenText(e)) + '</div>' + sess +
      (where ? '<div class="where">📍 ' + esc(where) + '</div>' : '') +
      (e.description ? '<p class="desc">' + esc(e.description) + '</p>' : '') +
      '<div class="actions">' + tickets + info + '<button type="button" class="btn addcal" data-id="' + e.id + '">＋ Calendario</button>' +
      '<button type="button" class="fav' + (favSet.has(e.id) ? ' on' : '') + '" data-fav="' + e.id + '" title="Guardar en favoritos">' + (favSet.has(e.id) ? '★' : '☆') + '</button>' +
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
  $('where').addEventListener('change', function () {
    var v = this.value;
    state.ccaa = v.indexOf('c:') === 0 ? v.slice(2) : ''; state.prov = v.indexOf('p:') === 0 ? v.slice(2) : '';
    $('ccaa').value = state.ccaa; fillProvinces(); $('prov').value = state.prov; state.city = ''; fillCities(); refresh();
  });
  $('city').addEventListener('change', function () { state.city = this.value; CITY_KEY = norm(this.value); refresh(); });
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

  // ---------- arranque
  var openId = readURL();
  window.PLANIKA_D = applyChunk;
  (window.PLANIKA_Q || []).forEach(function (a) { applyChunk(a[0], a[1], a[2]); });
  window.PLANIKA_Q = [];
  populate();
  if (state.from || state.to) { clearQuick(); refresh(); } else setRange('all');
  if (advCount()) $('adv').open = true;
  if (state.view !== 'list') setView(state.view);
  if (openId) openModal(openId);
})();
