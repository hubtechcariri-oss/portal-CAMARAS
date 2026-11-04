/* Menu com submenus e carrossel de banners, acessíveis por teclado e leitor de tela. */
(function () {
  "use strict";

  /* ---------- Menu ---------- */
  var grupos = Array.prototype.slice.call(document.querySelectorAll(".menu__grupo > button"));

  function fecharTodos(exceto) {
    grupos.forEach(function (b) {
      if (b !== exceto) b.setAttribute("aria-expanded", "false");
    });
  }

  grupos.forEach(function (botao) {
    botao.addEventListener("click", function () {
      var aberto = botao.getAttribute("aria-expanded") === "true";
      fecharTodos(botao);
      botao.setAttribute("aria-expanded", aberto ? "false" : "true");
    });
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Escape") return;
    var aberto = grupos.filter(function (b) { return b.getAttribute("aria-expanded") === "true"; })[0];
    if (aberto) { fecharTodos(); aberto.focus(); }
  });

  document.addEventListener("click", function (ev) {
    if (!ev.target.closest || !ev.target.closest(".menu__grupo")) fecharTodos();
  });

  // Fecha o submenu quando o foco sai dele (navegação por Tab).
  Array.prototype.forEach.call(document.querySelectorAll(".menu__grupo"), function (li) {
    li.addEventListener("focusout", function (ev) {
      if (ev.relatedTarget && !li.contains(ev.relatedTarget)) {
        li.querySelector("button").setAttribute("aria-expanded", "false");
      }
    });
  });

  var botaoMobile = document.querySelector(".menu-mobile");
  if (botaoMobile) {
    botaoMobile.addEventListener("click", function () {
      var aberto = botaoMobile.getAttribute("aria-expanded") === "true";
      botaoMobile.setAttribute("aria-expanded", aberto ? "false" : "true");
      botaoMobile.closest(".cabecalho").classList.toggle("menu-aberto", !aberto);
    });
  }

  /* ---------- Carrossel ---------- */
  var carrossel = document.querySelector("[data-carrossel]");
  if (!carrossel) return;
  var slides = Array.prototype.slice.call(carrossel.querySelectorAll(".carrossel__slide"));
  var pontos = Array.prototype.slice.call(carrossel.querySelectorAll(".carrossel__ponto"));
  var botaoPausa = carrossel.querySelector("[data-pausa]");
  if (slides.length < 2) return;

  var atual = 0;
  var timer = null;
  var pausadoPeloUsuario = false;
  var reduzir = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function mostrar(i) {
    atual = (i + slides.length) % slides.length;
    slides.forEach(function (s, n) {
      var ativo = n === atual;
      s.hidden = !ativo;
      s.setAttribute("aria-hidden", ativo ? "false" : "true");
    });
    pontos.forEach(function (p, n) {
      p.setAttribute("aria-current", n === atual ? "true" : "false");
    });
  }

  function iniciar() {
    if (timer || pausadoPeloUsuario || reduzir) return;
    timer = setInterval(function () { mostrar(atual + 1); }, 7000);
  }
  function parar() { clearInterval(timer); timer = null; }

  function atualizarPausa() {
    if (!botaoPausa) return;
    botaoPausa.setAttribute("aria-pressed", pausadoPeloUsuario ? "true" : "false");
    botaoPausa.textContent = pausadoPeloUsuario ? "▶ Reproduzir" : "❚❚ Pausar";
  }

  carrossel.querySelector("[data-anterior]").addEventListener("click", function () { mostrar(atual - 1); });
  carrossel.querySelector("[data-proximo]").addEventListener("click", function () { mostrar(atual + 1); });
  pontos.forEach(function (p, n) { p.addEventListener("click", function () { mostrar(n); }); });
  if (botaoPausa) {
    if (reduzir) pausadoPeloUsuario = true;
    botaoPausa.addEventListener("click", function () {
      pausadoPeloUsuario = !pausadoPeloUsuario;
      atualizarPausa();
      if (pausadoPeloUsuario) parar(); else iniciar();
    });
    atualizarPausa();
  }

  // WCAG 2.2.2: a rotação para enquanto a pessoa interage com o carrossel.
  carrossel.addEventListener("mouseenter", parar);
  carrossel.addEventListener("mouseleave", iniciar);
  carrossel.addEventListener("focusin", parar);
  carrossel.addEventListener("focusout", function (ev) {
    if (!ev.relatedTarget || !carrossel.contains(ev.relatedTarget)) iniciar();
  });

  mostrar(0);
  iniciar();
})();

// Transparência: filtra os itens do catálogo enquanto a pessoa digita.
(function () {
  "use strict";
  var campo = document.querySelector("[data-filtro-transparencia]");
  if (!campo) return;
  var grupos = document.querySelectorAll("[data-grupo]");
  var ocultaveis = document.querySelectorAll("[data-some-na-busca]");
  var aviso = document.querySelector("[data-sem-resultado]");

  function normalizar(texto) {
    return texto.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  campo.addEventListener("input", function () {
    var termo = normalizar(campo.value.trim());
    var achados = 0;
    grupos.forEach(function (grupo) {
      var visiveis = 0;
      grupo.querySelectorAll("[data-item]").forEach(function (item) {
        var mostra = !termo || normalizar(item.getAttribute("data-item")).indexOf(termo) !== -1;
        item.hidden = !mostra;
        if (mostra) visiveis++;
      });
      grupo.hidden = visiveis === 0;
      achados += visiveis;
    });
    ocultaveis.forEach(function (el) { el.hidden = !!termo; });
    aviso.hidden = !termo;
    aviso.textContent = !termo ? "" : achados
      ? achados + (achados === 1 ? " item encontrado." : " itens encontrados.")
      : "Nenhum item encontrado. Tente outra palavra ou faça um pedido no e-SIC.";
  });
})();
