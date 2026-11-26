/* Planika: idiomas de la interfaz (español, euskera, catalán, gallego e inglés).
   Se traduce lo que es de Planika (menús, filtros, botones, avisos y fechas); los planes se ven en su idioma original.
   El idioma sale de ?lang=, de la elección guardada o del navegador. Los buscadores ven siempre el español:
   la web es una sola URL por página y su contenido indexado no cambia. */
(function () {
  'use strict';
  var LANGS = [['es', 'Español'], ['eu', 'Euskara'], ['ca', 'Català'], ['gl', 'Galego'], ['en', 'English']];
  var IDX = { eu: 0, ca: 1, gl: 2, en: 3 };
  var LOCALES = { es: 'es-ES', eu: 'eu-ES', ca: 'ca-ES', gl: 'gl-ES', en: 'en-GB' };
  var BOT = /bot\b|bot\/|crawl|spider|slurp|lighthouse|inspectiontool|mediapartners|facebookexternalhit|embedly|headless/i;

  function pick() {
    var q = '';
    try { q = new URLSearchParams(location.search).get('lang') || ''; } catch (e) { /* */ }
    if (LOCALES[q]) { try { localStorage.setItem('planika_lang', q); } catch (e) { /* */ } return q; }
    try { var s = localStorage.getItem('planika_lang'); if (LOCALES[s]) return s; } catch (e) { /* */ }
    if (BOT.test(navigator.userAgent || '')) return 'es';
    var list = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || 'es'];
    for (var i = 0; i < list.length; i++) {
      var l = String(list[i]).toLowerCase().split('-')[0];
      if (l === 'va') return 'ca';  // valenciano
      if (LOCALES[l]) return l;
    }
    return 'es';
  }
  var L = pick();

  /*DICT*/
  var K = {
"+{n} fechas": [
"+{n} data",
"+{n} dates",
"+{n} datas",
"+{n} dates"
],
"1 día": [
"Egun 1",
"1 dia",
"1 día",
"1 day"
],
"30 días": [
"30 egun",
"30 dies",
"30 días",
"30 days"
],
"7 días": [
"7 egun",
"7 dies",
"7 días",
"7 days"
],
"A mi calendario": [
"Nire egutegira",
"Al meu calendari",
"Ao meu calendario",
"To my calendar"
],
"Abrir en Planika": [
"Ireki Planikan",
"Obre a Planika",
"Abrir en Planika",
"Open in Planika"
],
"Activado": [
"Aktibatuta",
"Activat",
"Activado",
"On"
],
"Activar": [
"Aktibatu",
"Activa",
"Activar",
"Turn on"
],
"Actualizado": [
"Eguneratua",
"Actualitzat",
"Actualizado",
"Updated"
],
"Actualizado ayer a las {h}": [
"Eguneratua: atzo, {h}",
"Actualitzat ahir a les {h}",
"Actualizado onte ás {h}",
"Updated yesterday at {h}"
],
"Actualizado el {d} a las {h}": [
"Eguneratua: {d}, {h}",
"Actualitzat el {d} a les {h}",
"Actualizado o {d} ás {h}",
"Updated on {d} at {h}"
],
"Actualizado hoy a las {h}": [
"Eguneratua: gaur, {h}",
"Actualitzat avui a les {h}",
"Actualizado hoxe ás {h}",
"Updated today at {h}"
],
"Además, {x}.": [
"Gainera, {x}.",
"A més, {x}.",
"Ademais, {x}.",
"Also, {x}."
],
"Al lado: 1 o 2 min a pie": [
"Ondoan: oinez 1 edo 2 min",
"Al costat: 1 o 2 min a peu",
"Ao lado: 1 ou 2 min a pé",
"Next door: 1–2 min walk"
],
"Artista, obra, lugar, ciudad…": [
"Artista, lana, lekua, hiria…",
"Artista, obra, lloc, ciutat…",
"Artista, obra, lugar, cidade…",
"Artist, show, venue, town…"
],
"Aviso legal": [
"Lege-oharra",
"Avís legal",
"Aviso legal",
"Legal notice"
],
"Añade algo a tu plan primero": [
"Gehitu zerbait zure planera lehenik",
"Afegeix primer alguna cosa al teu pla",
"Engade primeiro algo ao teu plan",
"Add something to your plan first"
],
"Añadido a tu plan ({d})": [
"Zure planera gehituta ({d})",
"Afegit al teu pla ({d})",
"Engadido ao teu plan ({d})",
"Added to your plan ({d})"
],
"Añadir planes": [
"Gehitu planak",
"Afegeix plans",
"Engadir plans",
"Add plans"
],
"Borrar filtros": [
"Ezabatu iragazkiak",
"Esborra els filtres",
"Borrar filtros",
"Clear filters"
],
"Buscando…": [
"Bilatzen…",
"Cercant…",
"Buscando…",
"Locating…"
],
"Buscar": [
"Bilatu",
"Cerca",
"Buscar",
"Search"
],
"Buscar en Planika": [
"Bilatu Planikan",
"Cerca a Planika",
"Buscar en Planika",
"Search Planika"
],
"Buscar planes en Planika": [
"Bilatu planak Planikan",
"Cerca plans a Planika",
"Buscar plans en Planika",
"Search plans on Planika"
],
"Búsqueda avanzada": [
"Bilaketa aurreratua",
"Cerca avançada",
"Busca avanzada",
"Advanced search"
],
"Cada punto es un plan con ubicación conocida; los números agrupan planes cercanos. Haz zoom o pulsa un grupo para desplegarlo.": [
"Puntu bakoitza kokapen ezaguneko plan bat da; zenbakiek gertuko planak taldekatzen dituzte. Egin zoom edo sakatu talde bat zabaltzeko.",
"Cada punt és un pla amb ubicació coneguda; els números agrupen plans propers. Fes zoom o prem un grup per desplegar-lo.",
"Cada punto é un plan con localización coñecida; os números agrupan plans próximos. Fai zoom ou preme un grupo para despregalo.",
"Each dot is a plan with a known location; numbers group nearby plans. Zoom in or tap a group to expand it."
],
"Calendario": [
"Egutegia",
"Calendari",
"Calendario",
"Calendar"
],
"Calendario: elige tus días": [
"Egutegia: aukeratu zure egunak",
"Calendari: tria els teus dies",
"Calendario: escolle os teus días",
"Calendar: pick your days"
],
"Cargando el mapa…": [
"Mapa kargatzen…",
"Carregant el mapa…",
"Cargando o mapa…",
"Loading the map…"
],
"Cargando el plan… vuelve a pulsar en un momento": [
"Plana kargatzen… sakatu berriro pixka bat barru",
"Carregant el pla… torna a prémer d'aquí a un moment",
"Cargando o plan… volve premer nun momento",
"Loading the plan… tap again in a moment"
],
"Cerca de mí": [
"Nire inguruan",
"A prop meu",
"Preto de min",
"Near me"
],
"Cerrar": [
"Itxi",
"Tanca",
"Pechar",
"Close"
],
"Cerrar menú": [
"Itxi menua",
"Tanca el menú",
"Pechar menú",
"Close menu"
],
"Charlas, libros y talleres": [
"Hitzaldiak, liburuak eta tailerrak",
"Xerrades, llibres i tallers",
"Charlas, libros e obradoiros",
"Talks, books and workshops"
],
"Charlas, libros y talleres en toda España": [
"Hitzaldiak, liburuak eta tailerrak Espainia osoan",
"Xerrades, llibres i tallers a tot Espanya",
"Charlas, libros e obradoiros en toda España",
"Talks, books and workshops across Spain"
],
"Charlas, libros y talleres en {x}": [
"{x}: hitzaldiak, liburuak eta tailerrak",
"Xerrades, llibres i tallers a {x}",
"Charlas, libros e obradoiros en {x}",
"Talks, books and workshops in {x}"
],
"Cine": [
"Zinema",
"Cinema",
"Cine",
"Cinema"
],
"Cine en toda España": [
"Zinema Espainia osoan",
"Cinema a tot Espanya",
"Cine en toda España",
"Cinema across Spain"
],
"Cine en {x}": [
"{x}: zinema",
"Cinema a {x}",
"Cine en {x}",
"Cinema in {x}"
],
"Ciudad": [
"Herria",
"Ciutat",
"Cidade",
"Town"
],
"Cobertura por provincia": [
"Estaldura probintziaka",
"Cobertura per província",
"Cobertura por provincia",
"Coverage by province"
],
"Compartir": [
"Partekatu",
"Comparteix",
"Compartir",
"Share"
],
"Compartir (WhatsApp…)": [
"Partekatu (WhatsApp…)",
"Comparteix (WhatsApp…)",
"Compartir (WhatsApp…)",
"Share (WhatsApp…)"
],
"Compartir este plan": [
"Partekatu plan hau",
"Comparteix aquest pla",
"Compartir este plan",
"Share this plan"
],
"Comprueba siempre fechas, horarios y precios en la fuente original.": [
"Egiaztatu beti datak, ordutegiak eta prezioak jatorrizko iturrian.",
"Comprova sempre dates, horaris i preus a la font original.",
"Comproba sempre datas, horarios e prezos na fonte orixinal.",
"Always check dates, times and prices at the original source."
],
"Comunidad": [
"Erkidegoa",
"Comunitat",
"Comunidade",
"Region"
],
"Con niños": [
"Haurrekin",
"Amb nens",
"Con nenos",
"With kids"
],
"Con venta de entradas": [
"Sarrera-salmentarekin",
"Amb venda d'entrades",
"Con venda de entradas",
"With tickets on sale"
],
"Conciertos": [
"Kontzertuak",
"Concerts",
"Concertos",
"Concerts"
],
"Conciertos en toda España": [
"Kontzertuak Espainia osoan",
"Concerts a tot Espanya",
"Concertos en toda España",
"Concerts across Spain"
],
"Conciertos en {x}": [
"{x}: kontzertuak",
"Concerts a {x}",
"Concertos en {x}",
"Concerts in {x}"
],
"Configurar cookies": [
"Konfiguratu cookieak",
"Configura les galetes",
"Configurar cookies",
"Cookie settings"
],
"Contacto y promoción": [
"Harremanak eta sustapena",
"Contacte i promoció",
"Contacto e promoción",
"Contact and promotion"
],
"Copia el enlace:": [
"Kopiatu esteka:",
"Copia l'enllaç:",
"Copia a ligazón:",
"Copy the link:"
],
"Copiar enlace": [
"Kopiatu esteka",
"Copia l'enllaç",
"Copiar ligazón",
"Copy link"
],
"Cualquiera": [
"Edozein",
"Qualsevol",
"Calquera",
"Any"
],
"Cuándo": [
"Noiz",
"Quan",
"Cando",
"When"
],
"Código": [
"Kodea",
"Codi",
"Código",
"Code"
],
"Código en GitHub": [
"Kodea GitHub-en",
"Codi a GitHub",
"Código en GitHub",
"Code on GitHub"
],
"De {n}, solo los que tienen ubicación": [
"{n} guztietatik, kokapena dutenak bakarrik",
"De {n}, només els que tenen ubicació",
"De {n}, só os que teñen localización",
"Of {n}, only those with a location"
],
"Deporte": [
"Kirola",
"Esport",
"Deporte",
"Sport"
],
"Deporte en toda España": [
"Kirola Espainia osoan",
"Esport a tot Espanya",
"Deporte en toda España",
"Sport across Spain"
],
"Deporte en {x}": [
"{x}: kirola",
"Esport a {x}",
"Deporte en {x}",
"Sport in {x}"
],
"Descargar el plan (.ics)": [
"Deskargatu plana (.ics)",
"Descarrega el pla (.ics)",
"Descargar o plan (.ics)",
"Download the plan (.ics)"
],
"Desde": [
"Noiztik",
"Des de",
"Desde",
"From"
],
"Día de la nota": [
"Oharraren eguna",
"Dia de la nota",
"Día da nota",
"Note day"
],
"Dónde": [
"Non",
"On",
"Onde",
"Where"
],
"El mapa no ha podido cargarse (sin conexión a la librería de mapas).": [
"Ezin izan da mapa kargatu (ez dago konexiorik mapen liburutegiarekin).",
"No s'ha pogut carregar el mapa (sense connexió amb la biblioteca de mapes).",
"Non se puido cargar o mapa (sen conexión coa biblioteca de mapas).",
"The map couldn't load (no connection to the map library)."
],
"Empieza a la vez que el anterior": [
"Aurrekoaren ordu berean hasten da",
"Comença alhora que l'anterior",
"Comeza á vez que o anterior",
"Starts at the same time as the previous one"
],
"Empieza solo {n} min después del anterior": [
"Aurrekoa baino {n} min geroago bakarrik hasten da",
"Comença només {n} min després de l'anterior",
"Comeza só {n} min despois do anterior",
"Starts only {n} min after the previous one"
],
"En curso": [
"Martxan",
"En curs",
"En curso",
"Ongoing"
],
"En el mapa solo salen los planes de tu plan": [
"Mapan zure planeko planak bakarrik agertzen dira",
"Al mapa només surten els plans del teu pla",
"No mapa só saen os plans do teu plan",
"The map now shows only the plans in your plan"
],
"En el mismo sitio": [
"Leku berean",
"Al mateix lloc",
"No mesmo sitio",
"Same place"
],
"En tu plan": [
"Zure planean",
"Al teu pla",
"No teu plan",
"In your plan"
],
"En {x}": [
"{x}",
"A {x}",
"En {x}",
"In {x}"
],
"Enlace de tu plan copiado": [
"Zure planaren esteka kopiatuta",
"Enllaç del teu pla copiat",
"Ligazón do teu plan copiada",
"Your plan link copied"
],
"Enlace del plan copiado": [
"Planaren esteka kopiatuta",
"Enllaç del pla copiat",
"Ligazón do plan copiada",
"Plan link copied"
],
"Entrada gratuita": [
"Sarrera doan",
"Entrada gratuïta",
"Entrada de balde",
"Free entry"
],
"Entradas": [
"Sarrerak",
"Entrades",
"Entradas",
"Tickets"
],
"Entradas:": [
"Sarrerak:",
"Entrades:",
"Entradas:",
"Tickets:"
],
"Ese enlace de plan no se puede leer": [
"Planaren esteka hori ezin da irakurri",
"Aquest enllaç de pla no es pot llegir",
"Esa ligazón de plan non se pode ler",
"That plan link can't be read"
],
"Ese plan ya no está en la agenda": [
"Plan hori jada ez dago agendan",
"Aquest pla ja no és a l'agenda",
"Ese plan xa non está na axenda",
"That plan is no longer listed"
],
"Este día": [
"Egun honetan",
"Aquest dia",
"Este día",
"This day"
],
"Este fin de semana": [
"Asteburu honetan",
"Aquest cap de setmana",
"Esta fin de semana",
"This weekend"
],
"Este plan ya no está en la agenda": [
"Plan hau jada ez dago agendan",
"Aquest pla ja no és a l'agenda",
"Este plan xa non está na axenda",
"This plan is no longer listed"
],
"Exposiciones": [
"Erakusketak",
"Exposicions",
"Exposicións",
"Exhibitions"
],
"Exposiciones en toda España": [
"Erakusketak Espainia osoan",
"Exposicions a tot Espanya",
"Exposicións en toda España",
"Exhibitions across Spain"
],
"Exposiciones en {x}": [
"{x}: erakusketak",
"Exposicions a {x}",
"Exposicións en {x}",
"Exhibitions in {x}"
],
"Exposiciones y museos": [
"Erakusketak eta museoak",
"Exposicions i museus",
"Exposicións e museos",
"Exhibitions and museums"
],
"Exposiciones y museos en toda España": [
"Erakusketak eta museoak Espainia osoan",
"Exposicions i museus a tot Espanya",
"Exposicións e museos en toda España",
"Exhibitions and museums across Spain"
],
"Exposiciones y museos en {x}": [
"{x}: erakusketak eta museoak",
"Exposicions i museus a {x}",
"Exposicións e museos en {x}",
"Exhibitions and museums in {x}"
],
"Fechas:": [
"Datak:",
"Dates:",
"Datas:",
"Dates:"
],
"Fechas…": [
"Datak…",
"Dates…",
"Datas…",
"Dates…"
],
"Ferias, mercados y gastronomía": [
"Azokak, merkatuak eta gastronomia",
"Fires, mercats i gastronomia",
"Feiras, mercados e gastronomía",
"Fairs, markets and food"
],
"Ferias, mercados y gastronomía en toda España": [
"Azokak, merkatuak eta gastronomia Espainia osoan",
"Fires, mercats i gastronomia a tot Espanya",
"Feiras, mercados e gastronomía en toda España",
"Fairs, markets and food across Spain"
],
"Ferias, mercados y gastronomía en {x}": [
"{x}: azokak, merkatuak eta gastronomia",
"Fires, mercats i gastronomia a {x}",
"Feiras, mercados e gastronomía en {x}",
"Fairs, markets and food in {x}"
],
"Festivales": [
"Jaialdiak",
"Festivals",
"Festivais",
"Festivals"
],
"Festivales en España": [
"Jaialdiak Espainian",
"Festivals a Espanya",
"Festivais en España",
"Festivals in Spain"
],
"Fiestas y tradiciones": [
"Jaiak eta ohiturak",
"Festes i tradicions",
"Festas e tradicións",
"Festivities and traditions"
],
"Fiestas y tradiciones en toda España": [
"Jaiak eta ohiturak Espainia osoan",
"Festes i tradicions a tot Espanya",
"Festas e tradicións en toda España",
"Festivities and traditions across Spain"
],
"Fiestas y tradiciones en {x}": [
"{x}: jaiak eta ohiturak",
"Festes i tradicions a {x}",
"Festas e tradicións en {x}",
"Festivities and traditions in {x}"
],
"Filtros": [
"Iragazkiak",
"Filtres",
"Filtros",
"Filters"
],
"Fin de semana": [
"Asteburua",
"Cap de setmana",
"Fin de semana",
"Weekend"
],
"Fuente:": [
"Iturria:",
"Font:",
"Fonte:",
"Source:"
],
"Fuentes": [
"Iturriak",
"Fonts",
"Fontes",
"Sources"
],
"Fuentes de datos": [
"Datu-iturriak",
"Fonts de dades",
"Fontes de datos",
"Data sources"
],
"Gastronomía, ferias y mercados": [
"Gastronomia, azokak eta merkatuak",
"Gastronomia, fires i mercats",
"Gastronomía, feiras e mercados",
"Food, fairs and markets"
],
"Gastronomía, ferias y mercados en toda España": [
"Gastronomia, azokak eta merkatuak Espainia osoan",
"Gastronomia, fires i mercats a tot Espanya",
"Gastronomía, feiras e mercados en toda España",
"Food, fairs and markets across Spain"
],
"Gastronomía, ferias y mercados en {x}": [
"{x}: gastronomia, azokak eta merkatuak",
"Gastronomia, fires i mercats a {x}",
"Gastronomía, feiras e mercados en {x}",
"Food, fairs and markets in {x}"
],
"Gratis": [
"Doan",
"Gratuït",
"De balde",
"Free"
],
"Gratis, sin tienda de apps y funciona sin conexión": [
"Doan, aplikazio-dendarik gabe eta konexiorik gabe dabil",
"Gratis, sense botiga d'apps i funciona sense connexió",
"De balde, sen tenda de apps e funciona sen conexión",
"Free, no app store, works offline"
],
"Guardar en favoritos": [
"Gorde gogokoetan",
"Desa als preferits",
"Gardar en favoritos",
"Save to favourites"
],
"Hasta": [
"Noiz arte",
"Fins a",
"Ata",
"To"
],
"Hasta el {d}": [
"{d} arte",
"Fins al {d}",
"Ata o {d}",
"Until {d}"
],
"Hora de la nota": [
"Oharraren ordua",
"Hora de la nota",
"Hora da nota",
"Note time"
],
"Horario": [
"Ordutegia",
"Horari",
"Horario",
"Time of day"
],
"Hoy": [
"Gaur",
"Avui",
"Hoxe",
"Today"
],
"Idioma": [
"Hizkuntza",
"Idioma",
"Idioma",
"Language"
],
"Infantil y familiar": [
"Haurrak eta familia",
"Infantil i familiar",
"Infantil e familiar",
"Kids and family"
],
"Infantil y familiar en toda España": [
"Haurrak eta familia Espainia osoan",
"Infantil i familiar a tot Espanya",
"Infantil e familiar en toda España",
"Kids and family across Spain"
],
"Infantil y familiar en {x}": [
"{x}: haurrak eta familia",
"Infantil i familiar a {x}",
"Infantil e familiar en {x}",
"Kids and family in {x}"
],
"Inicio": [
"Hasiera",
"Inici",
"Inicio",
"Home"
],
"Instala Planika": [
"Instalatu Planika",
"Instal·la Planika",
"Instala Planika",
"Install Planika"
],
"Instala Planika en tu móvil": [
"Instalatu Planika zure mugikorrean",
"Instal·la Planika al mòbil",
"Instala Planika no teu móbil",
"Install Planika on your phone"
],
"Lista": [
"Zerrenda",
"Llista",
"Lista",
"List"
],
"Los datos proceden de portales de datos abiertos y APIs públicas.": [
"Datuak datu irekien atarietatik eta API publikoetatik datoz.",
"Les dades provenen de portals de dades obertes i API públiques.",
"Os datos proceden de portais de datos abertos e API públicas.",
"Data comes from open data portals and public APIs."
],
"Mapa": [
"Mapa",
"Mapa",
"Mapa",
"Map"
],
"Mapa de planes": [
"Planen mapa",
"Mapa de plans",
"Mapa de plans",
"Map of plans"
],
"Mañana (antes de 14:00)": [
"Goiza (14:00 baino lehen)",
"Matí (abans de les 14:00)",
"Mañá (antes das 14:00)",
"Morning (before 14:00)"
],
"Menú": [
"Menua",
"Menú",
"Menú",
"Menu"
],
"Menú de Planika": [
"Planikaren menua",
"Menú de Planika",
"Menú de Planika",
"Planika menu"
],
"Mes anterior": [
"Aurreko hilabetea",
"Mes anterior",
"Mes anterior",
"Previous month"
],
"Mes siguiente": [
"Hurrengo hilabetea",
"Mes següent",
"Mes seguinte",
"Next month"
],
"Mi Planika": [
"Nire Planika",
"La meva Planika",
"A miña Planika",
"My Planika"
],
"Mi plan": [
"Nire plana",
"El meu pla",
"O meu plan",
"My plan"
],
"Migas de pan": [
"Nabigazio-bidea",
"Ruta de navegació",
"Ruta de navegación",
"Breadcrumbs"
],
"Mis favoritos": [
"Nire gogokoak",
"Els meus preferits",
"Os meus favoritos",
"My favourites"
],
"Mostrar más": [
"Erakutsi gehiago",
"Mostra'n més",
"Amosar máis",
"Show more"
],
"Mostrar más ({a} de {b} restantes)": [
"Erakutsi gehiago ({a}; {b} falta dira)",
"Mostra'n més ({a} de {b} restants)",
"Amosar máis ({a} de {b} restantes)",
"Show more ({a} of {b} remaining)"
],
"Más info": [
"Informazio gehiago",
"Més info",
"Máis info",
"More info"
],
"Más información:": [
"Informazio gehiago:",
"Més informació:",
"Máis información:",
"More information:"
],
"Más planes": [
"Plan gehiago",
"Més plans",
"Máis plans",
"More plans"
],
"Más tipos": [
"Mota gehiago",
"Més tipus",
"Máis tipos",
"More types"
],
"Música y conciertos": [
"Musika eta kontzertuak",
"Música i concerts",
"Música e concertos",
"Music and concerts"
],
"Música y conciertos en toda España": [
"Musika eta kontzertuak Espainia osoan",
"Música i concerts a tot Espanya",
"Música e concertos en toda España",
"Music and concerts across Spain"
],
"Música y conciertos en {x}": [
"{x}: musika eta kontzertuak",
"Música i concerts a {x}",
"Música e concertos en {x}",
"Music and concerts in {x}"
],
"Nada registrado ese día con los filtros actuales.": [
"Ez dago ezer egun horretan uneko iragazkiekin.",
"No hi ha res aquest dia amb els filtres actuals.",
"Non hai nada ese día cos filtros actuais.",
"Nothing listed that day with the current filters."
],
"Nada registrado esos días con los filtros actuales.": [
"Ez dago ezer egun horietan uneko iragazkiekin.",
"No hi ha res aquests dies amb els filtres actuals.",
"Non hai nada eses días cos filtros actuais.",
"Nothing listed on those days with the current filters."
],
"Naturaleza, rutas y visitas": [
"Natura, ibilbideak eta bisitak",
"Natura, rutes i visites",
"Natureza, rutas e visitas",
"Nature, routes and tours"
],
"Naturaleza, rutas y visitas en toda España": [
"Natura, ibilbideak eta bisitak Espainia osoan",
"Natura, rutes i visites a tot Espanya",
"Natureza, rutas e visitas en toda España",
"Nature, routes and tours across Spain"
],
"Naturaleza, rutas y visitas en {x}": [
"{x}: natura, ibilbideak eta bisitak",
"Natura, rutes i visites a {x}",
"Natureza, rutas e visitas en {x}",
"Nature, routes and tours in {x}"
],
"Navidad": [
"Gabonak",
"Nadal",
"Nadal",
"Christmas"
],
"Navidad en toda España": [
"Gabonak Espainia osoan",
"Nadal a tot Espanya",
"Nadal en toda España",
"Christmas across Spain"
],
"Navidad en {x}": [
"{x}: gabonak",
"Nadal a {x}",
"Nadal en {x}",
"Christmas in {x}"
],
"Ningún lugar con planes empieza por «{x}»": [
"Ez dago «{x}» hizkiekin hasten den lekurik",
"Cap lloc amb plans comença per «{x}»",
"Ningún lugar con plans comeza por «{x}»",
"No place with plans starts with «{x}»"
],
"No hay planes con esos filtros. Prueba a ampliar las fechas o quitar algún filtro.": [
"Ez dago planik iragazki horiekin. Zabaldu datak edo kendu iragazkiren bat.",
"No hi ha plans amb aquests filtres. Prova d'ampliar les dates o treure algun filtre.",
"Non hai plans con eses filtros. Proba a ampliar as datas ou quitar algún filtro.",
"No plans match those filters. Try widening the dates or removing a filter."
],
"No se ha podido obtener tu ubicación": [
"Ezin izan da zure kokapena lortu",
"No s'ha pogut obtenir la teva ubicació",
"Non se puido obter a túa localización",
"Couldn't get your location"
],
"Noche (desde 20:00)": [
"Gaua (20:00etatik aurrera)",
"Nit (des de les 20:00)",
"Noite (desde as 20:00)",
"Evening (from 20:00)"
],
"Nombre del plan": [
"Planaren izena",
"Nom del pla",
"Nome do plan",
"Plan name"
],
"Nota": [
"Oharra",
"Nota",
"Nota",
"Note"
],
"Nota de tu plan": [
"Zure planeko oharra",
"Nota del teu pla",
"Nota do teu plan",
"Note from your plan"
],
"Nota: comer, quedar en el bar…": [
"Oharra: bazkaldu, tabernan geratu…",
"Nota: dinar, quedar al bar…",
"Nota: xantar, quedar no bar…",
"Note: lunch, meet at the bar…"
],
"Otras fechas:": [
"Beste data batzuk:",
"Altres dates:",
"Outras datas:",
"Other dates:"
],
"Otras páginas": [
"Beste orri batzuk",
"Altres pàgines",
"Outras páxinas",
"Other pages"
],
"Otros planes": [
"Beste plan batzuk",
"Altres plans",
"Outros plans",
"Other plans"
],
"Otros planes en toda España": [
"Beste plan batzuk Espainia osoan",
"Altres plans a tot Espanya",
"Outros plans en toda España",
"Other plans across Spain"
],
"Otros planes en {x}": [
"{x}: beste plan batzuk",
"Altres plans a {x}",
"Outros plans en {x}",
"Other plans in {x}"
],
"Para adultos": [
"Helduentzat",
"Per a adults",
"Para adultos",
"For adults"
],
"Permanente": [
"Iraunkorra",
"Permanent",
"Permanente",
"Permanent"
],
"Plan que ya no está": [
"Jada ez dagoen plana",
"Pla que ja no hi és",
"Plan que xa non está",
"Plan no longer listed"
],
"Planes cerca de mí": [
"Planak nire inguruan",
"Plans a prop meu",
"Plans preto de min",
"Plans near me"
],
"Planes con niños": [
"Haurrekin egiteko planak",
"Plans amb nens",
"Plans con nenos",
"Plans with kids"
],
"Planes con niños en toda España": [
"Haurrekin egiteko planak Espainia osoan",
"Plans amb nens a tot Espanya",
"Plans con nenos en toda España",
"Plans with kids across Spain"
],
"Planes con niños en {x}": [
"{x}: haurrekin egiteko planak",
"Plans amb nens a {x}",
"Plans con nenos en {x}",
"Plans with kids in {x}"
],
"Planes de Navidad": [
"Gabonetako planak",
"Plans de Nadal",
"Plans de Nadal",
"Christmas plans"
],
"Planes de Navidad en toda España": [
"Gabonetako planak Espainia osoan",
"Plans de Nadal a tot Espanya",
"Plans de Nadal en toda España",
"Christmas plans across Spain"
],
"Planes de Navidad en {x}": [
"{x}: gabonetako planak",
"Plans de Nadal a {x}",
"Plans de Nadal en {x}",
"Christmas plans in {x}"
],
"Planes de ocio en toda España": [
"Aisialdi-planak Espainia osoan",
"Plans d'oci a tot Espanya",
"Plans de lecer en toda España",
"Things to do across Spain"
],
"Planes destacados": [
"Plan nabarmenak",
"Plans destacats",
"Plans destacados",
"Featured plans"
],
"Planes destacados:": [
"Plan nabarmenak:",
"Plans destacats:",
"Plans destacados:",
"Featured plans:"
],
"Planes en toda España": [
"Planak Espainia osoan",
"Plans a tot Espanya",
"Plans en toda España",
"Plans across Spain"
],
"Planes en {x}": [
"{x}: planak",
"Plans a {x}",
"Plans en {x}",
"Plans in {x}"
],
"Planes este fin de semana": [
"Asteburuko planak",
"Plans aquest cap de setmana",
"Plans esta fin de semana",
"Plans this weekend"
],
"Planes este fin de semana en España": [
"Asteburuko planak Espainian",
"Plans aquest cap de setmana a Espanya",
"Plans esta fin de semana en España",
"Plans this weekend in Spain"
],
"Planes este fin de semana en toda España": [
"Asteburuko planak Espainia osoan",
"Plans aquest cap de setmana a tot Espanya",
"Plans esta fin de semana en toda España",
"Plans this weekend across Spain"
],
"Planes este fin de semana en {x}": [
"{x}: asteburuko planak",
"Plans aquest cap de setmana a {x}",
"Plans esta fin de semana en {x}",
"Plans this weekend in {x}"
],
"Planes gratis": [
"Doako planak",
"Plans gratuïts",
"Plans de balde",
"Free plans"
],
"Planes gratis en toda España": [
"Doako planak Espainia osoan",
"Plans gratuïts a tot Espanya",
"Plans de balde en toda España",
"Free plans across Spain"
],
"Planes gratis en {x}": [
"{x}: doako planak",
"Plans gratuïts a {x}",
"Plans de balde en {x}",
"Free plans in {x}"
],
"Planes para hoy en España": [
"Gaurko planak Espainian",
"Plans per avui a Espanya",
"Plans para hoxe en España",
"Plans for today in Spain"
],
"Planes parecidos próximos": [
"Antzeko plan hurbilak",
"Plans semblants propers",
"Plans parecidos próximos",
"Similar upcoming plans"
],
"Planika, inicio": [
"Planika, hasiera",
"Planika, inici",
"Planika, inicio",
"Planika, home"
],
"Ponle nombre: Sábado en Bilbao": [
"Jarri izena: Larunbata Bilbon",
"Posa-li nom: Dissabte a Bilbao",
"Ponlle nome: Sábado en Bilbao",
"Name it: Saturday in Bilbao"
],
"Por provincia": [
"Probintziaka",
"Per província",
"Por provincia",
"By province"
],
"Precio máx. (€)": [
"Gehieneko prezioa (€)",
"Preu màx. (€)",
"Prezo máx. (€)",
"Max. price (€)"
],
"Precio:": [
"Prezioa:",
"Preu:",
"Prezo:",
"Price:"
],
"Privacidad": [
"Pribatutasuna",
"Privadesa",
"Privacidade",
"Privacy"
],
"Privacidad y cookies": [
"Pribatutasuna eta cookieak",
"Privadesa i galetes",
"Privacidade e cookies",
"Privacy and cookies"
],
"Provincia": [
"Probintzia",
"Província",
"Provincia",
"Province"
],
"Publica tu evento": [
"Argitaratu zure ekitaldia",
"Publica el teu esdeveniment",
"Publica o teu evento",
"Publish your event"
],
"Publica tu evento gratis": [
"Argitaratu zure ekitaldia doan",
"Publica el teu esdeveniment gratis",
"Publica o teu evento de balde",
"Publish your event for free"
],
"Puede que se haya cancelado o que ya haya pasado": [
"Baliteke bertan behera geratu izana edo dagoeneko pasatu izana",
"Potser s'ha cancel·lat o ja ha passat",
"Pode que se cancelase ou que xa pasase",
"It may have been cancelled or already happened"
],
"Puente de diciembre": [
"Abenduko zubia",
"Pont de desembre",
"Ponte de decembro",
"December long weekend"
],
"Encendido de luces de Navidad": [
"Gabonetako argiak piztea",
"Encesa de llums de Nadal",
"Acendido das luces de Nadal",
"Christmas lights switch-on"
],
"Cabalgatas de Reyes": [
"Errege Magoen kabalkadak",
"Cavalcades de Reis",
"Cabalgatas de Reis",
"Three Kings parades"
],
"Nochevieja y Año Nuevo": [
"Urtezahar eta Urteberri",
"Cap d'Any i Any Nou",
"Noitevella e Aninovo",
"New Year's Eve and New Year"
],
"Páginas por provincia y tipo de plan:": [
"Orriak probintziaka eta plan motaka:",
"Pàgines per província i tipus de pla:",
"Páxinas por provincia e tipo de plan:",
"Pages by province and type of plan:"
],
"Público": [
"Publikoa",
"Públic",
"Público",
"Audience"
],
"Quitado de tu plan": [
"Zure planetik kenduta",
"Tret del teu pla",
"Quitado do teu plan",
"Removed from your plan"
],
"Quitar": [
"Kendu",
"Treu",
"Quitar",
"Remove"
],
"Quitar del plan": [
"Kendu planetik",
"Treu del pla",
"Quitar do plan",
"Remove from plan"
],
"Quitar día": [
"Kendu eguna",
"Treu el dia",
"Quitar día",
"Remove day"
],
"Quitar días": [
"Kendu egunak",
"Treu els dies",
"Quitar días",
"Remove days"
],
"Quitar el lugar (toda España)": [
"Kendu lekua (Espainia osoa)",
"Treu el lloc (tot Espanya)",
"Quitar o lugar (toda España)",
"Clear the place (all of Spain)"
],
"Quitar nota": [
"Kendu oharra",
"Treu la nota",
"Quitar nota",
"Remove note"
],
"Qué": [
"Zer",
"Què",
"Que",
"What"
],
"Qué hacer hoy": [
"Zer egin gaur",
"Què fer avui",
"Que facer hoxe",
"What to do today"
],
"RSS del boletín": [
"Buletinaren RSSa",
"RSS del butlletí",
"RSS do boletín",
"Newsletter RSS"
],
"Radio en km": [
"Erradioa km-tan",
"Radi en km",
"Radio en km",
"Radius in km"
],
"Rutas y visitas guiadas": [
"Ibilbideak eta bisita gidatuak",
"Rutes i visites guiades",
"Rutas e visitas guiadas",
"Routes and guided tours"
],
"Rutas y visitas guiadas en toda España": [
"Ibilbideak eta bisita gidatuak Espainia osoan",
"Rutes i visites guiades a tot Espanya",
"Rutas e visitas guiadas en toda España",
"Routes and guided tours across Spain"
],
"Rutas y visitas guiadas en {x}": [
"{x}: ibilbideak eta bisita gidatuak",
"Rutes i visites guiades a {x}",
"Rutas e visitas guiadas en {x}",
"Routes and guided tours in {x}"
],
"Sin conexión: ves los planes de tu última visita": [
"Konexiorik gabe: zure azken bisitako planak ikusten ari zara",
"Sense connexió: veus els plans de la darrera visita",
"Sen conexión: ves os plans da túa última visita",
"Offline: you're seeing plans from your last visit"
],
"Sin filtro de lugar": [
"Lekuaren iragazkirik gabe",
"Sense filtre de lloc",
"Sen filtro de lugar",
"No place filter"
],
"Sin límite": [
"Mugarik gabe",
"Sense límit",
"Sen límite",
"No limit"
],
"Solo favoritos": [
"Gogokoak bakarrik",
"Només preferits",
"Só favoritos",
"Favourites only"
],
"Síguenos en Instagram": [
"Jarrai gaitzazu Instagramen",
"Segueix-nos a Instagram",
"Síguenos en Instagram",
"Follow us on Instagram"
],
"Tarde (14:00 a 20:00)": [
"Arratsaldea (14:00-20:00)",
"Tarda (de 14:00 a 20:00)",
"Tarde (das 14:00 ás 20:00)",
"Afternoon (14:00 to 20:00)"
],
"Te han compartido este plan.": [
"Plan hau partekatu dizute.",
"T'han compartit aquest pla.",
"Compartiron contigo este plan.",
"Someone shared this plan with you."
],
"Teatro y danza": [
"Antzerkia eta dantza",
"Teatre i dansa",
"Teatro e danza",
"Theatre and dance"
],
"Teatro y danza en toda España": [
"Antzerkia eta dantza Espainia osoan",
"Teatre i dansa a tot Espanya",
"Teatro e danza en toda España",
"Theatre and dance across Spain"
],
"Teatro y danza en {x}": [
"{x}: antzerkia eta dantza",
"Teatre i dansa a {x}",
"Teatro e danza en {x}",
"Theatre and dance in {x}"
],
"Tipo de plan": [
"Plan mota",
"Tipus de pla",
"Tipo de plan",
"Type of plan"
],
"Toda España": [
"Espainia osoa",
"Tot Espanya",
"Toda España",
"All of Spain"
],
"Toda España · escribe un lugar": [
"Espainia osoa · idatzi leku bat",
"Tot Espanya · escriu un lloc",
"Toda España · escribe un lugar",
"All of Spain · type a place"
],
"Todas": [
"Guztiak",
"Totes",
"Todas",
"All"
],
"Todo": [
"Dena",
"Tot",
"Todo",
"All"
],
"Todo el día": [
"Egun osoa",
"Tot el dia",
"Todo o día",
"All day"
],
"Todos": [
"Guztiak",
"Tots",
"Todos",
"All"
],
"Todos los planes en toda España": [
"Plan guztiak Espainia osoan",
"Tots els plans a tot Espanya",
"Todos os plans en toda España",
"All plans across Spain"
],
"Todos los planes en {x}": [
"{x}: plan guztiak",
"Tots els plans a {x}",
"Todos os plans en {x}",
"All plans in {x}"
],
"Todos los tipos de plan": [
"Plan mota guztiak",
"Tots els tipus de pla",
"Todos os tipos de plan",
"All types of plan"
],
"Tu navegador no permite obtener la ubicación": [
"Zure nabigatzaileak ez du kokapena lortzen uzten",
"El teu navegador no permet obtenir la ubicació",
"O teu navegador non permite obter a localización",
"Your browser can't get your location"
],
"Tu plan está vacío. Pulsa «＋ Mi plan» en cualquier plan de la lista o de su ficha y aparecerá aquí, ordenado por hora.": [
"Zure plana hutsik dago. Sakatu «＋ Nire plana» zerrendako edo fitxako edozein planetan, eta hemen agertuko da, orduaren arabera ordenatuta.",
"El teu pla és buit. Prem «＋ El meu pla» en qualsevol pla de la llista o de la seva fitxa i apareixerà aquí, ordenat per hora.",
"O teu plan está baleiro. Preme «＋ O meu plan» en calquera plan da lista ou da súa ficha e aparecerá aquí, ordenado por hora.",
"Your plan is empty. Tap «＋ My plan» on any plan in the list or on its page and it will show up here, sorted by time."
],
"Tu ubicación": [
"Zure kokapena",
"La teva ubicació",
"A túa localización",
"Your location"
],
"Usar mi ubicación": [
"Erabili nire kokapena",
"Fes servir la meva ubicació",
"Usar a miña localización",
"Use my location"
],
"Ver en el mapa": [
"Ikusi mapan",
"Mostra al mapa",
"Ver no mapa",
"See on the map"
],
"Ver en la lista": [
"Ikusi zerrendan",
"Mostra a la llista",
"Ver na lista",
"See in the list"
],
"Ver ficha": [
"Ikusi fitxa",
"Mostra la fitxa",
"Ver ficha",
"View details"
],
"Ver las fuentes de datos": [
"Ikusi datu-iturriak",
"Mostra les fonts de dades",
"Ver as fontes de datos",
"See the data sources"
],
"Verlos en la lista": [
"Ikusi zerrendan",
"Mostra'ls a la llista",
"Velos na lista",
"See them in the list"
],
"Visita permanente": [
"Bisita iraunkorra",
"Visita permanent",
"Visita permanente",
"Permanent visit"
],
"Visita permanente, sin una fecha única. Este aviso es un recordatorio de un día.": [
"Bisita iraunkorra, data jakinik gabe. Ohar hau egun bateko oroigarria da.",
"Visita permanent, sense una data única. Aquest avís és un recordatori d'un dia.",
"Visita permanente, sen unha data única. Este aviso é un recordatorio dun día.",
"Permanent visit with no single date. This entry is a one-day reminder."
],
"a menos de {n} km": [
"{n} km baino gutxiagora",
"a menys de {n} km",
"a menos de {n} km",
"within {n} km"
],
"a {n} km": [
"{n} km-ra",
"a {n} km",
"a {n} km",
"{n} km away"
],
"a {n} km: mejor en transporte": [
"{n} km-ra: hobe garraioan",
"a {n} km: millor en transport",
"a {n} km: mellor en transporte",
"{n} km away: better by transport"
],
"al {d}": [
"– {d}",
"al {d}",
"ao {d}",
"to {d}"
],
"con venta de entradas": [
"sarrera-salmentarekin",
"amb venda d'entrades",
"con venda de entradas",
"with tickets on sale"
],
"de {n}": [
"guztira {n}",
"de {n}",
"de {n}",
"of {n}"
],
"del {d}": [
"{d}",
"del {d}",
"do {d}",
"from {d}"
],
"desde hoy": [
"gaurtik",
"des d'avui",
"desde hoxe",
"from today"
],
"en curso": [
"martxan",
"en curs",
"en curso",
"ongoing"
],
"en el mapa": [
"mapan",
"al mapa",
"no mapa",
"on the map"
],
"en los próximos 30 días": [
"hurrengo 30 egunetan",
"els propers 30 dies",
"nos próximos 30 días",
"in the next 30 days"
],
"en los próximos 7 días": [
"hurrengo 7 egunetan",
"els propers 7 dies",
"nos próximos 7 días",
"in the next 7 days"
],
"en {x}": [
"{x}",
"a {x}",
"en {x}",
"in {x}"
],
"este fin de semana": [
"asteburu honetan",
"aquest cap de setmana",
"esta fin de semana",
"this weekend"
],
"hasta {n} €": [
"gehienez {n} €",
"fins a {n} €",
"ata {n} €",
"up to {n} €"
],
"hoy": [
"gaur",
"avui",
"hoxe",
"today"
],
"infantil y familiar": [
"haurrak eta familia",
"infantil i familiar",
"infantil e familiar",
"kids and family"
],
"para adultos": [
"helduentzat",
"per a adults",
"para adultos",
"for adults"
],
"plan": [
"plan",
"pla",
"plan",
"plan"
],
"planes": [
"plan",
"plans",
"plans",
"plans"
],
"por la mañana": [
"goizez",
"al matí",
"pola mañá",
"in the morning"
],
"por la noche": [
"gauez",
"a la nit",
"pola noite",
"in the evening"
],
"por la tarde": [
"arratsaldez",
"a la tarda",
"pola tarde",
"in the afternoon"
],
"sin datos": [
"daturik ez",
"sense dades",
"sen datos",
"no data"
],
"solo favoritos": [
"gogokoak bakarrik",
"només preferits",
"só favoritos",
"favourites only"
],
"solo tu plan": [
"zure plana bakarrik",
"només el teu pla",
"só o teu plan",
"your plan only"
],
"toda España": [
"Espainia osoa",
"tot Espanya",
"toda España",
"all of Spain"
],
"unos {n} min a pie": [
"oinez {n} min inguru",
"uns {n} min a peu",
"uns {n} min a pé",
"about a {n} min walk"
],
"vía Planika": [
"Planikaren bidez",
"via Planika",
"vía Planika",
"via Planika"
],
"y": [
"eta",
"i",
"e",
"and"
],
"y {n} más": [
"eta beste {n}",
"i {n} més",
"e {n} máis",
"and {n} more"
],
"{n} días": [
"{n} egun",
"{n} dies",
"{n} días",
"{n} days"
],
"{n} días elegidos: {x}": [
"{n} egun aukeratuta: {x}",
"{n} dies triats: {x}",
"{n} días escollidos: {x}",
"{n} days selected: {x}"
],
"{n} plan de larga duración (exposiciones, temporadas…)": [
"iraupen luzeko {n} plan (erakusketak, denboraldiak…)",
"{n} pla de llarga durada (exposicions, temporades…)",
"{n} plan de longa duración (exposicións, tempadas…)",
"{n} long-running plan (exhibitions, seasons…)"
],
"{n} planes de larga duración (exposiciones, temporadas…)": [
"iraupen luzeko {n} plan (erakusketak, denboraldiak…)",
"{n} plans de llarga durada (exposicions, temporades…)",
"{n} plans de longa duración (exposicións, tempadas…)",
"{n} long-running plans (exhibitions, seasons…)"
],
"{n} planes del {a} al {b}": [
"{n} plan ({a} – {b})",
"{n} plans del {a} al {b}",
"{n} plans do {a} ao {b}",
"{n} plans from {a} to {b}"
],
"{n} visita permanente": [
"{n} bisita iraunkor",
"{n} visita permanent",
"{n} visita permanente",
"{n} permanent visit"
],
"{n} visitas permanentes": [
"{n} bisita iraunkor",
"{n} visites permanents",
"{n} visitas permanentes",
"{n} permanent visits"
],
"¡Planika instalada! Ya la tienes en tu pantalla de inicio": [
"Planika instalatuta! Hasierako pantailan duzu jada",
"Planika instal·lada! Ja la tens a la pantalla d'inici",
"Planika instalada! Xa a tes na pantalla de inicio",
"Planika installed! It's now on your home screen"
],
"¿Buscas un plan?": [
"Plan baten bila?",
"Busques un pla?",
"Buscas un plan?",
"Looking for a plan?"
],
"¿Organizas un evento? Publícalo gratis en Planika": [
"Ekitaldi bat antolatzen duzu? Argitaratu doan Planikan",
"Organitzes un esdeveniment? Publica'l gratis a Planika",
"Organizas un evento? Publícao de balde en Planika",
"Organising an event? Publish it for free on Planika"
],
"Ábrelo en Planika:": [
"Ireki Planikan:",
"Obre'l a Planika:",
"Ábreo en Planika:",
"Open it in Planika:"
],
"… y {n} más. Pulsa «Ver en la lista» para verlos todos.": [
"… eta beste {n}. Sakatu «Ikusi zerrendan» guztiak ikusteko.",
"… i {n} més. Prem «Mostra a la llista» per veure'ls tots.",
"… e {n} máis. Preme «Ver na lista» para velos todos.",
"… and {n} more. Tap «See in the list» to see them all."
],
"Mis planes": [
"Nire planak",
"Els meus plans",
"Os meus plans",
"My plans"
],
"Crea varios planes y comparte cada uno con quien vaya.": [
"Sortu hainbat plan eta partekatu bakoitza joango denarekin.",
"Crea diversos plans i comparteix-ne cadascun amb qui hi vagi.",
"Crea varios plans e comparte cada un con quen vaia.",
"Make several plans and share each one with whoever is going."
],
"Nuevo plan": [
"Plan berria",
"Pla nou",
"Plan novo",
"New plan"
],
"¿A qué plan lo añades?": [
"Zein planetara gehitu nahi duzu?",
"A quin pla l'afegeixes?",
"A que plan o engades?",
"Which plan should it go in?"
],
"Nuevo plan con este": [
"Plan berria honekin",
"Pla nou amb aquest",
"Plan novo con este",
"New plan with this one"
],
"Duplicar": [
"Bikoiztu",
"Duplica",
"Duplicar",
"Duplicate"
],
"Borrar plan": [
"Ezabatu plana",
"Esborra el pla",
"Borrar plan",
"Delete plan"
],
"Guardar en Mis planes": [
"Gorde nire planetan",
"Desa als meus plans",
"Gardar nos meus plans",
"Save to My plans"
],
"Guardado en Mis planes": [
"Nire planetan gordeta",
"Desat als meus plans",
"Gardado nos meus plans",
"Saved to My plans"
],
"Plan sin nombre": [
"Izenik gabeko plana",
"Pla sense nom",
"Plan sen nome",
"Untitled plan"
],
"En {n} planes": [
"{n} planetan",
"En {n} plans",
"En {n} plans",
"In {n} plans"
],
"Quitado de «{p}»": [
"«{p}» planetik kenduta",
"Tret de «{p}»",
"Quitado de «{p}»",
"Removed from “{p}”"
],
"Añadido a «{p}» ({d})": [
"«{p}» planera gehituta ({d})",
"Afegit a «{p}» ({d})",
"Engadido a «{p}» ({d})",
"Added to “{p}” ({d})"
],
"Ya tienes {n} planes: borra alguno para crear otro": [
"Dagoeneko {n} plan dituzu: ezabatu bat beste bat sortzeko",
"Ja tens {n} plans: esborra'n algun per crear-ne un altre",
"Xa tes {n} plans: borra algún para crear outro",
"You already have {n} plans: delete one to make another"
],
"1 plan": [
"Plan 1",
"1 pla",
"1 plan",
"1 plan"
],
"{n} planes": [
"{n} plan",
"{n} plans",
"{n} plans",
"{n} plans"
],
"1 nota": [
"Ohar 1",
"1 nota",
"1 nota",
"1 note"
],
"{n} notas": [
"{n} ohar",
"{n} notes",
"{n} notas",
"{n} notes"
],
"Vacío": [
"Hutsik",
"Buit",
"Baleiro",
"Empty"
],
"Ya está: tócalo para quitarlo": [
"Hemen dago jada: sakatu kentzeko",
"Ja hi és: toca'l per treure'l",
"Xa está: tócao para quitalo",
"Already in: tap to remove it"
],
"Aún no tienes ningún plan. Crea uno o pulsa «＋ Mi plan» en cualquier plan de la agenda.": [
"Oraindik ez duzu planik. Sortu bat edo sakatu «＋ Nire plana» agendako edozein planetan.",
"Encara no tens cap pla. Crea'n un o prem «＋ El meu pla» en qualsevol pla de l'agenda.",
"Aínda non tes ningún plan. Crea un ou preme «＋ O meu plan» en calquera plan da axenda.",
"You have no plans yet. Make one or tap «＋ My plan» on any plan in the listings."
],
"Pasados ({n})": [
"Iraganak ({n})",
"Passats ({n})",
"Pasados ({n})",
"Past ({n})"
],
"{p} (copia)": [
"{p} (kopia)",
"{p} (còpia)",
"{p} (copia)",
"{p} (copy)"
],
"¿Borrar el plan «{p}»?": [
"«{p}» plana ezabatu?",
"Vols esborrar el pla «{p}»?",
"Borrar o plan «{p}»?",
"Delete the plan “{p}”?"
],
"En el mapa solo salen los planes de «{p}»": [
"Mapan «{p}» planekoak bakarrik agertzen dira",
"Al mapa només surten els plans de «{p}»",
"No mapa só saen os plans de «{p}»",
"The map only shows what is in “{p}”"
],
"Con aviso 2 horas antes de cada plan": [
"Abisua plan bakoitza baino 2 ordu lehenago",
"Amb avís 2 hores abans de cada pla",
"Con aviso 2 horas antes de cada plan",
"With a reminder 2 hours before each plan"
],
"Todo el plan de una vez: iPhone, Android, Apple Calendar y Outlook": [
"Plan osoa batera: iPhone, Android, Apple Calendar eta Outlook",
"Tot el pla d'una vegada: iPhone, Android, Apple Calendar i Outlook",
"Todo o plan dunha vez: iPhone, Android, Apple Calendar e Outlook",
"The whole plan at once: iPhone, Android, Apple Calendar and Outlook"
],
"En Android: abre el archivo descargado y elige Google Calendar": [
"Androiden: ireki deskargatutako fitxategia eta aukeratu Google Calendar",
"A Android: obre el fitxer baixat i tria Google Calendar",
"En Android: abre o ficheiro descargado e escolle Google Calendar",
"On Android: open the downloaded file and choose Google Calendar"
],
"O con Google Calendar, un toque por plan": [
"Edo Google Calendar-ekin, ukitu bat plan bakoitzeko",
"O amb Google Calendar, un toc per pla",
"Ou con Google Calendar, un toque por plan",
"Or with Google Calendar, one tap per plan"
],
"Con Google Calendar, un toque por plan": [
"Google Calendar-ekin, ukitu bat plan bakoitzeko",
"Amb Google Calendar, un toc per pla",
"Con Google Calendar, un toque por plan",
"With Google Calendar, one tap per plan"
],
"Calendario del móvil (.ics)": [
"Mugikorreko egutegia (.ics)",
"Calendari del mòbil (.ics)",
"Calendario do móbil (.ics)",
"Phone calendar (.ics)"
],
"Síguenos en Instagram: @planikaapp": [
"Jarraitu gaitzazu Instagramen: @planikaapp",
"Segueix-nos a Instagram: @planikaapp",
"Síguenos en Instagram: @planikaapp",
"Follow us on Instagram: @planikaapp"
],
"Pegar un enlace de Planika": [
"Itsatsi Planikako esteka bat",
"Enganxa un enllaç de Planika",
"Pegar unha ligazón de Planika",
"Paste a Planika link"
],
"Pega aquí el enlace que te han mandado": [
"Itsatsi hemen bidali dizuten esteka",
"Enganxa aquí l'enllaç que t'han enviat",
"Pega aquí a ligazón que che mandaron",
"Paste the link you were sent here"
],
"Enlace de Planika": [
"Planikako esteka",
"Enllaç de Planika",
"Ligazón de Planika",
"Planika link"
],
"Abrir": [
"Ireki",
"Obre",
"Abrir",
"Open"
],
"Ese enlace no es de un plan de Planika": [
"Esteka hori ez da Planikako plan batena",
"Aquest enllaç no és d'un pla de Planika",
"Esa ligazón non é dun plan de Planika",
"That link isn't a Planika plan"
],
"¿Usas Planika desde la pantalla de inicio? Copia este enlace y pégalo allí, en «Mis planes».": [
"Planika hasierako pantailatik erabiltzen duzu? Kopiatu esteka hau eta itsatsi han, «Nire planak» atalean.",
"Fas servir Planika des de la pantalla d'inici? Copia aquest enllaç i enganxa'l allà, a «Els meus plans».",
"Usas Planika desde a pantalla de inicio? Copia esta ligazón e pégaa alí, en «Os meus plans».",
"Using Planika from your home screen? Copy this link and paste it there, in «My plans»."
],
"Enlace copiado": [
"Esteka kopiatuta",
"Enllaç copiat",
"Ligazón copiada",
"Link copied"
],
"Plan compartido: quien tenga el enlace lo ve y lo edita, y los cambios les llegan a todos.": [
"Partekatutako plana: esteka duenak ikusi eta editatu dezake, eta aldaketak guztiei iristen zaizkie.",
"Pla compartit: qui tingui l'enllaç el veu i l'edita, i els canvis arriben a tothom.",
"Plan compartido: quen teña a ligazón veo e edítao, e os cambios chéganlles a todos.",
"Shared plan: anyone with the link can see and edit it, and changes reach everyone."
],
"Es un plan en vivo: guárdalo y verás los cambios que hagan los demás.": [
"Zuzeneko plana da: gorde ezazu eta besteen aldaketak ikusiko dituzu.",
"És un pla en directe: desa-ho i veuràs els canvis que facin els altres.",
"É un plan en directo: gárdao e verás os cambios que fagan os demais.",
"It's a live plan: save it and you'll see the changes others make."
],
"Compartido": [
"Partekatua",
"Compartit",
"Compartido",
"Shared"
],
"«{p}» se ha actualizado": [
"«{p}» eguneratu da",
"«{p}» s'ha actualitzat",
"«{p}» actualizouse",
"«{p}» has been updated"
],
"¿Borrar «{p}» de tu móvil? Quien tenga el enlace lo seguirá teniendo.": [
"«{p}» zure mugikorretik ezabatu? Esteka duenak izaten jarraituko du.",
"Vols esborrar «{p}» del mòbil? Qui tingui l'enllaç el continuarà tenint.",
"Borrar «{p}» do teu móbil? Quen teña a ligazón seguirá téndoo.",
"Delete «{p}» from your phone? Anyone with the link will still have it."
],
"Ese plan compartido ya no existe": [
"Partekatutako plan hori ez da existitzen",
"Aquest pla compartit ja no existeix",
"Ese plan compartido xa non existe",
"That shared plan no longer exists"
],
"No se ha podido cargar el plan compartido. Prueba en un rato.": [
"Ezin izan da partekatutako plana kargatu. Saiatu geroxeago.",
"No s'ha pogut carregar el pla compartit. Prova-ho d'aquí a una estona.",
"Non se puido cargar o plan compartido. Proba nun anaco.",
"The shared plan couldn't be loaded. Try again in a while."
],
"Escape rooms y ocio": [
"Escape room-ak eta aisialdia",
"Escape rooms i oci",
"Escape rooms e lecer",
"Escape rooms and leisure"
],
"Escape rooms y ocio en toda España": [
"Escape room-ak eta aisialdia Espainia osoan",
"Escape rooms i oci a tot Espanya",
"Escape rooms e lecer en toda España",
"Escape rooms and leisure across Spain"
],
"Escape rooms y ocio en {x}": [
"{x}: escape room-ak eta aisialdia",
"Escape rooms i oci a {x}",
"Escape rooms e lecer en {x}",
"Escape rooms and leisure in {x}"
],
"Parques infantiles y de bolas": [
"Haur-parkeak eta bola-parkeak",
"Parcs infantils i de boles",
"Parques infantís e de bólas",
"Indoor play and soft play"
],
"Parques infantiles y de bolas en toda España": [
"Haur-parkeak eta bola-parkeak Espainia osoan",
"Parcs infantils i de boles a tot Espanya",
"Parques infantís e de bólas en toda España",
"Indoor play and soft play across Spain"
],
"Parques infantiles y de bolas en {x}": [
"{x}: haur-parkeak eta bola-parkeak",
"Parcs infantils i de boles a {x}",
"Parques infantís e de bólas en {x}",
"Indoor play and soft play in {x}"
],
"Todo el año": [
"Urte osoan",
"Tot l'any",
"Todo o ano",
"All year round"
],
"Aventura y turismo activo": [
"Abentura eta turismo aktiboa",
"Aventura i turisme actiu",
"Aventura e turismo activo",
"Adventure and outdoor activities"
],
"Aventura y turismo activo en toda España": [
"Abentura eta turismo aktiboa Espainia osoan",
"Aventura i turisme actiu a tot Espanya",
"Aventura e turismo activo en toda España",
"Adventure and outdoor activities across Spain"
],
"Aventura y turismo activo en {x}": [
"{x}: abentura eta turismo aktiboa",
"Aventura i turisme actiu a {x}",
"Aventura e turismo activo en {x}",
"Adventure and outdoor activities in {x}"
],
"Spas y bienestar": [
"Spa-ak eta ongizatea",
"Spas i benestar",
"Spas e benestar",
"Spas and wellness"
],
"Spas y bienestar en toda España": [
"Spa-ak eta ongizatea Espainia osoan",
"Spas i benestar a tot Espanya",
"Spas e benestar en toda España",
"Spas and wellness across Spain"
],
"Spas y bienestar en {x}": [
"{x}: spa-ak eta ongizatea",
"Spas i benestar a {x}",
"Spas e benestar en {x}",
"Spas and wellness in {x}"
],
"Bodegas y experiencias": [
"Upategiak eta esperientziak",
"Cellers i experiències",
"Adegas e experiencias",
"Wineries and experiences"
],
"Bodegas y experiencias en toda España": [
"Upategiak eta esperientziak Espainia osoan",
"Cellers i experiències a tot Espanya",
"Adegas e experiencias en toda España",
"Wineries and experiences across Spain"
],
"Bodegas y experiencias en {x}": [
"{x}: upategiak eta esperientziak",
"Cellers i experiències a {x}",
"Adegas e experiencias en {x}",
"Wineries and experiences in {x}"
],
"Destacado": [
"Nabarmendua",
"Destacat",
"Destacado",
"Featured"
]
};
  /*END*/
  /*HTML*/
  var H = {
"lead": [
"Kontzertuak, antzerkia, erakusketak, kirola, azokak eta jaiak, agenda publikoetatik bilduta. Iragazi probintziaren eta plan motaren arabera, begiratu egutegia eta gorde plana zure agendan.",
"Concerts, teatre, exposicions, esport, fires i festes recollits d'agendes públiques. Filtra per província i tipus de pla, mira el calendari i desa el pla a la teva agenda.",
"Concertos, teatro, exposicións, deporte, feiras e festas recollidos de axendas públicas. Filtra por provincia e tipo de plan, mira o calendario e garda o plan na túa axenda.",
"Concerts, theatre, exhibitions, sport, fairs and festivities gathered from public listings. Filter by province and type of plan, check the calendar and save plans to your calendar."
],
"cal_hint": [
"Zenbaki handia egun horretan <strong>hasten</strong> diren planak dira; txikia, martxan jarraitzen dutenak (erakusketak, zikloak…). Sakatu egun bat edo gehiago (ez dute jarraian egon behar) haien planak ikusteko; sakatu berriro kentzeko.",
"El número gran són els plans que <strong>comencen</strong> aquell dia; el petit, els que continuen en curs (exposicions, cicles…). Prem un o més dies (no cal que siguin seguits) per veure'n els plans; torna a prémer per treure'l.",
"O número grande son os plans que <strong>comezan</strong> ese día; o pequeno, os que seguen en curso (exposicións, ciclos…). Preme un ou varios días (non fai falta que sexan seguidos) para ver os seus plans; volve premer para quitalo.",
"The big number is the plans that <strong>start</strong> that day; the small one, those still running (exhibitions, series…). Tap one or more days (they don't need to be consecutive) to see their plans; tap again to remove it."
],
"install_ios": [
"iPhone edo iPadean, <strong>Safari</strong>-tik:",
"A l'iPhone o l'iPad, des de <strong>Safari</strong>:",
"No iPhone ou iPad, desde <strong>Safari</strong>:",
"On iPhone or iPad, in <strong>Safari</strong>:"
],
"install_ios_steps": [
"<li>Sakatu helbidearen ondoko <strong>⋯</strong> eta gero <strong>Partekatu</strong> <span aria-hidden=\"true\">(aurreko bertsioetan, Partekatu botoia: gora begira dagoen gezia duen laukia)</span>.</li><li>Aukeratu <strong>Gehitu hasierako pantailan</strong>.</li><li>Utzi aktibatuta <strong>Ireki web-aplikazio gisa</strong> eta sakatu <strong>Gehitu</strong>. Planika bere ikonoarekin agertuko da, beste aplikazio bat bezala.</li>",
"<li>Prem <strong>⋯</strong> al costat de l'adreça i després <strong>Comparteix</strong> <span aria-hidden=\"true\">(en versions anteriors, el botó Comparteix: el quadrat amb la fletxa cap amunt)</span>.</li><li>Tria <strong>Afegeix a la pantalla d'inici</strong>.</li><li>Deixa activat <strong>Obre com a app web</strong> i prem <strong>Afegeix</strong>. Planika apareixerà amb la seva icona, com una app més.</li>",
"<li>Preme <strong>⋯</strong> xunto ao enderezo e despois <strong>Compartir</strong> <span aria-hidden=\"true\">(en versións anteriores, o botón Compartir: o cadrado coa frecha cara arriba)</span>.</li><li>Escolle <strong>Engadir á pantalla de inicio</strong>.</li><li>Deixa activado <strong>Abrir como app web</strong> e preme <strong>Engadir</strong>. Planika aparecerá coa súa icona, como unha app máis.</li>",
"<li>Tap <strong>⋯</strong> next to the address, then <strong>Share</strong> <span aria-hidden=\"true\">(in older versions, the Share button: the square with an arrow pointing up)</span>.</li><li>Choose <strong>Add to Home Screen</strong>.</li><li>Leave <strong>Open as Web App</strong> on and tap <strong>Add</strong>. Planika will appear with its icon, like any other app.</li>"
],
"install_ios_app": [
"Instagramen barruan zaude? Ireki lehenik orria Safarin (··· menua → «Ireki nabigatzailean»).",
"Ets dins d'Instagram? Obre abans la pàgina a Safari (menú ··· → «Obre al navegador»).",
"Estás dentro de Instagram? Abre antes a páxina en Safari (menú ··· → «Abrir no navegador»).",
"Inside Instagram? Open the page in Safari first (··· menu → «Open in browser»)."
],
"install_other": [
"Ireki nabigatzailearen menua <strong>⋮</strong>, aukeratu <strong>Gehitu hasierako pantailan</strong> (edo <strong>Instalatu aplikazioa</strong>) eta gero <strong>Instalatu</strong>. Planika bere ikonoarekin agertuko da, beste aplikazio bat bezala.",
"Obre el menú del navegador <strong>⋮</strong>, tria <strong>Afegeix a la pantalla d'inici</strong> (o <strong>Instal·la l'aplicació</strong>) i després <strong>Instal·la</strong>. Planika apareixerà amb la seva icona, com una app més.",
"Abre o menú do navegador <strong>⋮</strong>, escolle <strong>Engadir á pantalla de inicio</strong> (ou <strong>Instalar app</strong>) e despois <strong>Instalar</strong>. Planika aparecerá coa súa icona, como unha app máis.",
"Open the browser menu <strong>⋮</strong>, choose <strong>Add to Home screen</strong> (or <strong>Install app</strong>) and then <strong>Install</strong>. Planika will appear with its icon, like any other app."
]
};
  /*END*/

  function fill(s, v) {
    return v ? String(s).replace(/\{(\w+)\}/g, function (m, n) { return v[n] != null ? v[n] : m; }) : s;
  }
  function t(s, v) {
    var r = s;
    if (L !== 'es') { var k = K[s]; if (k && k[IDX[L]]) r = k[IDX[L]]; }
    return fill(r, v);
  }

  // Claves con un hueco {x} («Todos los planes en {x}») para textos de las páginas ya generadas
  var PATS = null;
  function patterns() {
    if (PATS) return PATS;
    PATS = [];
    Object.keys(K).forEach(function (k) {
      if (!/^[^{}]*\{x\}[^{}]*$/.test(k)) return;
      var rx = new RegExp('^' + k.replace(/[.*+?^$()|[\]\\]/g, '\\$&').replace('\\{x\\}', '{x}').replace('{x}', '(.+?)') + '$');
      PATS.push([rx, k]);
    });
    return PATS;
  }
  function lookup(core) {
    var k = K[core];
    if (k) return k[IDX[L]] || null;
    var ps = patterns();
    for (var i = 0; i < ps.length; i++) {
      var m = ps[i][0].exec(core);
      if (m && K[ps[i][1]][IDX[L]]) return fill(K[ps[i][1]][IDX[L]], { x: m[1] });
    }
    return null;
  }
  var EDGE = /^([^\p{L}\p{N}¿¡«"(]*)([\s\S]*?)([^\p{L}\p{N}.…?!)»"]*)$/u;
  function trText(s) {
    var core = s.trim();
    if (!core) return null;
    var r = lookup(core);
    if (r == null) {  // emoji o símbolos a los lados: «📸 Síguenos en Instagram», «Más info ↗»
      var m = EDGE.exec(core);
      if (m && (m[1] || m[3]) && m[2]) { var r2 = lookup(m[2]); if (r2 != null) r = m[1] + r2 + m[3]; }
    }
    if (r == null) return null;
    return s.match(/^\s*/)[0] + r + s.match(/\s*$/)[0];
  }
  var ROOTS = '[data-i18n], nav.foot, nav.crumbs, .actions, .lang-row';
  var SKIP = 'ul, .list, script, style, [data-noi18n]';
  var ATTRS = ['placeholder', 'aria-label', 'title'];
  function apply(scope) {
    if (L === 'es') return;
    scope = scope || document;
    scope.querySelectorAll('[data-i18n-html]').forEach(function (el) {
      var h = H[el.getAttribute('data-i18n-html')];
      if (h && h[IDX[L]]) el.innerHTML = h[IDX[L]];
    });
    var roots = [].slice.call(scope.querySelectorAll(ROOTS));
    roots.forEach(function (root) {
      var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), n, nodes = [];
      while ((n = w.nextNode())) nodes.push(n);
      nodes.forEach(function (node) {
        var p = node.parentElement;
        if (!p || p.closest(SKIP)) return;
        var r = trText(node.nodeValue);
        if (r != null) node.nodeValue = r;
      });
      [root].concat([].slice.call(root.querySelectorAll('*'))).forEach(function (el) {
        if (el.closest(SKIP)) return;
        ATTRS.forEach(function (a) {
          var v = el.getAttribute(a);
          if (v) { var r = lookup(v.trim()); if (r != null) el.setAttribute(a, r); }
        });
      });
    });
  }

  // Selector: <select class="lang-sel">; en las páginas generadas se añade al pie automáticamente
  function selectors() {
    if (!document.querySelector('.lang-sel')) {
      var navs = document.querySelectorAll('nav.foot');
      var host = navs[navs.length - 1];
      if (host) {
        var p = document.createElement('p'); p.className = 'lang-row';
        p.innerHTML = '<label>🌐 <select class="lang-sel" aria-label="Idioma"></select></label>';
        host.appendChild(p);
      }
    }
    document.querySelectorAll('.lang-sel').forEach(function (sel) {
      sel.innerHTML = LANGS.map(function (x) { return '<option value="' + x[0] + '"' + (x[0] === L ? ' selected' : '') + '>' + x[1] + '</option>'; }).join('');
      sel.setAttribute('aria-label', t('Idioma'));
      sel.addEventListener('change', function () {
        try { localStorage.setItem('planika_lang', this.value); } catch (e) { /* */ }
        try { if (window.gtag) window.gtag('event', 'lang_change', { lang: this.value }); } catch (e) { /* */ }
        var u = new URL(location.href); u.searchParams.delete('lang');
        location.replace(u.href);
      });
    });
  }

  // Fechas y números. Algunos navegadores (Chrome en Android, entre otros) no traen los datos de euskera ni de
  // gallego y escribirían «Sat, Dec 5»: en ese caso se usan los nombres de aquí.
  var NAMES = {
    eu: { wd: ['ig.', 'al.', 'ar.', 'az.', 'og.', 'or.', 'lr.'], wdl: ['igandea', 'astelehena', 'asteartea', 'asteazkena', 'osteguna', 'ostirala', 'larunbata'],
      mo: ['urt.', 'ots.', 'mar.', 'api.', 'mai.', 'eka.', 'uzt.', 'abu.', 'ira.', 'urr.', 'aza.', 'abe.'],
      mol: ['urtarrila', 'otsaila', 'martxoa', 'apirila', 'maiatza', 'ekaina', 'uztaila', 'abuztua', 'iraila', 'urria', 'azaroa', 'abendua'] },
    gl: { wd: ['dom.', 'luns', 'mar.', 'mér.', 'xov.', 'ven.', 'sáb.'], wdl: ['domingo', 'luns', 'martes', 'mércores', 'xoves', 'venres', 'sábado'],
      mo: ['xan.', 'feb.', 'mar.', 'abr.', 'maio', 'xuño', 'xul.', 'ago.', 'set.', 'out.', 'nov.', 'dec.'],
      mol: ['xaneiro', 'febreiro', 'marzo', 'abril', 'maio', 'xuño', 'xullo', 'agosto', 'setembro', 'outubro', 'novembro', 'decembro'] }
  };
  function native(loc) {
    try { return Intl.DateTimeFormat.supportedLocalesOf([loc]).length > 0; } catch (e) { return false; }
  }
  var NATIVE = native(LOCALES[L]);
  function own(o) {
    var n = NAMES[L];
    return { format: function (d) {
      var day = d.getDate(), m = d.getMonth(), y = d.getFullYear(), w = d.getDay();
      if (L === 'eu') {  // «lr., abe. 5», «abenduaren 5a, larunbata», «abendua 2026»
        if (o.weekday === 'long') return n.mol[m] + 'ren ' + day + 'a, ' + n.wdl[w];
        if (!o.day) return n.mol[m] + (o.year ? ' ' + y : '');
        return (o.weekday ? n.wd[w] + ', ' : '') + n.mo[m] + ' ' + day;
      }
      if (o.weekday === 'long') return n.wdl[w] + ', ' + day + ' de ' + n.mol[m] + (o.year ? ' de ' + y : '');
      if (!o.day) return n.mol[m] + (o.year ? ' de ' + y : '');
      return (o.weekday ? n.wd[w] + ', ' : '') + day + ' ' + n.mo[m];
    } };
  }
  function dtf(o) { return NATIVE || !NAMES[L] ? new Intl.DateTimeFormat(LOCALES[L], o) : own(o); }
  function num(n) { return Number(n).toLocaleString(NATIVE ? LOCALES[L] : 'es-ES'); }

  window.PLANIKA_I18N = { lang: L, locale: LOCALES[L], t: t, apply: apply, langs: LANGS, dtf: dtf, num: num };
  if (L !== 'es') document.documentElement.lang = L;
  function start() { selectors(); apply(document); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
