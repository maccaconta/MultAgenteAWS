(function(){
  function ensureAura(card, running){
    const agent = card.querySelector('.timeline-agent');
    if(!agent) return;
    let aura = agent.querySelector('.timeline-agent-aura');
    if(running && !aura){
      aura = document.createElement('span');
      aura.className = 'timeline-agent-aura';
      aura.setAttribute('aria-hidden', 'true');
      agent.appendChild(aura);
    }
    if(!running && aura){
      aura.remove();
    }
  }

  function syncRunningState(root){
    const cards = root.querySelectorAll('[data-agent-card]');
    cards.forEach((card)=>{
      const status = (card.getAttribute('data-status') || '').toLowerCase().trim();
      const running = status === 'running' || status === 'processando' || status === 'em processamento';
      card.classList.toggle('is-running', running);
      ensureAura(card, running);
    });
  }

  function boot(){
    const panel = document.querySelector('[data-agents-panel]');
    if(!panel) return;
    syncRunningState(panel);

    const observer = new MutationObserver(()=>syncRunningState(panel));
    observer.observe(panel,{
      childList:true,
      subtree:true,
      attributes:true,
      attributeFilter:['data-status','class']
    });

    window.addEventListener('load', ()=>syncRunningState(panel));
    setInterval(()=>syncRunningState(panel), 700);
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();