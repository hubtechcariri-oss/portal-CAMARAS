/* Painel: contador de caracteres e prévia do endereço (slug). Sem dependências. */
(function () {
  "use strict";
  function iniciar() {

  // Contador: <textarea data-contador="300"> ganha "N de 300 caracteres" logo abaixo.
  Array.prototype.forEach.call(document.querySelectorAll("[data-contador]"), function (campo) {
    var limite = parseInt(campo.getAttribute("data-contador"), 10);
    campo.setAttribute("maxlength", limite);
    var aviso = document.createElement("div");
    aviso.className = "contador";
    aviso.id = campo.id + "_contador";
    aviso.setAttribute("aria-live", "polite");
    var ajuda = campo.closest(".form-row") && campo.closest(".form-row").querySelector(".help");
    if (ajuda) ajuda.insertBefore(aviso, ajuda.firstChild);
    else campo.insertAdjacentElement("afterend", aviso);
    var descritos = (campo.getAttribute("aria-describedby") || "").trim();
    campo.setAttribute("aria-describedby", (descritos + " " + aviso.id).trim());
    function atualizar() {
      var n = campo.value.length;
      aviso.textContent = n + " de " + limite + " caracteres";
      aviso.classList.toggle("contador--perto", n >= limite * 0.9);
    }
    campo.addEventListener("input", atualizar);
    atualizar();
  });

  // Prévia do endereço: acompanha o slug (inclusive quando ele é preenchido a partir do título).
  var previa = document.querySelector("[data-previa-slug]");
  var slug = document.getElementById("id_slug");
  if (previa && slug) {
    var atualizarSlug = function () { previa.textContent = slug.value || "endereco-da-noticia"; };
    slug.addEventListener("input", atualizarSlug);
    slug.addEventListener("change", atualizarSlug);
    var titulo = document.getElementById("id_titulo");
    if (titulo) ["input", "keyup", "change"].forEach(function (ev) { titulo.addEventListener(ev, function () { setTimeout(atualizarSlug, 0); }); });
    atualizarSlug();
  }

  /* Menu lateral: aberto em telas largas, recolhido no celular (abre pelo botão "Menu"). */
  var menu = document.querySelector("[data-menu-painel]");
  if (menu && window.matchMedia) {
    var estreita = window.matchMedia("(max-width: 1023px)");
    var ajustarMenu = function () { if (estreita.matches) menu.removeAttribute("open"); else menu.setAttribute("open", ""); };
    ajustarMenu();
    if (estreita.addEventListener) estreita.addEventListener("change", ajustarMenu);
  }

  /* Menu do usuário: fecha com Esc (devolvendo o foco) e ao clicar fora. */
  var conta = document.querySelector("[data-menu-usuario]");
  if (conta) {
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && conta.open) { conta.open = false; conta.querySelector("summary").focus(); }
    });
    document.addEventListener("click", function (ev) { if (conta.open && !conta.contains(ev.target)) conta.open = false; });
  }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
