const fs = require('fs');

const newSection = `<!-- FRAMEWORKS -->
<section class="sec" id="frameworks" style="text-align:center">
<div class="label en">Integrations & Ecosystem</div>
<div class="label fr">Intégrations & Écosystème</div>
<div class="title en" style="display:inline-block">Works with your stack. Any stack.</div>
<div class="title fr" style="display:inline-block">Compatible avec votre stack. N'importe laquelle.</div>
<p style="color:var(--tx2);font-size:.85rem;margin:.75rem auto 0;max-width:560px" class="en">Connect AEGIS-X5 to your existing agents in minutes — no rearchitecting required.</p>
<p style="color:var(--tx2);font-size:.85rem;margin:.75rem auto 0;max-width:560px" class="fr">Connectez AEGIS-X5 à vos agents existants en quelques minutes — sans refactoring.</p>

<div style="max-width:920px;margin:0 auto">

<div class="int-section-label en">🔗 Orchestration Frameworks</div>
<div class="int-section-label fr">🔗 Frameworks d'Orchestration</div>
<div class="int-grid">
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🦜</div><span class="int-card-name">LangChain</span></div>
    <div class="int-card-tag cy en">Orchestration</div>
    <div class="int-card-desc en">Full chain observability. Wrap any LangChain agent with @observe in one line.</div>
    <div class="int-card-desc fr">Observabilité complète. Wrappez n'importe quel agent en une ligne.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">👥</div><span class="int-card-name">CrewAI</span></div>
    <div class="int-card-tag vi en">Multi-Agent</div>
    <div class="int-card-desc en">Guard each role, trace crew coordination, audit decisions across agents.</div>
    <div class="int-card-desc fr">Guard par rôle, trace de coordination, audit des décisions inter-agents.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🕸️</div><span class="int-card-name">LangGraph</span></div>
    <div class="int-card-tag cy en">State Machine</div>
    <div class="int-card-desc en">Monitor graph transitions, detect loop anomalies, guard node outputs.</div>
    <div class="int-card-desc fr">Transitions, boucles, outputs de nœuds — surveillés en temps réel.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🤖</div><span class="int-card-name">AutoGen</span></div>
    <div class="int-card-tag bl en">Conversational</div>
    <div class="int-card-desc en">Trace agent-to-agent messages, guard multi-turn outputs, audit decisions.</div>
    <div class="int-card-desc fr">Traces agent-à-agent, guard sur les tours de dialogue.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🦙</div><span class="int-card-name">LlamaIndex</span></div>
    <div class="int-card-tag gr en">RAG Pipeline</div>
    <div class="int-card-desc en">DriftPredictor on faithfulness, automatic reindex triggers, RAG governance.</div>
    <div class="int-card-desc fr">DriftPredictor sur faithfulness, reindex automatique.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🌾</div><span class="int-card-name">Haystack</span></div>
    <div class="int-card-tag gr en">Pipeline</div>
    <div class="int-card-desc en">Observe each component, guard final outputs, evaluate answers per stage.</div>
    <div class="int-card-desc fr">Observe, guard et évalue chaque étape du pipeline.</div>
    <div class="int-badge prod">Production</div>
  </div>
</div>

<div class="int-section-label en">🤖 LLM Providers</div>
<div class="int-section-label fr">🤖 Fournisseurs LLM</div>
<div class="int-grid">
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">⚡</div><span class="int-card-name">OpenAI</span></div>
    <div class="int-card-tag cy en">GPT-4o · o3</div>
    <div class="int-card-desc en">Token cost tracking per model, latency p95, Guard on completions.</div>
    <div class="int-card-desc fr">Coûts par modèle, latence p95, Guard sur les completions.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🧠</div><span class="int-card-name">Anthropic</span></div>
    <div class="int-card-tag vi en">Claude 4.6</div>
    <div class="int-card-desc en">Native SDK integration. Observe thinking chains, guard outputs, evaluate faithfulness.</div>
    <div class="int-card-desc fr">Intégration native SDK. Observe, guard, évalue les outputs Claude.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🔥</div><span class="int-card-name">Open Models</span></div>
    <div class="int-card-tag gr en">Llama · Mistral</div>
    <div class="int-card-desc en">Llama 3.3, Mistral Large, local models via Ollama — same governance layer.</div>
    <div class="int-card-desc fr">Llama, Mistral, modèles locaux Ollama — même couche de gouvernance.</div>
    <div class="int-badge prod">Production</div>
  </div>
</div>

<div class="int-section-label en">📡 Observability & DevOps</div>
<div class="int-section-label fr">📡 Observabilité & DevOps</div>
<div class="int-grid">
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">📊</div><span class="int-card-name">OpenTelemetry</span></div>
    <div class="int-card-tag cy en">Telemetry</div>
    <div class="int-card-desc en">Export AEGIS-X5 traces to any OTel-compatible backend. Grafana, Datadog, Jaeger.</div>
    <div class="int-card-desc fr">Exportez les traces vers tout backend OTel. Grafana, Datadog, Jaeger.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🪝</div><span class="int-card-name">Webhook / REST</span></div>
    <div class="int-card-tag bl en">Universal</div>
    <div class="int-card-desc en">Connect any agent via REST or webhook. No SDK required for basic governance.</div>
    <div class="int-card-desc fr">Connectez n'importe quel agent via REST ou webhook. Sans SDK.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🚀</div><span class="int-card-name">Vercel AI SDK</span></div>
    <div class="int-card-tag gr en">JS / TS</div>
    <div class="int-card-desc en">Govern Next.js AI apps. Observe streaming completions, guard edge outputs.</div>
    <div class="int-card-desc fr">Gouvernez vos apps Next.js IA. Observe streaming, guard edge outputs.</div>
    <div class="int-badge poc">Beta</div>
  </div>
</div>

<div class="int-section-label en">🏭 Industry Templates</div>
<div class="int-section-label fr">🏭 Templates Industrie</div>
<div class="int-grid">
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🦺</div><span class="int-card-name">HSE / SST</span></div>
    <div class="int-card-tag rd en">Regulated</div>
    <div class="int-card-desc en">SST_FactCheck, EPIValidator, CNESSTCompliance, HazardMinimizer. 20 golden test cases.</div>
    <div class="int-card-desc fr">SST_FactCheck, EPIValidator, CNESSTCompliance. 20 cas de test golden.</div>
    <div class="int-badge prod">Production</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🏥</div><span class="int-card-name">Healthcare</span></div>
    <div class="int-card-tag vi en">HIPAA</div>
    <div class="int-card-desc en">PII guard, HIPAA compliance layer, clinical decision support governance.</div>
    <div class="int-card-desc fr">Guard PII, conformité HIPAA, gouvernance aide à la décision clinique.</div>
    <div class="int-badge poc">Roadmap</div>
  </div>
  <div class="int-card">
    <div class="int-card-head"><div class="int-emoji">🏦</div><span class="int-card-name">Finance / Legal</span></div>
    <div class="int-card-tag bl en">SOC2 · GDPR</div>
    <div class="int-card-desc en">Audit trail for financial agents. SOC2, GDPR, regulatory output validation.</div>
    <div class="int-card-desc fr">Audit trail agents financiers. SOC2, RGPD, validation outputs réglementaires.</div>
    <div class="int-badge poc">Roadmap</div>
  </div>
</div>

</div>
</section>
`;

const file = 'aegis-x5-deploy/index.html';
let content = fs.readFileSync(file, 'utf8');
const OLD = '<!-- FRAMEWORKS -->\n\n\n';
if (!content.includes(OLD)) {
  console.log('ERROR: marker not found. Trying alternate...');
  const alt = content.indexOf('<!-- FRAMEWORKS -->');
  console.log('Position:', alt, '| Next 50 chars:', JSON.stringify(content.substring(alt, alt+50)));
  process.exit(1);
}
const updated = content.replace(OLD, newSection);
fs.writeFileSync(file, updated, 'utf8');
console.log('✅ Done. Section replaced successfully.');
