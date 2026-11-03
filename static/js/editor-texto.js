/* Editor de texto (Trix): recusa anexos — imagens coladas ou arrastadas não entram no texto. */
document.addEventListener("trix-file-accept", function (ev) { ev.preventDefault(); });
