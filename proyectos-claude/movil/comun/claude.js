/* Claude desde el móvil, sin servidor.
 * La clave de Claude la pone cada persona en su teléfono y se guarda SOLO en ese teléfono.
 * Uso:  const r = await Claude.run({ system, messages, tools, handlers, effort });
 */
(function () {
  const KEY = 'claude-api-key', MODEL = 'claude-model';
  const MODELS = [
    ['claude-opus-5-5', 'Claude Opus 5.5 — el más capaz (recomendado)'],
    ['claude-sonnet-5-5', 'Claude Sonnet 5.5 — más rápido y barato'],
  ];
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* almacenamiento bloqueado */ } },
  };
  const endpoint = () => (store.get('claude-base-url') || 'https://api.anthropic.com') + '/v1/messages';
  const key = () => (store.get(KEY) || '').trim();
  const model = () => store.get(MODEL) || MODELS[0][0];

  // ---------- Ajustes (clave + modelo) ----------
  let dlg = null;
  function settingsDialog(reason) {
    return new Promise((resolve) => {
      if (!dlg) {
        dlg = document.createElement('div');
        dlg.className = 'cl-overlay';
        dlg.innerHTML = `
          <div class="cl-modal" role="dialog" aria-modal="true" aria-labelledby="cl-t">
            <h3 id="cl-t">Conectar con Claude</h3>
            <p class="cl-reason"></p>
            <ol class="cl-steps">
              <li>Entra en <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a> y crea una cuenta.</li>
              <li>En <b>Billing</b> añade un poco de saldo.</li>
              <li>En <b>API Keys</b> pulsa <b>Create Key</b>, cópiala y pégala aquí.</li>
            </ol>
            <label for="cl-key">Tu clave de Claude</label>
            <input id="cl-key" type="password" autocomplete="off" spellcheck="false" placeholder="sk-ant-...">
            <label for="cl-model">Modelo</label>
            <select id="cl-model">${MODELS.map(([v, t]) => `<option value="${v}">${t}</option>`).join('')}</select>
            <p class="cl-note">🔒 La clave se guarda solo en este teléfono. Cada uso se cobra en tu cuenta de Claude.</p>
            <div class="cl-row"><button type="button" class="cl-cancel">Cancelar</button><button type="button" class="cl-save">Guardar</button></div>
          </div>`;
        document.body.appendChild(dlg);
      }
      const input = dlg.querySelector('#cl-key'), sel = dlg.querySelector('#cl-model');
      dlg.querySelector('.cl-reason').textContent = reason || 'Esta app usa Claude. Pega tu clave de Claude para empezar.';
      input.value = key(); sel.value = model();
      dlg.classList.add('open');
      setTimeout(() => input.focus(), 50);
      const close = (ok) => {
        dlg.classList.remove('open');
        dlg.querySelector('.cl-save').onclick = dlg.querySelector('.cl-cancel').onclick = null;
        resolve(ok);
      };
      dlg.querySelector('.cl-cancel').onclick = () => close(false);
      dlg.querySelector('.cl-save').onclick = () => {
        const v = input.value.trim();
        if (v && !/^sk-ant-/.test(v)) { input.setCustomValidity('La clave empieza por sk-ant-'); input.reportValidity(); return; }
        input.setCustomValidity('');
        store.set(KEY, v); store.set(MODEL, sel.value);
        close(!!v);
      };
    });
  }

  // ---------- Llamada a la API ----------
  async function request(body) {
    if (!key() && !(await settingsDialog())) throw new Error('Falta tu clave de Claude (botón ⚙️).');
    let r;
    try {
      r = await fetch(endpoint(), {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': key(),
          'anthropic-version': '2026-10-21',
          'anthropic-beta': 'server-side-fallback-2026-07-01',
          'anthropic-dangerous-direct-browser-access': 'true',
        },
        body: JSON.stringify(Object.assign({ model: model(), fallbacks: 'default' }, body)),
      });
    } catch (e) {
      throw new Error('Sin conexión a internet. Revisa tus datos o la wifi.');
    }
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      const msg = (j.error && j.error.message) || r.statusText || 'Error';
      if (r.status === 401) { store.set(KEY, ''); throw new Error('La clave de Claude no es válida. Ponla de nuevo en ⚙️.'); }
      if (/credit|balance|billing/i.test(msg)) throw new Error('Tu cuenta de Claude no tiene saldo. Añádelo en console.anthropic.com → Billing.');
      if (r.status === 429) throw new Error('Demasiadas peticiones seguidas. Espera un minuto y vuelve a intentarlo.');
      if (r.status >= 500) throw new Error('Claude está saturado ahora mismo. Inténtalo en un momento.');
      throw new Error(msg);
    }
    return j;
  }

  const textOf = (m) => (m.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('\n').trim();

  /** Bucle de herramientas: ejecuta las herramientas que pida Claude hasta tener la respuesta final. */
  async function run({ system, messages, tools = [], handlers = {}, effort = 'medium', max_tokens = 16000, format, maxTurns = 25, onStep }) {
    const msgs = messages.slice();
    for (let turn = 0; turn < maxTurns; turn++) {
      const body = { max_tokens, messages: msgs, output_config: { effort } };
      if (system) body.system = system;
      if (format) body.output_config.format = format;
      if (tools.length) body.tools = tools;
      const res = await request(body);
      if (onStep) onStep(res);
      if (res.stop_reason === 'refusal') throw new Error('Claude no puede ayudar con esa petición.');
      msgs.push({ role: 'assistant', content: res.content });
      if (res.stop_reason === 'pause_turn') continue;           // búsqueda web larga: continuar
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
    throw new Error('Claude necesitó demasiados pasos. Prueba con una petición más concreta.');
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
    .cl-modal p{margin:6px 0;color:var(--cl-muted,#b9b9b9)} .cl-steps{margin:6px 0 10px;padding-left:20px;color:var(--cl-muted,#b9b9b9)}
    .cl-modal a{color:var(--cl-accent,#ff7a3d)} .cl-modal label{display:block;font-size:13px;margin:10px 0 4px;color:var(--cl-muted,#b9b9b9)}
    .cl-modal input,.cl-modal select{width:100%;box-sizing:border-box;font:inherit;padding:11px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:rgba(255,255,255,.06);color:inherit}
    .cl-note{font-size:12.5px} .cl-row{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}
    .cl-row button{font:inherit;font-weight:700;padding:11px 16px;border-radius:12px;border:1px solid rgba(255,255,255,.18);background:transparent;color:inherit}
    .cl-row .cl-save{background:var(--cl-accent,#ff7a3d);border-color:var(--cl-accent,#ff7a3d);color:#111}`;
  document.head.appendChild(css);

  window.Claude = { run, request, textOf, settings: settingsDialog, hasKey: () => !!key(), WEB_TOOLS };
})();
