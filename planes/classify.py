# -*- coding: utf-8 -*-
"""Clasificación de eventos en tipos de plan."""
import re

from .util import norm

CATEGORIES = [
    ("musica", "Música y conciertos", "🎵"),
    ("escena", "Teatro y danza", "🎭"),
    ("expos", "Exposiciones y museos", "🖼️"),
    ("cine", "Cine", "🎬"),
    ("deporte", "Deporte", "⚽"),
    ("gastro", "Gastronomía, ferias y mercados", "🍷"),
    ("infantil", "Infantil y familiar", "🧒"),
    ("navidad", "Navidad", "🎄"),
    ("fiestas", "Fiestas y tradiciones", "🎉"),
    ("naturaleza", "Naturaleza, rutas y visitas", "🥾"),
    ("charlas", "Charlas, libros y talleres", "📚"),
    ("otros", "Otros planes", "✨"),
]
CATEGORY_KEYS = [c[0] for c in CATEGORIES]

# Reglas por palabras clave sobre el tipo declarado por la fuente y el título.
# El orden importa: la primera regla que casa gana.
_RULES = [
    ("infantil", r"\b(infantil|familiar|famil|ninos|nens|haur|txiki|umeentzat|cuentacuentos|titeres|marionet|bebes|nadons|kids|children|peques)\b"),
    ("navidad", r"\b(navidad|navidenas?|navidenos?|nadal|nadalenc|nadalencs|gabon|gabonetako|belen|belenes|naixement|pesebre|villancicos?|nadales|reyes magos|cabalgata de reyes|cavalcada de reis|reis magos|papa noel|olentzero|mari domingi|fin de ano|nochevieja|nit de cap d.any|campanadas|christmas|xmas|turron)"),
    ("cine", r"\b(cine|cinema|pelicula|film|audiovisual|documental|cortometraje|zinema|proyeccion|projeccio)"),
    ("deporte", r"\b(deport|esport|kirol|futbol|baloncesto|basket|maraton|carrera popular|ciclis|triatlon|running|padel|tenis|natacion|rugby|balonmano|voleibol|motogp|formula|trail|regata|hipica|golf|boxeo|mma|surf|esqui|pelota|trainera)"),
    ("escena", r"\b(teatro|teatre|antzerki|danza|dansa|dantza|ballet|opera|zarzuela|musical|circo|circ|magia|monolog|comedia|humor|performance|clown|improvisacion|bertso|titella|escenic|escenica|arts esceniques|espectacle|espectaculo|flamenco)"),
    ("musica", r"\b(concierto|concert|kontzertu|musica|music|musika|jazz|rock|pop|folk|coral|coro|orquesta|orquestra|sinfonic|filarmon|recital|dj|festival de musica|banda|blues|soul|funk|hip hop|rap|reggae|electronic|indie|metal|cantautor|gospel|tributo)"),
    ("expos", r"\b(exposicion|exposicio|erakusketa|museo|museu|museum|galeria|fotografia|pintura|escultura|arte|arts visuals|arte urbano|instalacion|muestra)"),
    ("gastro", r"\b(gastronom|feria|fira|azoka|mercado|mercat|mercadillo|degustacion|catas?\b|vino|vins\b|tast|celler|enoturis|cerveza|tapas|pintxo|food|cocina|cuina|sukaldaritza|congreso|salon)"),
    ("fiestas", r"\b(fiesta|festa|jai|jaiak|fiestas|festes|romeria|carnaval|carnestoltes|navidad|nadal|gabon|reyes|cabalgata|cavalcada|procesion|processo|semana santa|verbena|patron|tradicional|popular|falla|hoguera|feria de abril|pasacalle|cercavila|castells?\b|casteller|gigantes|gegants|correfoc|sant joan|san juan|halloween|mercado medieval|commemor|festival|festivales)"),
    ("naturaleza", r"\b(ruta|rutes|senderis|excursion|itinerari|visita guiada|visita|visites|paseo|passeig|naturaleza|natura|parque|parc|jardin|jardi|montana|muntanya|mendi|playa|platja|observacion|astronom|ornitolog|bici|kayak)"),
    ("charlas", r"\b(conferencia|hitzaldi|charla|xerrada|coloquio|mesa redonda|debate|taller|tailer|curso|cursos|formacion|presentacion|libro|llibre|liburu|lectura|literatura|poesia|club de lectura|jornada|seminario|encuentro|trobada|divulga|ciencia|historia|idioma|digital|biblioteca)"),
]
_COMPILED = [(k, re.compile(rx)) for k, rx in _RULES]

# Mapeo directo de tipos declarados por cada fuente -> categoría
_SOURCE_TYPES = {
    # Madrid (@type)
    "musica": "musica", "jazzsoulfunkyswingreagge": "musica", "flamenco": "musica", "clasicaespanola": "musica",
    "zarzuela": "escena", "latinaespanola": "musica", "corogospel": "musica", "festivales": "musica",
    "teatroperformance": "escena", "danzabaile": "escena", "circomagia": "escena", "comediamonologo": "escena",
    "cineactividadesaudiovisuales": "cine", "cineficcion": "cine",
    "cuentacuentostiteresmarionetas": "infantil", "actividadesescolares": "infantil", "campamentos": "infantil",
    "exposiciones": "expos", "arte": "expos", "actividadescallearteurbano": "expos",
    "conferenciascoloquios": "charlas", "cursostalleres": "charlas", "recitalespresentacionesactosliterarios": "charlas",
    "clubeslectura": "charlas", "historia": "charlas", "literatura": "charlas", "capacitaciondigital": "charlas",
    "idiomas": "charlas", "concursoscertamenes": "otros", "culturalibre": "charlas",
    "excursionesitinerariosvisitas": "naturaleza", "itinerariosotrasactividadesambientales": "naturaleza",
    "fiestasnavidadesreyes": "fiestas", "comemoracioneshomenajes": "fiestas", "ferias": "gastro",
    "actividadesdeportivas": "deporte",
    # Euskadi (typeEs)
    "concierto": "musica", "teatro": "escena", "danza": "escena", "bertsolarismo": "escena",
    "cine y audiovisuales": "cine", "conferencia": "charlas", "exposicion": "expos", "feria": "gastro",
    "fiesta": "fiestas", "taller": "charlas", "infantil": "infantil", "deporte": "deporte",
    "otros": "otros", "formacion": "charlas", "visita guiada": "naturaleza", "festival": "musica",
    "literatura": "charlas", "presentacion": "charlas", "actividad infantil": "infantil",
    # Cataluña (categories)
    "teatre": "escena", "exposicions": "expos", "concerts": "musica", "festivals i mostres": "musica",
    "commemoracions": "fiestas", "conferencies": "charlas", "rutes i visites": "naturaleza", "dansa": "escena",
    "nadal": "fiestas", "fires i mercats": "gastro", "cicles": "musica", "cinema": "cine", "tallers": "charlas",
    "presentacions": "charlas", "jornades": "charlas", "cursos": "charlas", "festes": "fiestas",
    "activitats infantils": "infantil", "circ": "escena", "opera": "escena", "lectures": "charlas",
    # Castilla y León (categoria / tematica)
    "conciertos": "musica", "conferencias y cursos": "charlas", "espectaculos": "escena", "libros y lectura": "charlas",
    # IVC (tipo_evento)
    "pelicula": "cine", "artes escenicas": "escena", "musica y cultura popular valenciana": "musica",
    "audiovisuales y cinematografia": "cine",
    # Málaga (CATEGORIA)
    "cursos y talleres": "charlas", "congresos conferencias y festivales": "charlas", "fiestas populares": "fiestas",
    "ferias exposiciones y museos": "expos", "deportes": "deporte", "actos religiosos": "fiestas",
    "otros eventos": "otros", "premios y concursos": "otros", "cine": "cine",
    # Ticketmaster (segment / genre)
    "music": "musica", "sports": "deporte", "arts & theatre": "escena", "arts theatre": "escena", "film": "cine",
    "miscellaneous": "otros", "family": "infantil", "comedy": "escena", "theatre": "escena", "dance": "escena",
    "classical": "musica", "fairs & festivals": "gastro", "fairs festivals": "gastro", "museum": "expos",
    "fine art": "expos", "lecture/seminar": "charlas", "food & drink": "gastro", "food drink": "gastro",
}


def classify(raw_types, title="", description="", audience=""):
    """Devuelve la clave de categoría más probable."""
    types = raw_types if isinstance(raw_types, (list, tuple)) else [raw_types]
    aud = norm(audience)
    if re.search(r"\b(ninos|infantil|familias|familiar|publico infantil|haurrak|infants)\b", aud):
        return "infantil"
    for t in types:
        key = norm(t).replace("agenda categories/", "").replace("agenda ambits/", "").strip()
        if key in _SOURCE_TYPES:
            return _SOURCE_TYPES[key]
    text = norm(" ".join([str(t) for t in types if t] + [str(title or "")]))
    for key, rx in _COMPILED:
        if rx.search(text):
            return key
    text2 = norm(description or "")[:300]
    for key, rx in _COMPILED:
        if rx.search(text2):
            return key
    return "otros"
