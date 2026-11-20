/* Consentimiento de analítica de Planika. GA4 solo se carga tras aceptación explícita. */
(function () {
  "use strict";
  var KEY = "planika_analytics_consent", ID = "G-E4DXWFYPH1";
  var css = "#planika-consent{position:fixed;z-index:10000;left:16px;right:16px;bottom:16px;max-width:760px;margin:auto;padding:18px;background:#fff;color:#1a1033;border:3px solid #1a1033;border-radius:16px;box-shadow:6px 6px 0 #1a1033;font:15px/1.5 system-ui}#planika-consent p{margin:0 0 12px}#planika-consent .pc-actions{display:flex;flex-wrap:wrap;gap:10px}#planika-consent button,#planika-privacy-settings{min-height:42px;padding:8px 14px;border:2px solid #1a1033;border-radius:999px;background:#fff;color:#1a1033;font:700 14px system-ui;cursor:pointer;box-shadow:2px 2px 0 #1a1033}#planika-consent button:focus-visible,#planika-privacy-settings:focus-visible{outline:3px solid #ff3d81;outline-offset:3px}#planika-consent button.primary{background:#1a1033;color:#fff}#planika-consent a{color:#1a1033;font-weight:700}#planika-privacy-settings{position:fixed;z-index:9999;right:12px;bottom:12px;font-size:12px;min-height:34px;padding:5px 10px;background:#fff}@media(max-width:520px){#planika-consent{left:8px;right:8px;bottom:8px;padding:14px}#planika-consent .pc-actions{display:grid;grid-template-columns:1fr 1fr}#planika-consent button{width:100%}}";
  function style() { if (!document.getElementById("planika-consent-style")) { var s=document.createElement("style");s.id="planika-consent-style";s.textContent=css;document.head.appendChild(s); } }
  function choice() { try { return localStorage.getItem(KEY); } catch (_) { return null; } }
  function save(v) { try { localStorage.setItem(KEY,v); } catch (_) {} }
  function loadGA() {
    if (window.__planikaGA4Loaded) return;
    window.__planikaGA4Loaded=true;window.dataLayer=window.dataLayer||[];
    window.gtag=function(){window.dataLayer.push(arguments);};
    window.gtag("consent","default",{analytics_storage:"denied",ad_storage:"denied",ad_user_data:"denied",ad_personalization:"denied"});
    window.gtag("consent","update",{analytics_storage:"granted"});
    var s=document.createElement("script");s.async=true;s.src="https://www.googletagmanager.com/gtag/js?id="+ID;document.head.appendChild(s);
    window.gtag("js",new Date());window.gtag("config",ID);
  }
  function clearCookies() {
    var names=document.cookie?document.cookie.split(";").map(function(x){return x.trim().split("=")[0];}):[];
    names.forEach(function(n){if(n==="_ga"||n.indexOf("_ga_")===0||n==="_gid"||n==="_gat"){
      document.cookie=n+"=; Max-Age=0; path=/; SameSite=Lax";
      document.cookie=n+"=; Max-Age=0; path=/; domain="+location.hostname+"; SameSite=Lax";
      var b=location.hostname.split(".");if(b.length>1)document.cookie=n+"=; Max-Age=0; path=/; domain=."+b.slice(-2).join(".")+"; SameSite=Lax";
    }});
  }
  function closePanel(){var p=document.getElementById("planika-consent");if(p)p.remove();}
  function select(v){save(v);closePanel();if(v==="accepted")loadGA();else clearCookies();}
  function panel(){
    closePanel();style();var p=document.createElement("section");p.id="planika-consent";p.setAttribute("role","dialog");p.setAttribute("aria-labelledby","planika-consent-title");
    p.innerHTML='<p id="planika-consent-title"><strong>Privacidad y analítica</strong></p><p>Planika utiliza Google Analytics 4 para medir el uso de la web y mejorarla. Solo se activará si aceptas las cookies de analítica. Puedes rechazar o cambiar tu decisión cuando quieras. <a href="/privacidad.html">Más información</a>.</p><div class="pc-actions"><button type="button" class="primary" data-choice="accepted">Aceptar analítica</button><button type="button" data-choice="rejected">Rechazar</button></div>';
    p.addEventListener("click",function(e){var b=e.target.closest("button[data-choice]");if(b)select(b.getAttribute("data-choice"));});document.body.appendChild(p);
  }
  function init(){
    style();var b=document.createElement("button");b.id="planika-privacy-settings";b.type="button";b.textContent="Privacidad";b.setAttribute("aria-label","Cambiar preferencias de privacidad");b.addEventListener("click",panel);document.body.appendChild(b);
    var v=choice();if(v==="accepted")loadGA();else if(v!=="rejected")panel();
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init);else init();
})();