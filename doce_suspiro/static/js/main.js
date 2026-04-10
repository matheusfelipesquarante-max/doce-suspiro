// ==============================
// LAMBARY - GLOBAL JS
// ==============================

// Confirmações padrão
function confirmarExclusao(mensagem = "Deseja realmente excluir?") {
    return confirm(mensagem);
}

// Converter automaticamente campos para MAIÚSCULO
document.addEventListener("DOMContentLoaded", function () {
    const inputs = document.querySelectorAll(".uppercase-input");

    inputs.forEach(input => {
        input.addEventListener("input", function () {
            this.value = this.value.toUpperCase();
        });
    });
});
