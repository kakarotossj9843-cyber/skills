/* IA desde el móvil, sin servidor. Funciona con Claude (de pago) o con IAs gratuitas
 * (Google Gemini, Groq, OpenRouter) a través de su API compatible con OpenAI.
 * La clave la pone cada persona en su teléfono y se guarda SOLO en ese teléfono.
 * Uso:  const r = await Claude.run({ system, messages, tools, handlers, effort });
 * (Internamente todo habla el formato de mensajes de Claude; para los demás proveedores se traduce.) */
(function () {
  const PROVIDERS = {
    gemini: { name: 'Google Gemini — GRATIS (recomendado)', base: 'https://generativelanguage.googleapis.com/v1beta/openai', free: true,
      model: 'gemini-2.5-flash', hint: 'AIza...', keyUrl: 'https://aistudio.google.com/apikey',
      steps: ['Entra en <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener">aistudio.google.com/apikey</a> con tu cuenta de Google.',
        'Pulsa <b>Create API key</b> (crear clave). Es gratis, sin tarjeta.', 'Cópiala y pégala aquí.'],
      note: 'Gratis con límites diarios. En el plan gratuito Google puede usar lo que escribes para mejorar sus productos: no pongas datos muy sensibles.' },
    groq: { name: 'Groq (Llama) — GRATIS', base: 'https://api.groq.com/openai/v1', free: true,
      model: 'llama-3.3-70b-versatile', hint: 'gsk_...', keyUrl: 'https://console.groq.com/keys',
      steps: ['Entra en <a href="https://console.groq.com/keys" target="_blank" rel="noopener">console.groq.com/keys</a> y crea una cuenta gratis.',
        'Pulsa <b>Create API Key</b>.', 'Cópiala y pégala aquí.'],
      note: 'Gratis con límites por minuto y por día. Muy rápido.' },
    openrouter: { name: 'OpenRouter — modelos GRATIS', base: 'https://openrouter.ai/api/v1', free: true,
      model: 'meta-llama/llama-3.3-70b-instruct:free', hint: 'sk-or-...', keyUrl: 'https://openrouter.ai/keys',
      steps: ['Entra en <a href="https://openrouter.ai/keys" target="_blank" rel="noopener">openrouter.ai/keys</a> y crea una cuenta.',
        'Pulsa <b>Create Key</b>.', 'Cópiala y pégala aquí. Usa modelos que terminen en <b>:free</b>.'],
      note: 'Los modelos «:free» son gratis con límites diarios.' },
    claude: { name: 'Claude (Anthropic) — de pago, el más capaz', free: false,
      model: 'claude-opus-5-5', hint: 'sk-ant-...', keyUrl: 'https://console.anthropic.com/settings/keys',
      models: [['claude-opus-5-5', 'Claude Opus 5.5 — el más capaz'], ['claude-sonnet-5-5', 'Claude Sonnet 5.5 — más rápido y barato']],
      steps: ['Entra en <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a> y crea una cuenta.',
        'En <b>Billing</b> añade saldo.', 'En <b>API Keys</b> pulsa <b>Create Key</b>, cópiala y pégala aquí.'],
      note: 'Cada uso se cobra en tu cuenta de Claude. Incluye búsqueda web propia.' },
  };
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* almacenamiento bloqueado */ } },
  };
  // Compatibilidad con la versión anterior (solo Claude)
  if (!store.get('ia-proveedor') && store.get('claude-api-key')) {
    store.set('ia-proveedor', 'claude'); store.set('ia-clave-claude', store.get('claude-api-key'));
    if (store.get('claude-model')) store.set('ia-modelo-claude', store.get('claude-model'));
  }
  const provider = () => (PROVIDERS[store.get('ia-proveedor')] ? store.get('ia-proveedor') : 'gemini');
  const key = (p = provider()) => (store.get('ia-clave-' + p) || '').trim();
  const model = (p = provider()) => store.get('ia-modelo-' + p) || PROVIDERS[p].model;
  const baseUrl = (p) => store.get('ia-base-' + p) || PROVIDERS[p].base;   // ia-base-* solo para pruebas
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // ---------- Ajustes (proveedor + clave + modelo) ----------
  let dlg = null;
  function settingsDialog(reason) {
    return new Promise((resolve) => {
      if (!dlg) {
        dlg = document.createElement('div');
        dlg.className = 'cl-overlay';
        dlg.innerHTML = `
          <div class="cl-modal" role="dialog" aria-modal="true" aria-labelledby="cl-t">
            <h3 id="cl-t">Conectar con la IA</h3>
            <p class="cl-reason"></p>
            <label for="cl-prov">¿Qué IA quieres usar?</label>
            <select id="cl-prov">${Object.entries(PROVIDERS).map(([k, v]) => `<option value="${k}">${v.name}</option>`).join('')}</select>
            <ol class="cl-steps"></ol>
            <label for="cl-key">Tu clave</label>
            <input id="cl-key" type="password" autocomplete="off" spellcheck="false">
            <label for="cl-model">Modelo</label>
            <input id="cl-model" list="cl-models" autocomplete="off" spellcheck="false"><datalist id="cl-models"></datalist>
            <p class="cl-note"></p>
            <div class="cl-row"><button type="button" class="cl-cancel">Cancelar</button><button type="button" class="cl-save">Guardar</button></div>
          </div>`;
        document.body.appendChild(dlg);
      }
      const prov = dlg.querySelector('#cl-prov'), input = dlg.querySelector('#cl-key'), mod = dlg.querySelector('#cl-model'), dl = dlg.querySelector('#cl-models');
      const show = () => {
        const p = prov.value, P = PROVIDERS[p];
        dlg.querySelector('.cl-steps').innerHTML = P.steps.map((s) => `<li>${s}</li>`).join('');
        dlg.querySelector('.cl-note').textContent = '🔒 La clave se guarda solo en este teléfono. ' + P.note;
        input.placeholder = P.hint; input.value = key(p); mod.value = model(p);
        dl.innerHTML = (P.models || [[P.model, '']]).map(([v, t]) => `<option value="${v}">${t}</option>`).join('');
        if (P.free && key(p)) listModels(p).then((ids) => { if (prov.value === p && ids.length) dl.innerHTML = ids.map((v) => `<option value="${v}"></option>`).join(''); });
      };
      dlg.querySelector('.cl-reason').textContent = reason || 'Elige la IA que usará la app. Google Gemini es gratis.';
      prov.value = provider(); prov.onchange = show; show();
      dlg.classList.add('open');
      const close = (ok) => { dlg.classList.remove('open'); dlg.querySelector('.cl-save').onclick = dlg.querySelector('.cl-cancel').onclick = null; resolve(ok); };
      dlg.querySelector('.cl-cancel').onclick = () => close(false);
      dlg.querySelector('.cl-save').onclick = () => {
        const p = prov.value, v = input.value.trim();
        if (v && p === 'claude' && !/^sk-ant-/.test(v)) { input.setCustomValidity('La clave de Claude empieza por sk-ant-'); input.reportValidity(); return; }
        input.setCustomValidity('');
        store.set('ia-proveedor', p); store.set('ia-clave-' + p, v); store.set('ia-modelo-' + p, mod.value.trim() || PROVIDERS[p].model);
        close(!!v);
      };
    });
  }
  async function listModels(p) {
    try {
      const r = await fetch(baseUrl(p) + '/models', { headers: { Authorization: 'Bearer ' + key(p) } });
      const j = await r.json();
      let ids = (j.data || []).map((m) => String(m.id).replace(/^models\//, ''));
      if (p === 'openrouter') ids = ids.filter((x) => x.endsWith(':free'));
      if (p === 'gemini') ids = ids.filter((x) => /gemini/.test(x) && !/embedding|image|tts|audio|live/.test(x));
      return ids.sort();
    } catch (e) { return []; }
  }

  function friendlyError(status, msg, P) {
    if (status === 401 || status === 403 || /api key|API_KEY|invalid.*key/i.test(msg)) return 'La clave no es válida. Revísala en ✳ IA.';
    if (/credit|balance|billing|quota/i.test(msg) && !P.free) return 'Tu cuenta de Claude no tiene saldo. Añádelo en console.anthropic.com → Billing.';
    if (status === 429 || /quota|rate/i.test(msg)) return P.free ? 'Has llegado al límite gratuito por ahora. Espera un minuto (o hasta mañana) y vuelve a intentarlo.' : 'Demasiadas peticiones seguidas. Espera un minuto.';
    if (status === 404 || /model.*(not found|does not exist|decommissioned|deprecated)/i.test(msg)) return 'Ese modelo ya no está disponible. Elige otro en ✳ IA.';
    if (status >= 500) return 'El servicio de IA está saturado. Inténtalo en un momento.';
    return msg;
  }

  // ---------- Claude (formato nativo) ----------
  async function requestClaude(body) {
    let r;
    try {
      r = await fetch((store.get('claude-base-url') || 'https://api.anthropic.com') + '/v1/messages', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-api-key': key('claude'), 'anthropic-version': '2026-10-21',
          'anthropic-beta': 'server-side-fallback-2026-07-01', 'anthropic-dangerous-direct-browser-access': 'true' },
        body: JSON.stringify(Object.assign({ model: model('claude'), fallbacks: 'default' }, body)),
      });
    } catch (e) { throw new Error('Sin conexión a internet. Revisa tus datos o la wifi.'); }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(friendlyError(r.status, (j.error && j.error.message) || r.statusText, PROVIDERS.claude));
    return j;
  }

  // ---------- Proveedores gratuitos (API compatible con OpenAI) ----------
  const blocksText = (c) => (typeof c === 'string' ? c : (c || []).filter((b) => b.type === 'text').map((b) => b.text).join('\n'));
  function toOpenAI(body) {
    const msgs = [];
    const sys = typeof body.system === 'string' ? body.system : blocksText(body.system);
    let sysText = sys || '';
    if (body.output_config && body.output_config.format) sysText += '\n\nResponde ÚNICAMENTE con un objeto JSON válido que cumpla este esquema, sin texto adicional:\n' + JSON.stringify(body.output_config.format.schema);
    if (sysText) msgs.push({ role: 'system', content: sysText });
    for (const m of body.messages) {
      if (typeof m.content === 'string') { msgs.push({ role: m.role, content: m.content }); continue; }
      if (m.role === 'assistant') {
        const calls = m.content.filter((b) => b.type === 'tool_use').map((b) => ({ id: b.id, type: 'function', function: { name: b.name, arguments: JSON.stringify(b.input || {}) } }));
        const out = { role: 'assistant', content: blocksText(m.content) || null };
        if (calls.length) out.tool_calls = calls;
        msgs.push(out);
      } else {
        for (const b of m.content) if (b.type === 'tool_result') msgs.push({ role: 'tool', tool_call_id: b.tool_use_id, content: typeof b.content === 'string' ? b.content : JSON.stringify(b.content) });
        const t = blocksText(m.content); if (t) msgs.push({ role: 'user', content: t });
      }
    }
    const req = { model: model(), messages: msgs, max_tokens: Math.min(body.max_tokens || 8000, 8000) };
    const tools = (body.tools || []).filter((t) => t.input_schema).map((t) => ({ type: 'function', function: { name: t.name, description: t.description || '', parameters: t.input_schema } }));
    if (tools.length) req.tools = tools;
    if (body.output_config && body.output_config.format) req.response_format = { type: 'json_object' };
    return req;
  }
  function fromOpenAI(j) {
    const ch = (j.choices || [])[0] || {}, msg = ch.message || {}, content = [];
    let text = msg.content || '';
    if (Array.isArray(text)) text = text.map((p) => p.text || '').join('');
    if (text) content.push({ type: 'text', text: String(text) });
    for (const c of msg.tool_calls || []) {
      let input = {}; try { input = JSON.parse(c.function.arguments || '{}'); } catch (e) { input = {}; }
      content.push({ type: 'tool_use', id: c.id || 'call_' + Math.random().toString(36).slice(2), name: c.function.name, input });
    }
    const stop = (msg.tool_calls || []).length ? 'tool_use' : ch.finish_reason === 'length' ? 'max_tokens' : 'end_turn';
    return { content, stop_reason: stop, usage: { input_tokens: (j.usage && j.usage.prompt_tokens) || 0, output_tokens: (j.usage && j.usage.completion_tokens) || 0 } };
  }
  async function requestFree(body) {
    const p = provider(), P = PROVIDERS[p];
    const req = toOpenAI(body);
    for (let attempt = 0; ; attempt++) {
      let r;
      try {
        r = await fetch(baseUrl(p) + '/chat/completions', { method: 'POST',
          headers: Object.assign({ 'content-type': 'application/json', Authorization: 'Bearer ' + key(p) },
            p === 'openrouter' ? { 'X-Title': 'Proyectos Claude' } : {}), body: JSON.stringify(req) });
      } catch (e) { throw new Error('Sin conexión a internet. Revisa tus datos o la wifi.'); }
      const j = await r.json().catch(() => ({}));
      const err = j.error ? (j.error.message || JSON.stringify(j.error)) : '';
      if (r.ok && !j.error) return fromOpenAI(j);
      // Límite por minuto de los planes gratis: esperar y reintentar (hasta 3 veces)
      if ((r.status === 429 || r.status === 503) && attempt < 3) {
        const wait = Math.min(60, +(r.headers.get('retry-after') || 0) || 8 * (attempt + 1));
        await sleep(wait * 1000); continue;
      }
      throw new Error(friendlyError(r.status, err || r.statusText, P));
    }
  }

  // ---------- Búsqueda web gratuita (para las IAs que no la traen) ----------
  async function webSearch(query) {
    const out = [];
    try {
      const r = await fetch('https://html.duckduckgo.com/html/?q=' + encodeURIComponent(query) + '&kl=es-es');
      const doc = new DOMParser().parseFromString(await r.text(), 'text/html');
      for (const res of doc.querySelectorAll('.result')) {
        const a = res.querySelector('.result__a'); if (!a) continue;
        let url = a.getAttribute('href') || '';
        const m = url.match(/[?&]uddg=([^&]+)/); if (m) url = decodeURIComponent(m[1]);
        if (url.startsWith('//')) url = 'https:' + url;
        if (!/^https?:/.test(url) || /duckduckgo\.com\/y\.js/.test(url)) continue;
        out.push({ titulo: a.textContent.trim(), url, fragmento: ((res.querySelector('.result__snippet') || {}).textContent || '').trim() });
        if (out.length >= 8) break;
      }
    } catch (e) { /* probamos con Wikipedia */ }
    if (!out.length) {
      try {
        const r = await fetch('https://es.wikipedia.org/w/api.php?action=query&list=search&format=json&origin=*&srlimit=6&srsearch=' + encodeURIComponent(query));
        const j = await r.json();
        for (const s of (j.query && j.query.search) || []) out.push({ titulo: s.title, url: 'https://es.wikipedia.org/wiki/' + encodeURIComponent(s.title.replace(/ /g, '_')),
          fragmento: s.snippet.replace(/<[^>]+>/g, '') });
      } catch (e) { /* sin resultados */ }
    }
    return out.length ? out : 'No encontré resultados (o no hay conexión). Responde con lo que sepas y dilo.';
  }
  async function webFetch(url) {
    if (!/^https?:\/\//.test(url)) throw new Error('URL no válida');
    const r = await fetch(url);
    const html = await r.text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    doc.querySelectorAll('script,style,noscript,svg,nav,footer,header,iframe,form').forEach((n) => n.remove());
    const text = (doc.body ? doc.body.textContent : html).replace(/\s+/g, ' ').trim();
    return `Título: ${(doc.title || '').trim()}\n\n${text.slice(0, 15000)}`;
  }
  const FREE_WEB_TOOLS = [
    { name: 'buscar_en_internet', description: 'Busca en internet (resultados con título, enlace y fragmento). Úsalo para información actual.',
      input_schema: { type: 'object', properties: { consulta: { type: 'string' } }, required: ['consulta'] } },
    { name: 'leer_pagina', description: 'Lee el texto de una página web por su URL (por ejemplo, un resultado de buscar_en_internet).',
      input_schema: { type: 'object', properties: { url: { type: 'string' } }, required: ['url'] } },
  ];
  const FREE_WEB_HANDLERS = { buscar_en_internet: (i) => webSearch(i.consulta), leer_pagina: (i) => webFetch(i.url) };

  // ---------- Petición y bucle de herramientas ----------
  async function request(body) {
    if (!key() && !(await settingsDialog())) throw new Error('Falta tu clave de IA (botón ✳ IA).');
    return provider() === 'claude' ? requestClaude(body) : requestFree(body);
  }
  const textOf = (m) => (m.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('\n').trim();

  /** Ejecuta las herramientas que pida la IA hasta tener la respuesta final. */
  async function run({ system, messages, tools = [], handlers = {}, effort = 'medium', max_tokens = 16000, format, maxTurns = 25, onStep }) {
    const msgs = messages.slice();
    if (provider() !== 'claude' && tools.some((t) => /^web_(search|fetch)_/.test(t.type || ''))) {
      tools = tools.filter((t) => !/^web_(search|fetch)_/.test(t.type || '')).concat(FREE_WEB_TOOLS);
      handlers = Object.assign({}, handlers, FREE_WEB_HANDLERS);
    }
    for (let turn = 0; turn < maxTurns; turn++) {
      const body = { max_tokens, messages: msgs, output_config: { effort } };
      if (system) body.system = system;
      if (format) body.output_config.format = format;
      if (tools.length) body.tools = tools;
      const res = await request(body);
      if (onStep) onStep(res);
      if (res.stop_reason === 'refusal') throw new Error('La IA no puede ayudar con esa petición.');
      msgs.push({ role: 'assistant', content: res.content });
      if (res.stop_reason === 'pause_turn') continue;           // búsqueda web larga de Claude: continuar
      if (res.stop_reason !== 'tool_use') return { message: res, text: textOf(res), messages: msgs };
      const uses = res.content.filter((b) => b.type === 'tool_use');
      const results = await Promise.all(uses.map(async (u) => {
        try {
          const h = handlers[u.name];
          if (!h) throw new Error('herramienta desconocida: ' + u.name);
          const out = await h(u.input || {});
          return { type: 'tool_result', tool_use_id: u.id, content: typeof out === 'string' ? out : JSON.stringify(out) };
        } catch (e) {
          return { type: 'tool_result', tool_use_id: u.id, content: 'Error: ' + e.message, is_error: true };
        }
      }));
      msgs.push({ role: 'user', content: results });
    }
    throw new Error('La IA necesitó demasiados pasos. Prueba con una petición más concreta.');
  }

  /** Para respuestas en JSON: los modelos gratuitos a veces añaden texto alrededor. */
  function parseJSON(text) {
    try { return JSON.parse(text); } catch (e) { /* buscamos el objeto dentro del texto */ }
    const a = text.indexOf('{'), b = text.lastIndexOf('}');
    if (a >= 0 && b > a) return JSON.parse(text.slice(a, b + 1));
    throw new Error('La IA no devolvió un formato válido. Inténtalo otra vez.');
  }

  const WEB_TOOLS = [
    { type: 'web_search_20260209', name: 'web_search', max_uses: 10 },
    { type: 'web_fetch_20260209', name: 'web_fetch', max_uses: 6, max_content_tokens: 20000 },
  ];

  // Estilos del diálogo (usa los colores de cada app si existen)
  const css = document.createElement('style');
  css.textContent = `
    .cl-overlay{position:fixed;inset:0;background:rgba(0,0,0,.65);display:none;align-items:flex-end;justify-content:center;z-index:1000;padding:12px}
    .cl-overlay.open{display:flex}
    @media(min-width:560px){.cl-overlay{align-items:center}}
    .cl-modal{width:min(460px,100%);max-height:92vh;overflow:auto;background:var(--cl-bg,#1b1b1b);color:var(--cl-text,#f5f5f5);
      border:1px solid var(--cl-accent,#ff7a3d);border-radius:18px;padding:18px;font:15px/1.45 system-ui,-apple-system,Roboto,sans-serif}
    .cl-modal h3{margin:0 0 6px;color:var(--cl-accent,#ff7a3d);font-size:19px}
    .cl-modal p{margin:6px 0;color:var(--cl-muted,#b9b9b9)} .cl-steps{margin:8px 0 6px;padding-left:20px;color:var(--cl-muted,#b9b9b9)}
    .cl-modal a{color:var(--cl-accent,#ff7a3d)} .cl-modal label{display:block;font-size:13px;margin:10px 0 4px;color:var(--cl-muted,#b9b9b9)}
    .cl-modal input,.cl-modal select{width:100%;box-sizing:border-box;font:inherit;padding:11px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.06);color:inherit}
    .cl-modal select option{color:#111}
    .cl-note{font-size:12.5px} .cl-row{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}
    .cl-row button{font:inherit;font-weight:700;padding:11px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:transparent;color:inherit}
    .cl-row .cl-save{background:var(--cl-accent,#ff7a3d);border-color:var(--cl-accent,#ff7a3d);color:#111}`;
  document.head.appendChild(css);

  window.Claude = { run, request, textOf, parseJSON, settings: settingsDialog, hasKey: () => !!key(), isFree: () => provider() !== 'claude',
    WEB_TOOLS, _webSearch: webSearch, _toOpenAI: toOpenAI, _fromOpenAI: fromOpenAI };
})();
