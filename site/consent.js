/* Consentimiento de analítica de Planika.
   Google Analytics 4 solo se carga tras aceptar de forma expresa. Rechazar es igual de fácil que aceptar
   (mismo botón, mismo estilo) y la decisión se puede cambiar en cualquier momento desde el enlace
   «Configurar cookies» del pie de cada página (cualquier elemento con data-privacy-settings). */
(function () {
  "use strict";
  var KEY = "planika_analytics_consent", ID = "G-E4DXWFYPH1";
  var css = "#planika-consent{position:fixed;z-index:10000;left:16px;right:16px;bottom:16px;max-width:760px;margin:auto;padding:18px;background:#fff;color:#1a1033;border:3px solid #1a1033;border-radius:16px;box-shadow:6px 6px 0 #1a1033;font:15px/1.5 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}" +
    "#planika-consent p{margin:0 0 12px}#planika-consent .pc-actions{display:flex;flex-wrap:wrap;gap:10px}" +
    "#planika-consent button{min-height:44px;padding:8px 18px;border:2px solid #1a1033;border-radius:999px;background:#fff;color:#1a1033;font:700 15px system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;cursor:pointer;box-shadow:2px 2px 0 #1a1033}" +
    "#planika-consent button:focus-visible{outline:3px solid #ff3d81;outline-offset:3px}#planika-consent a{color:#1a1033;font-weight:700}" +
    "@media(max-width:520px){#planika-consent{left:8px;right:8px;bottom:8px;padding:14px;font-size:14px}#planika-consent .pc-actions{display:grid;grid-template-columns:1fr 1fr}#planika-consent button{width:100%}}";

  function style() {
    if (document.getElementById("planika-consent-style")) return;
    var s = document.createElement("style");
    s.id = "planika-consent-style";
    s.textContent = css;
    document.head.appendChild(s);
  }
  function choice() { try { return localStorage.getItem(KEY); } catch (_) { return null; } }
  function save(v) { try { localStorage.setItem(KEY, v); } catch (_) {} }

  function loadGA() {
    if (window.__planikaGA4Loaded) return;
    window.__planikaGA4Loaded = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("consent", "default", { analytics_storage: "denied", ad_storage: "denied", ad_user_data: "denied", ad_personalization: "denied" });
    window.gtag("consent", "update", { analytics_storage: "granted" });
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + ID;
    document.head.appendChild(s);
    window.gtag("js", new Date());
    window.gtag("config", ID);
  }

  function clearCookies() {
    var names = document.cookie ? document.cookie.split(";").map(function (x) { return x.trim().split("=")[0]; }) : [];
    var parts = location.hostname.split(".");
    var domains = ["", location.hostname, parts.length > 1 ? "." + parts.slice(-2).join(".") : ""];
    names.forEach(function (n) {
      if (n === "_ga" || n.indexOf("_ga_") === 0 || n === "_gid" || n === "_gat") {
        domains.forEach(function (d) {
          document.cookie = n + "=; Max-Age=0; path=/" + (d ? "; domain=" + d : "") + "; SameSite=Lax";
        });
      }
    });
  }

  function closePanel() { var p = document.getElementById("planika-consent"); if (p) p.remove(); }

  function select(v) {
    var before = choice();
    save(v);
    closePanel();
    if (v === "accepted") loadGA();
    else {
      clearCookies();
      // GA ya cargado en esta página: se recarga para que deje de medir ahora mismo
      if (before === "accepted" && window.__planikaGA4Loaded) location.reload();
    }
  }

  function panel() {
    closePanel();
    style();
    var p = document.createElement("section");
    p.id = "planika-consent";
    p.setAttribute("role", "dialog");
    p.setAttribute("aria-labelledby", "planika-consent-title");
    p.innerHTML = '<p id="planika-consent-title"><strong>Privacidad y analítica</strong></p>' +
      '<p>Con tu permiso, Planika usa Google Analytics para contar visitas y saber qué planes interesan. ' +
      'Si rechazas, no se carga y la web funciona igual. Puedes cambiarlo cuando quieras en «Configurar cookies», al pie de la página. ' +
      '<a href="/privacidad.html#cookies">Más información</a>.</p>' +
      '<div class="pc-actions"><button type="button" data-choice="accepted">Aceptar</button>' +
      '<button type="button" data-choice="rejected">Rechazar</button></div>';
    p.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-choice]");
      if (b) select(b.getAttribute("data-choice"));
    });
    document.body.appendChild(p);
  }

  function init() {
    document.addEventListener("click", function (e) {
      var t = e.target.closest && e.target.closest("[data-privacy-settings]");
      if (t) { e.preventDefault(); panel(); }
    });
    var v = choice();
    if (v === "accepted") loadGA();
    else if (v !== "rejected") panel();
  }

  window.planikaPrivacySettings = panel;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
