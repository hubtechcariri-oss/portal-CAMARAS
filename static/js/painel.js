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
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
