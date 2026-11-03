(function () {
  var raiz = document.documentElement;
  var escala = 100;

  function ler(chave) { try { return localStorage.getItem(chave); } catch (e) { return null; } }
  function gravar(chave, valor) { try { localStorage.setItem(chave, valor); } catch (e) {} }

  function aplicar() {
    raiz.style.fontSize = escala + "%";
    var contraste = raiz.classList.contains("alto-contraste");
    var botao = document.querySelector('[data-acao="contraste"]');
    if (botao) botao.setAttribute("aria-pressed", contraste ? "true" : "false");
  }

  escala = parseInt(ler("fonte") || "100", 10) || 100;
  if (ler("contraste") === "1") raiz.classList.add("alto-contraste");
  aplicar();

  document.addEventListener("click", function (ev) {
    var acao = ev.target.getAttribute && ev.target.getAttribute("data-acao");
    if (!acao) return;
    if (acao === "contraste") {
      raiz.classList.toggle("alto-contraste");
      gravar("contraste", raiz.classList.contains("alto-contraste") ? "1" : "0");
    } else if (acao === "aumentar") {
      escala = Math.min(escala + 10, 160);
    } else if (acao === "diminuir") {
      escala = Math.max(escala - 10, 80);
    }
    gravar("fonte", String(escala));
    aplicar();
  });

  if (window.VLibras) { new window.VLibras.Widget("https://vlibras.gov.br/app"); }
  else {
    window.addEventListener("load", function () {
      if (window.VLibras) new window.VLibras.Widget("https://vlibras.gov.br/app");
    });
  }
})();
