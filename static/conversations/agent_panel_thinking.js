(function () {
  function updateThinkingState(root) {
    const cards = root.querySelectorAll("[data-agent-card]");
    cards.forEach((card) => {
      const status = (card.getAttribute("data-status") || "").toLowerCase();
      card.classList.toggle("is-running", status === "running" || status === "processando" || status === "em processamento");
    });
  }

  function boot() {
    const panel = document.querySelector("[data-agents-panel]");
    if (!panel) return;
    updateThinkingState(panel);

    const observer = new MutationObserver(() => updateThinkingState(panel));
    observer.observe(panel, { childList: true, subtree: true, attributes: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();