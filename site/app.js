/* Planes de ocio: filtros, lista, calendario y enlaces "añadir al calendario". */
(function () {
  'use strict';
  var DATA = window.PLANES_DATA || { events: [], categories: [], provinces: [], sources: [] };
  var EVENTS = DATA.events;
  var CATS = {};
  DATA.categories.forEach(function (c) { CATS[c.key] = c; });
  var PAGE = 48;
  var LONG_DAYS = 45; // a partir de aquí un evento se considera "de larga duración" en el calendario

  var $ = function (id) { return document.getElementById(id); };
  var state = { q: '', ccaa: '', prov: '', from: '', to: '', free: false, tickets: false, cats: {}, view: 'list', shown: PAGE,
                month: null, selDay: null };

  // ---------- utilidades de fecha
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function isoDate(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function fromIso(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function addDays(s, n) { var d = fromIso(s); d.setDate(d.getDate() + n); return isoDate(d); }
  var TODAY = isoDate(new Date());
  var fmtDay = new Intl.DateTimeFormat('es-ES', { weekday: 'short', day: 'numeric', month: 'short' });
  var fmtLong = new Intl.DateTimeFormat('es-ES', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  var fmtMonth = new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric' });
  var thisYear = TODAY.slice(0, 4);
  function fmtD(s) { return fmtDay.format(fromIso(s)) + (s.slice(0, 4) !== thisYear ? ' ' + s.slice(0, 4) : ''); }
  function spanDays(e) { return Math.round((fromIso(e.end) - fromIso(e.start)) / 864e5); }
  function whenText(e) {
    if (e.end !== e.start && e.start < TODAY) return 'Hasta el ' + fmtD(e.end) + (e.time ? ' · ' + e.time : '');
    var s = fmtD(e.start);
    if (e.end && e.end !== e.start) return s + ' – ' + fmtD(e.end);
    return e.time ? s + ' · ' + e.time : s;
  }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }

  // ---------- filtros
  function populate() {
    var ccaas = {}; var provCount = {};
    EVENTS.forEach(function (e) { if (e.ccaa) ccaas[e.ccaa] = (ccaas[e.ccaa] || 0) + 1; if (e.province_code) provCount[e.province_code] = (provCount[e.province_code] || 0) + 1; });
    var selC = $('ccaa');
    Object.keys(ccaas).sort(function (a, b) { return a.localeCompare(b, 'es'); }).forEach(function (c) {
      var o = document.createElement('option'); o.value = c; o.textContent = c + ' (' + ccaas[c] + ')'; selC.appendChild(o);
    });
    fillProvinces(provCount);
    var chips = $('cats');
    DATA.categories.forEach(function (c) {
      var n = EVENTS.filter(function (e) { return e.category === c.key; }).length;
      if (!n) return;
      var b = document.createElement('button'); b.type = 'button'; b.className = 'chip'; b.dataset.cat = c.key;
      b.innerHTML = c.icon + ' ' + esc(c.name) + ' <small>' + n + '</small>';
      b.addEventListener('click', function () { state.cats[c.key] = !state.cats[c.key]; b.classList.toggle('on', !!state.cats[c.key]); refresh(); });
      chips.appendChild(b);
    });
    var ul = $('sources');
    DATA.sources.forEach(function (s) {
      var li = document.createElement('li');
      li.innerHTML = '<a href="' + esc(s.home) + '" target="_blank" rel="noopener">' + esc(s.name) + '</a> · ' + s.count + ' planes';
      ul.appendChild(li);
    });
    $('meta').textContent = 'Actualizado el ' + (DATA.updated_at || '').replace('T', ' a las ') + ' · ' + EVENTS.length.toLocaleString('es-ES') + ' planes del ' + fmtDay.format(fromIso(DATA.from)) + ' al ' + fmtDay.format(fromIso(DATA.to));
  }
  function fillProvinces(provCount) {
    var sel = $('prov'); var cur = state.prov;
    sel.innerHTML = '<option value="">Todas</option>';
    DATA.provinces.filter(function (p) { return (!state.ccaa || p.ccaa === state.ccaa) && provCount[p.code]; })
      .sort(function (a, b) { return a.name.localeCompare(b.name, 'es'); })
      .forEach(function (p) { var o = document.createElement('option'); o.value = p.code; o.textContent = p.name + ' (' + provCount[p.code] + ')'; sel.appendChild(o); });
    sel.value = cur; if (sel.value !== cur) { state.prov = ''; }
  }
  var provCountAll = null;
  function provCounts() {
    if (!provCountAll) { provCountAll = {}; EVENTS.forEach(function (e) { if (e.province_code) provCountAll[e.province_code] = (provCountAll[e.province_code] || 0) + 1; }); }
    return provCountAll;
  }

  function anyCat() { for (var k in state.cats) if (state.cats[k]) return true; return false; }
  function matches(e, ignoreDates) {
    if (state.ccaa && e.ccaa !== state.ccaa) return false;
    if (state.prov && e.province_code !== state.prov) return false;
    if (state.free && !e.free) return false;
    if (state.tickets && !e.tickets_url) return false;
    if (anyCat() && !state.cats[e.category]) return false;
    if (!ignoreDates) {
      if (state.from && e.end < state.from) return false;
      if (state.to && e.start > state.to) return false;
    }
    if (state.q) {
      var hay = norm(e.title + ' ' + e.venue + ' ' + e.city + ' ' + e.province + ' ' + e.subtype + ' ' + e.description);
      var terms = norm(state.q).split(/\s+/).filter(Boolean);
      for (var i = 0; i < terms.length; i++) if (hay.indexOf(terms[i]) < 0) return false;
    }
    return true;
  }
  function filtered(ignoreDates) { return EVENTS.filter(function (e) { return matches(e, ignoreDates); }); }
  // Orden de la lista: lo que ocurre antes primero; entre lo ya en curso, lo más corto (no exposiciones de meses) antes.
  function sortKey(e) { var from = state.from && state.from > TODAY ? state.from : TODAY; return (e.start > from ? e.start : from) + '|' + pad(Math.min(99, spanDays(e))) + '|' + (e.time || '99'); }
  function sorted(list) { return list.map(function (e) { return [sortKey(e), e]; }).sort(function (a, b) { return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0; }).map(function (x) { return x[1]; }); }

  // ---------- tarjetas
  function card(e, opts) {
    opts = opts || {};
    var c = CATS[e.category] || { icon: '✨', name: 'Otros' };
    var ongoing = e.start < TODAY && e.end >= TODAY;
    var img = e.image ? '<img src="' + esc(e.image) + '" alt="" loading="lazy" onerror="this.remove()">' : '';
    var where = [e.venue, e.city, e.province && e.province !== e.city ? e.province : ''].filter(Boolean).join(' · ');
    var price = e.free ? '<span class="badge free">Gratis</span>' : (e.price ? '<span class="badge">' + esc(e.price) + '</span>' : '');
    var tickets = e.tickets_url ? '<a class="btn primary" href="' + esc(e.tickets_url) + '" target="_blank" rel="noopener">🎫 Entradas</a>' : '';
    var info = e.url && e.url !== e.tickets_url ? '<a class="btn" href="' + esc(e.url) + '" target="_blank" rel="noopener">Más info ↗</a>' : '';
    return '<article class="card" data-id="' + e.id + '">' + img + '<div class="body">' +
      '<div class="badges"><span class="badge">' + c.icon + ' ' + esc(c.name) + '</span>' + price + (ongoing && !opts.noOngoing ? '<span class="badge ongoing">En curso</span>' : '') + '</div>' +
      '<h3><a href="' + esc(e.url || e.tickets_url || '#') + '" target="_blank" rel="noopener">' + esc(e.title) + '</a></h3>' +
      '<div class="when">📅 ' + esc(whenText(e)) + '</div>' +
      (where ? '<div class="where">📍 ' + esc(where) + '</div>' : '') +
      (e.description ? '<p class="desc">' + esc(e.description) + '</p>' : '') +
      '<div class="actions">' + tickets + info + '<button type="button" class="btn addcal" data-id="' + e.id + '">＋ Calendario</button></div>' +
      '<div class="src">Fuente: ' + esc(e.source) + (e.subtype ? ' · ' + esc(e.subtype) : '') + '</div>' +
      '</div></article>';
  }

  function renderList() {
    var list = sorted(filtered());
    var el = $('list');
    $('count').innerHTML = '<strong>' + list.length.toLocaleString('es-ES') + '</strong> planes' + (list.length !== EVENTS.length ? ' de ' + EVENTS.length.toLocaleString('es-ES') : '');
    if (!list.length) { el.innerHTML = '<div class="empty">No hay planes con esos filtros. Prueba a ampliar las fechas o quitar algún filtro.</div>'; $('more').hidden = true; return; }
    el.innerHTML = list.slice(0, state.shown).map(function (e) { return card(e); }).join('');
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
      html += '<button type="button" class="day' + (out ? ' out' : '') + (ds === TODAY ? ' today' : '') + (ds === state.selDay ? ' sel' : '') + '" data-day="' + ds + '"' + (out ? ' tabindex="-1"' : '') + '>' +
        '<span class="n">' + cur.getDate() + '</span>' + (s ? '<span class="starts">' + s + '</span>' : '') + (o ? '<span class="ongoing">+' + o + ' en curso</span>' : '') + '</button>';
      cur.setDate(cur.getDate() + 1);
      if (i === 34 && cur.getMonth() !== m.getMonth()) break;
    }
    $('calGrid').innerHTML = html;
    renderDay();
  }
  function renderDay() {
    var p = $('dayPanel');
    if (!state.selDay) { p.hidden = true; return; }
    var d = state.selDay;
    var list = filtered(true).filter(function (e) { return e.start <= d && e.end >= d; });
    var st = sorted(list.filter(function (e) { return e.start === d; }));
    var on = list.filter(function (e) { return e.start !== d && spanDays(e) <= LONG_DAYS; }).sort(function (a, b) { return a.end < b.end ? -1 : 1; });
    var longOnes = list.length - st.length - on.length;
    var h = '<h3>' + cap(fmtLong.format(fromIso(d))) + ' · ' + (st.length + on.length) + ' planes</h3>';
    if (!st.length && !on.length) h += '<p class="empty">Nada registrado ese día con los filtros actuales.</p>';
    if (st.length) h += '<h4>Empiezan este día (' + st.length + ')</h4><div class="mini">' + st.slice(0, 120).map(function (e) { return card(e, { noOngoing: true }); }).join('') + (st.length > 120 ? '<p class="empty">… y ' + (st.length - 120) + ' más. Afina los filtros o usa la vista de lista.</p>' : '') + '</div>';
    if (on.length) h += '<h4>En curso (' + on.length + ')</h4><div class="mini">' + on.slice(0, 60).map(function (e) { return card(e, { noOngoing: true }); }).join('') + (on.length > 60 ? '<p class="empty">… y ' + (on.length - 60) + ' más. Usa la vista de lista para verlos todos.</p>' : '') + '</div>';
    if (longOnes > 0) h += '<p class="hint">Además hay ' + longOnes + ' planes de larga duración activos ese día (exposiciones, temporadas…) que no se cuentan en el calendario. <button type="button" class="linklike" data-golist="' + d + '">Verlos en la lista</button></p>';
    p.innerHTML = h; p.hidden = false;
  }

  // ---------- añadir al calendario
  function calTimes(e) {
    var allDay = !e.time;
    var start, end;
    if (allDay) { start = e.start.replace(/-/g, ''); end = addDays(e.end, 1).replace(/-/g, ''); }
    else {
      var t = e.time.replace(':', '') + '00';
      start = e.start.replace(/-/g, '') + 'T' + t;
      var hh = +e.time.slice(0, 2) + 2; var endDay = e.start;
      if (hh >= 24) { hh -= 24; endDay = addDays(e.start, 1); }
      end = endDay.replace(/-/g, '') + 'T' + pad(hh) + e.time.slice(3) + '00';
    }
    return { allDay: allDay, start: start, end: end };
  }
  function details(e) {
    var parts = [];
    if (e.description) parts.push(e.description);
    if (e.price) parts.push('Precio: ' + e.price); else if (e.free) parts.push('Entrada gratuita');
    if (e.tickets_url) parts.push('Entradas: ' + e.tickets_url);
    if (e.url && e.url !== e.tickets_url) parts.push('Más información: ' + e.url);
    parts.push('Fuente: ' + e.source);
    return parts.join('\n');
  }
  function location(e) { return [e.venue, e.address, e.city, e.province].filter(Boolean).join(', '); }
  function isoLocal(s) { return s.length === 8 ? s.slice(0, 4) + '-' + s.slice(4, 6) + '-' + s.slice(6, 8) : s.slice(0, 4) + '-' + s.slice(4, 6) + '-' + s.slice(6, 8) + 'T' + s.slice(9, 11) + ':' + s.slice(11, 13) + ':00'; }
  function links(e) {
    var t = calTimes(e), enc = encodeURIComponent, title = e.title, det = details(e), loc = location(e);
    var google = 'https://calendar.google.com/calendar/render?action=TEMPLATE&text=' + enc(title) + '&dates=' + t.start + '/' + t.end + '&details=' + enc(det) + '&location=' + enc(loc) + '&ctz=Europe/Madrid';
    var ol = '&subject=' + enc(title) + '&startdt=' + enc(isoLocal(t.start)) + '&enddt=' + enc(isoLocal(t.end)) + '&body=' + enc(det) + '&location=' + enc(loc) + (t.allDay ? '&allday=true' : '');
    var outlook = 'https://outlook.live.com/calendar/0/action/compose?rru=addevent' + ol;
    var office = 'https://outlook.office.com/calendar/0/action/compose?rru=addevent' + ol;
    var yahoo = 'https://calendar.yahoo.com/?v=60&title=' + enc(title) + '&st=' + t.start + (t.allDay ? '&dur=allday' : '&et=' + t.end) + '&desc=' + enc(det) + '&in_loc=' + enc(loc);
    return { google: google, outlook: outlook, office: office, yahoo: yahoo };
  }
  function icsText(e) {
    var t = calTimes(e);
    var f = function (s) { return String(s).replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/[,;]/g, function (c) { return '\\' + c; }); };
    var stamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Planika//planikaapp.com//ES', 'CALSCALE:GREGORIAN', 'BEGIN:VEVENT',
      'UID:' + e.id + '@planikaapp.com', 'DTSTAMP:' + stamp,
      t.allDay ? 'DTSTART;VALUE=DATE:' + t.start : 'DTSTART;TZID=Europe/Madrid:' + t.start,
      t.allDay ? 'DTEND;VALUE=DATE:' + t.end : 'DTEND;TZID=Europe/Madrid:' + t.end,
      'SUMMARY:' + f(e.title), 'DESCRIPTION:' + f(details(e)), 'LOCATION:' + f(location(e))];
    if (e.url || e.tickets_url) lines.push('URL:' + (e.tickets_url || e.url));
    if (e.lat != null && e.lon != null) lines.push('GEO:' + e.lat + ';' + e.lon);
    lines.push('END:VEVENT', 'END:VCALENDAR');
    return lines.join('\r\n');
  }
  function downloadIcs(e) {
    var blob = new Blob([icsText(e)], { type: 'text/calendar;charset=utf-8' });
    var a = document.createElement('a'); a.href = URL.createObjectURL(blob);
    a.download = e.title.replace(/[^\w\dáéíóúñü ]+/gi, '').trim().slice(0, 60).replace(/\s+/g, '_') + '.ics';
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
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('.addcal');
    if (b) { ev.stopPropagation(); var e = EVENTS.find(function (x) { return x.id === b.dataset.id; }); if (e) openMenu(b, e); return; }
    if (!ev.target.closest('#menu')) closeMenu();
    var gl = ev.target.closest('[data-golist]');
    if (gl) { state.from = gl.dataset.golist; state.to = gl.dataset.golist; $('from').value = state.from; $('to').value = state.to; $('quick').querySelectorAll('button').forEach(function (b) { b.classList.remove('on'); }); setView('list'); window.scrollTo({ top: $('list').offsetTop - 80, behavior: 'smooth' }); return; }
    var d = ev.target.closest('.day');
    if (d && !d.classList.contains('out')) { state.selDay = state.selDay === d.dataset.day ? null : d.dataset.day; renderCalendar(); }
  });
  document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeMenu(); });

  // ---------- eventos de UI
  function refresh() { state.shown = PAGE; state.view === 'list' ? renderList() : renderCalendar(); }
  function setView(v) {
    state.view = v;
    $('view').querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.view === v); });
    $('calendar').hidden = v !== 'cal'; $('list').hidden = v !== 'list'; $('more').hidden = v !== 'list';
    refresh();
  }
  function setRange(key) {
    $('quick').querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b.dataset.range === key); });
    var from = TODAY, to = '';
    if (key === 'all') from = '';
    else if (key === 'today') to = TODAY;
    else if (key === 'weekend') {
      var d = fromIso(TODAY); var dow = (d.getDay() + 6) % 7; // 0 = lunes
      var sat = addDays(TODAY, dow <= 5 ? 5 - dow : 0); var sun = addDays(sat, 1);
      from = dow >= 4 ? TODAY : sat; if (dow === 6) from = TODAY; to = sun;
      if (dow === 4) from = TODAY; // viernes cuenta como fin de semana
    } else to = addDays(TODAY, +key);
    state.from = from; state.to = to; $('from').value = from; $('to').value = to;
    refresh();
  }
  var qt;
  $('q').addEventListener('input', function () { clearTimeout(qt); qt = setTimeout(function () { state.q = $('q').value.trim(); refresh(); }, 180); });
  $('ccaa').addEventListener('change', function () { state.ccaa = this.value; fillProvinces(provCounts()); refresh(); });
  $('prov').addEventListener('change', function () { state.prov = this.value; refresh(); });
  $('from').addEventListener('change', function () { state.from = this.value; $('quick').querySelectorAll('button').forEach(function (b) { b.classList.remove('on'); }); refresh(); });
  $('to').addEventListener('change', function () { state.to = this.value; $('quick').querySelectorAll('button').forEach(function (b) { b.classList.remove('on'); }); refresh(); });
  $('free').addEventListener('change', function () { state.free = this.checked; refresh(); });
  $('tickets').addEventListener('change', function () { state.tickets = this.checked; refresh(); });
  $('quick').addEventListener('click', function (ev) { var b = ev.target.closest('button'); if (b) setRange(b.dataset.range); });
  $('view').addEventListener('click', function (ev) { var b = ev.target.closest('button'); if (b) setView(b.dataset.view); });
  $('more').addEventListener('click', function () { state.shown += PAGE; renderList(); });
  $('prevM').addEventListener('click', function () { state.month = new Date(state.month.getFullYear(), state.month.getMonth() - 1, 1); state.selDay = null; renderCalendar(); });
  $('nextM').addEventListener('click', function () { state.month = new Date(state.month.getFullYear(), state.month.getMonth() + 1, 1); state.selDay = null; renderCalendar(); });
  $('todayM').addEventListener('click', function () { state.month = fromIso(TODAY); state.selDay = TODAY; renderCalendar(); });

  // El navegador puede restaurar valores de formulario al recargar; se parte siempre de un estado limpio.
  ['q', 'from', 'to'].forEach(function (id) { $(id).value = ''; });
  ['ccaa', 'prov'].forEach(function (id) { $(id).value = ''; });
  ['free', 'tickets'].forEach(function (id) { $(id).checked = false; });
  populate();
  setRange('all');
})();
