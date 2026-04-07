const fs = require('fs');
const file = 'aegis-x5-deploy/index.html';
let c = fs.readFileSync(file, 'utf8');

// 1. Inject video section BEFORE <!-- DEMO EXPLANATION -->
const demoMarker = '<!-- DEMO EXPLANATION -->';
const videoSection = `<!-- VIDEO -->
<section class="sec" id="video" style="text-align:center">
<div class="label en">Watch AEGIS-X5 in Action</div>
<div class="label fr">AEGIS-X5 en Action</div>
<div class="title en" style="display:inline-block">Gouvernance Autonome — Demo</div>
<div class="title fr" style="display:inline-block">Gouvernance Autonome — Démo</div>
<p style="color:var(--tx2);font-size:.85rem;margin:.75rem auto 1.5rem;max-width:560px" class="en">See how AEGIS-X5 governs 500+ agents in real time — hallucination blocking, drift prediction, autonomous correction.</p>
<p style="color:var(--tx2);font-size:.85rem;margin:.75rem auto 1.5rem;max-width:560px" class="fr">Voyez comment AEGIS-X5 gouverne 500+ agents en temps réel — blocage d'hallucinations, prédiction de drift, correction autonome.</p>
<div style="max-width:860px;margin:0 auto;border-radius:12px;overflow:hidden;border:1px solid var(--bdr);background:#000;box-shadow:0 24px 64px rgba(0,0,0,.5)">
  <video controls preload="metadata" style="width:100%;display:block;max-height:500px" poster="">
    <source src="gouvernance-autonome.mp4" type="video/mp4">
    <p style="padding:2rem;color:var(--tx2)">Your browser does not support HTML5 video. <a href="gouvernance-autonome.mp4" style="color:var(--gold)">Download the video</a>.</p>
  </video>
</div>
<p style="color:var(--tx3);font-size:.72rem;margin-top:1rem;font-family:'JetBrains Mono',monospace" class="en">🎬 AEGIS-X5 · Gouvernance Autonome · AgenticX5 Research</p>
<p style="color:var(--tx3);font-size:.72rem;margin-top:1rem;font-family:'JetBrains Mono',monospace" class="fr">🎬 AEGIS-X5 · Gouvernance Autonome · AgenticX5 Research</p>
</section>

`;

if (!c.includes(demoMarker)) {
  console.log('ERROR: <!-- DEMO EXPLANATION --> not found');
  process.exit(1);
}
c = c.replace(demoMarker, videoSection + demoMarker);
console.log('✅ Video section injected before DEMO EXPLANATION');

// 2. Inject deck cards BEFORE <!-- COMPLIANCE -->
const complianceMarker = '<!-- COMPLIANCE -->';
const deckSection = `<!-- DECKS -->
<section class="sec" id="decks" style="text-align:center">
<div class="label en">Presentation Decks</div>
<div class="label fr">Decks de Présentation</div>
<div class="title en" style="display:inline-block">Strategy & Architecture Decks</div>
<div class="title fr" style="display:inline-block">Decks Stratégie & Architecture</div>
<p style="color:var(--tx2);font-size:.85rem;margin:.75rem auto 2rem;max-width:560px" class="en">Download our research presentations — built from real deployments, not slides-as-fiction.</p>
<p style="color:var(--tx2);font-size:.85rem;margin:.75rem auto 2rem;max-width:560px" class="fr">Téléchargez nos présentations de recherche — issues de déploiements réels, pas de slides théoriques.</p>
<div style="max-width:860px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:16px;text-align:left">

  <div style="background:var(--s2);border:1px solid var(--bdr);border-radius:12px;padding:24px;display:flex;flex-direction:column;gap:12px">
    <div style="display:flex;align-items:center;gap:10px">
      <div style="width:40px;height:40px;background:rgba(232,163,23,.12);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.3rem">🎯</div>
      <div>
        <div style="font-weight:700;font-size:.95rem" class="en">Vibe Coding Agents in the Enterprise</div>
        <div style="font-weight:700;font-size:.95rem" class="fr">Vibe Coding Agents en Entreprise</div>
        <div style="font-size:.65rem;color:var(--tx3);font-family:'JetBrains Mono',monospace;margin-top:2px">12 slides · NotebookLM Research</div>
      </div>
    </div>
    <p style="font-size:.78rem;color:var(--tx2);line-height:1.6" class="en">Why governance is non-negotiable when building AI agents by natural prompts. Shadow AI, the 5 failure modes, AEGIS-X5 intervention, runtime governance.</p>
    <p style="font-size:.78rem;color:var(--tx2);line-height:1.6" class="fr">Pourquoi la gouvernance est non-négociable quand on construit des agents IA par prompts naturels. Shadow AI, 5 failles, intervention AEGIS-X5.</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <span style="font-size:.6rem;padding:2px 8px;border-radius:4px;background:rgba(232,163,23,.12);color:var(--gold);border:1px solid rgba(232,163,23,.3);font-family:'JetBrains Mono',monospace">Vibe Coding</span>
      <span style="font-size:.6rem;padding:2px 8px;border-radius:4px;background:rgba(28,199,122,.12);color:#1cc77a;border:1px solid rgba(28,199,122,.3);font-family:'JetBrains Mono',monospace">HSE Case</span>
      <span style="font-size:.6rem;padding:2px 8px;border-radius:4px;background:rgba(124,92,250,.12);color:#7c5cfa;border:1px solid rgba(124,92,250,.3);font-family:'JetBrains Mono',monospace">Enterprise</span>
    </div>
    <a href="deck-vibe-coding.pdf" target="_blank" style="display:inline-flex;align-items:center;gap:8px;background:var(--gold);color:#000;font-weight:700;font-size:.8rem;padding:10px 20px;border-radius:8px;text-decoration:none;transition:opacity .2s;margin-top:4px" onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
      ⬇ <span class="en">Download PDF</span><span class="fr">Télécharger PDF</span>
    </a>
  </div>

  <div style="background:var(--s2);border:1px solid var(--bdr);border-radius:12px;padding:24px;display:flex;flex-direction:column;gap:12px">
    <div style="display:flex;align-items:center;gap:10px">
      <div style="width:40px;height:40px;background:rgba(34,184,207,.12);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.3rem">⚔️</div>
      <div>
        <div style="font-weight:700;font-size:.95rem" class="en">AEGIS-X5 vs The Market</div>
        <div style="font-weight:700;font-size:.95rem" class="fr">AEGIS-X5 vs Le Marché</div>
        <div style="font-size:.65rem;color:var(--tx3);font-family:'JetBrains Mono',monospace;margin-top:2px">8 slides · AgenticX5 Research</div>
      </div>
    </div>
    <p style="font-size:.78rem;color:var(--tx2);line-height:1.6" class="en">Why agentic governance requires a new category. Fragmented market analysis, functional coverage matrix, autonomous correction vs passive monitoring.</p>
    <p style="font-size:.78rem;color:var(--tx2);line-height:1.6" class="fr">Pourquoi la gouvernance agentique nécessite une nouvelle catégorie. Analyse marché, matrice de couverture fonctionnelle, correction autonome.</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <span style="font-size:.6rem;padding:2px 8px;border-radius:4px;background:rgba(34,184,207,.12);color:#22b8cf;border:1px solid rgba(34,184,207,.3);font-family:'JetBrains Mono',monospace">Competitive</span>
      <span style="font-size:.6rem;padding:2px 8px;border-radius:4px;background:rgba(232,163,23,.12);color:var(--gold);border:1px solid rgba(232,163,23,.3);font-family:'JetBrains Mono',monospace">Strategy</span>
      <span style="font-size:.6rem;padding:2px 8px;border-radius:4px;background:rgba(28,199,122,.12);color:#1cc77a;border:1px solid rgba(28,199,122,.3);font-family:'JetBrains Mono',monospace">Architecture</span>
    </div>
    <a href="deck-vs-market.pdf.pdf" target="_blank" style="display:inline-flex;align-items:center;gap:8px;background:var(--gold);color:#000;font-weight:700;font-size:.8rem;padding:10px 20px;border-radius:8px;text-decoration:none;transition:opacity .2s;margin-top:4px" onmouseover="this.style.opacity='.85'" onmouseout="this.style.opacity='1'">
      ⬇ <span class="en">Download PDF</span><span class="fr">Télécharger PDF</span>
    </a>
  </div>

</div>
</section>

`;

if (!c.includes(complianceMarker)) {
  console.log('ERROR: <!-- COMPLIANCE --> not found');
  process.exit(1);
}
c = c.replace(complianceMarker, deckSection + complianceMarker);
console.log('✅ Deck cards injected before COMPLIANCE');

fs.writeFileSync(file, c, 'utf8');
console.log('✅ All done. Deploy aegis-x5-deploy/ to Netlify.');
