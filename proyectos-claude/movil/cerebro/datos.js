/* Segundo cerebro — versión móvil: las notas (Markdown) viven en el teléfono.
 * Reproduce la API del servidor (cerebro/server.py + vault.py + agent.py). */
(function () {
  const { Store } = window.Movil;
  let N = Store.load('cerebro-notas', null);
  if (!N) { N = Object.assign({}, window.NOTAS_INICIALES || {}); Store.save('cerebro-notas', N); }
  const save = () => Store.save('cerebro-notas', N);
  const PROFILE = 'PERFIL.md';
  const LINK_RE = /\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]/g;
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };

  function norm(path) {
    let p = String(path || '').trim().replace(/^[/\\]+/, '').replace(/\\/g, '/');
    if (!p) throw new Error('Ruta vacía');
    if (p.split('/').some((x) => x === '..' || x === '.')) throw new Error('Ruta no permitida');
    if (!p.endsWith('.md')) p += '.md';
    return p;
  }
  const title = (p) => p.split('/').pop().replace(/\.md$/, '');
  const paths = () => Object.keys(N).sort();
  function find(path) {
    const p = norm(path);
    if (p in N) return p;
    const t = title(p).toLowerCase();
    return paths().find((x) => title(x).toLowerCase() === t) || null;
  }
  function read(path) { const p = find(path); if (!p) throw new Error('No existe la nota ' + path); return N[p]; }
  function write(path, content, overwrite) {
    const p = norm(path);
    if (p in N && !overwrite) throw new Error('Ya existe ' + p + '. Usa append_to_note para añadir información.');
    N[p] = String(content).replace(/\s+$/, '') + '\n'; save(); return p;
  }
  function append(path, content) {
    const p = find(path) || norm(path);
    if (!(p in N)) return write(p, `# ${title(p)}\n\n${content}`);
    N[p] = N[p].replace(/\s+$/, '') + `\n\n## ${today()}\n${String(content).replace(/\s+$/, '')}\n`; save(); return p;
  }
  const tokens = (t) => (String(t).toLowerCase().match(/[\p{L}\p{N}]+/gu) || []).filter((w) => w.length > 2);
  function search(query, limit = 8) {
    const terms = [...new Set(tokens(query))];
    if (!terms.length) return [];
    const out = [];
    for (const p of paths()) {
      const text = N[p], low = text.toLowerCase(), t = title(p).toLowerCase();
      let score = 0; for (const w of terms) { score += low.split(w).length - 1; if (t.includes(w)) score += 5; }
      if (score) {
        const idx = Math.min(...terms.map((w) => low.indexOf(w)).filter((i) => i >= 0));
        out.push({ path: p, score, snippet: text.slice(Math.max(0, idx - 120), idx + 240).replace(/\n/g, ' ').trim() });
      }
    }
    return out.sort((a, b) => b.score - a.score).slice(0, limit);
  }
  function graph() {
    const byTitle = {}; for (const p of paths()) byTitle[title(p).toLowerCase()] = p;
    const nodes = [], edges = [];
    for (const p of paths()) {
      nodes.push({ id: p, title: title(p), area: p.includes('/') ? p.split('/')[0] : 'raíz' });
      for (const m of N[p].matchAll(LINK_RE)) {
        const target = byTitle[title(m[1].trim()).toLowerCase()];
        if (target && target !== p) edges.push({ source: p, target });
      }
    }
    return { nodes, edges };
  }

  // ---------- Claude ----------
  const TOOLS = [
    { name: 'list_notes', description: 'Lista todas las notas (rutas). Úsalo para orientarte o elegir dónde archivar.', input_schema: { type: 'object', properties: {} } },
    { name: 'search_notes', description: 'Busca notas por palabras clave y devuelve rutas con un fragmento. Haz varias búsquedas con sinónimos si hace falta.',
      input_schema: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] } },
    { name: 'read_note', description: 'Lee una nota completa (ruta o solo el título).', input_schema: { type: 'object', properties: { path: { type: 'string' } }, required: ['path'] } },
    { name: 'create_note', description: 'Crea una nota NUEVA en Markdown, empezando por «# Título». Enlaza conceptos con [[Título]] y añade #etiquetas.',
      input_schema: { type: 'object', properties: { path: { type: 'string', description: "ej. '30-Areas/Salud/Rutina de gimnasio.md'" }, content: { type: 'string' } }, required: ['path', 'content'] } },
    { name: 'append_to_note', description: 'Añade información nueva al final de una nota existente (con fecha). Si no existe, la crea.',
      input_schema: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] } },
    { name: 'rewrite_note', description: 'Reescribe por completo una nota existente (para reorganizarla o corregirla). Conserva la información valiosa.',
      input_schema: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] } },
    { name: 'update_profile', description: 'Reescribe PERFIL.md (resumen de quién es el usuario, máx. ~80 líneas): identidad, objetivos, negocio, personas clave, preferencias.',
      input_schema: { type: 'object', properties: { content: { type: 'string' } }, required: ['content'] } },
  ];
  const HANDLERS = {
    list_notes: () => paths().join('\n') || '(sin notas)',
    search_notes: (i) => search(i.query),
    read_note: (i) => { try { return read(i.path); } catch (e) { return e.message; } },
    create_note: (i) => { try { return 'Creada: ' + write(i.path, i.content, false); } catch (e) { return e.message; } },
    append_to_note: (i) => 'Actualizada: ' + append(i.path, i.content),
    rewrite_note: (i) => 'Reescrita: ' + write(find(i.path) || i.path, i.content, true),
    update_profile: (i) => 'Perfil actualizado: ' + write(PROFILE, i.content, true),
  };
  const INSTRUCTIONS = `Eres el segundo cerebro del usuario: una biblioteca infinita de contexto sobre su vida, su negocio y sus áreas personales, guardada como notas Markdown.

Estructura:
- 10-Vida/     personas, familia, recuerdos, objetivos vitales, diario
- 20-Negocio/  empresa, clientes, productos, ideas, procesos, métricas
- 30-Areas/    Salud, Finanzas, Relaciones, Aprendizaje (y las que hagan falta)
- PERFIL.md    resumen de quién es el usuario (lo tienes abajo)

Reglas:
- Responde en español, claro y breve (se lee en el móvil). Para responder, BUSCA y LEE notas antes de contestar; cita las notas que usas con [[Título]]. Si no hay información, dilo y pregunta.
- Cuando el usuario cuente algo nuevo y duradero, guárdalo sin que te lo pida: en la nota existente (append_to_note) o en una nueva bien ubicada (create_note). Una idea por nota, enlaces [[...]] y #etiquetas.
- Si aprendes algo importante sobre quién es, actualiza PERFIL.md con update_profile, breve.
- Nunca borres información valiosa. No inventes datos.`;
  const system = () => [{ type: 'text', text: INSTRUCTIONS },
    { type: 'text', text: '<perfil>\n' + (N[PROFILE] || '(vacío: aún no conoces al usuario)') + '\n</perfil>', cache_control: { type: 'ephemeral' } }];

  async function ask(message, history) {
    const r = await Claude.run({ system: system(), tools: TOOLS, handlers: HANDLERS, effort: 'medium', maxTurns: 30,
      messages: [...history, { role: 'user', content: `(Hoy es ${today()})\n\n${message}` }] });
    return r.text || 'Hecho.';
  }
  async function capture(raw) {
    const r = await Claude.run({ system: system(), tools: TOOLS, handlers: HANDLERS, effort: 'medium', maxTurns: 30,
      messages: [{ role: 'user', content: `(Hoy es ${today()}) Procesa este material y archívalo en mi segundo cerebro: revisa qué notas existen, ` +
        'divide el contenido por temas, crea o amplía las notas adecuadas con enlaces [[...]] y actualiza PERFIL.md si aprendes algo importante de mí. ' +
        `Al final dime en 3-6 líneas qué has guardado y dónde.\n\n<material>\n${raw}\n</material>` }] });
    return r.text || 'Guardado.';
  }

  async function handle(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const body = opts.body ? JSON.parse(opts.body) : {};
    const [route, query] = path.replace(/^api\//, '').split('?');
    if (route === 'graph') return graph();
    if (route === 'note' && method === 'GET') {
      const p = new URLSearchParams(query).get('path');
      const f = find(p); if (!f) throw new Error('No existe'); return { path: f, content: N[f] };
    }
    if (route === 'note' && method === 'POST') { const p = body.overwrite ? write(body.path, body.content, true) : write(body.path, body.content, false); return { path: p }; }
    if (route === 'note' && method === 'DELETE') { const f = find(body.path); if (f) { delete N[f]; save(); } return { ok: true }; }
    if (route === 'chat') {
      const hist = (body.history || []).filter((m) => (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string').slice(-20);
      while (hist.length && hist[0].role !== 'user') hist.shift();
      return { reply: body.mode === 'capture' ? await capture(body.message) : await ask(body.message, hist) };
    }
    if (route === 'copia' && method === 'GET') return N;
    if (route === 'copia' && method === 'POST') {
      if (!body || typeof body !== 'object' || Array.isArray(body) || !Object.keys(body).every((k) => k.endsWith('.md'))) throw new Error('Ese archivo no es una copia del cerebro');
      N = body; save(); return { ok: true };
    }
    throw new Error('Ruta desconocida: ' + path);
  }
  window.CerebroLocal = { handle, paths: () => paths() };
})();
