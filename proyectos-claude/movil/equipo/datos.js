/* Equipo de agentes — versión móvil: el jefe y sus 4 subagentes trabajan desde el teléfono.
 * Reproduce la API del servidor (equipo/server.py + team.py + job.py). */
(function () {
  const { Store } = window.Movil;
  const AGENTS = ['jefe', 'busca', 'escribe', 'disena', 'revisa'];
  const EXT = ['.md', '.txt', '.html', '.svg', '.css', '.json', '.csv'];
  let JOBS = Store.load('equipo-trabajos', {});
  const active = new Set();
  const save = () => {
    const ids = Object.keys(JOBS).sort().reverse();
    for (const id of ids.slice(15)) delete JOBS[id];      // guarda los 15 últimos
    Store.save('equipo-trabajos', JOBS);
  };
  // Trabajos que quedaron a medias al cerrar la app
  for (const j of Object.values(JOBS)) if (j.estado === 'trabajando') {
    j.estado = 'error'; j.error = 'Se interrumpió (se cerró la app mientras trabajaba)';
    for (const a of Object.values(j.agentes)) if (a.estado === 'trabajando') a.estado = 'libre';
  }
  save();

  const SUB = {
    busca: { nombre: 'Busca', web: true, system: 'Eres «Busca», el investigador del equipo. Buscas en internet información actual y fiable, contrastas fuentes y nunca inventas. ' +
      'Guarda tu investigación en un archivo .md (con enlaces) con guardar_archivo y termina con un resumen de 3-6 líneas y el nombre del archivo.' },
    escribe: { nombre: 'Escribe', web: false, system: 'Eres «Escribe», el redactor del equipo. Escribes textos claros, persuasivos y sin relleno, en el idioma y tono del encargo. ' +
      'Lee primero los archivos que te indiquen. Guarda tu trabajo con guardar_archivo (.md) y termina diciendo qué archivo has creado y qué contiene.' },
    disena: { nombre: 'Diseña', web: false, system: 'Eres «Diseña», el diseñador del equipo. Creas piezas visuales como archivos HTML autocontenidos (CSS en <style>, SIN JavaScript, ' +
      'sin imágenes externas: usa SVG inline, degradados y tipografía del sistema). Diseño moderno, buen contraste y pensado para verse en el móvil. ' +
      'Usa los textos que te indiquen tal cual. Guarda con guardar_archivo (.html o .svg) y termina diciendo qué archivo has creado.' },
    revisa: { nombre: 'Revisa', web: false, system: 'Eres «Revisa», el control de calidad. Lees los archivos indicados y los compruebas contra el encargo: errores, datos sin fuente, ' +
      'ortografía, tono, claridad, que el diseño use los textos correctos y sea legible. Responde SIEMPRE empezando por «VEREDICTO: APROBADO» o «VEREDICTO: CAMBIOS», ' +
      'seguido de una lista corta y concreta de cambios (archivo y qué cambiar). Exigente pero justo.' },
  };
  const JEFE = `Eres «El jefe»: diriges un equipo de 4 subagentes para cumplir el encargo del usuario con calidad profesional.

Tu equipo:
- busca: investiga en internet y guarda la investigación en .md
- escribe: redacta textos y los guarda en .md
- disena: crea piezas visuales como HTML/SVG autocontenido (landing, carrusel, infografía, post)
- revisa: control de calidad; responde VEREDICTO: APROBADO o VEREDICTO: CAMBIOS

Cómo trabajas:
1. Divide el encargo en tareas. Usa \`delegar\` con varias tareas a la vez cuando sean independientes (van en paralelo).
2. Cada subagente empieza de cero: dale TODO el contexto (objetivo, público, tono, idioma, formato, nombres exactos de archivos a leer y crear).
3. Antes de entregar, manda SIEMPRE el resultado a \`revisa\`. Si pide cambios, delega las correcciones y vuelve a revisar (máximo 2 rondas).
4. Termina llamando a \`entregar\` con un resumen y la lista de archivos finales. Tú planificas y decides; no hagas el trabajo de los especialistas.
5. Mensajes al usuario en español y breves.`;

  function newJob(encargo) {
    const d = new Date(), id = d.toISOString().replace(/[-:T]/g, '').slice(0, 14) + '-' + Math.random().toString(16).slice(2, 6);
    JOBS[id] = { id, encargo, estado: 'trabajando', creado: d.toISOString(), fin: null, resumen: null, entregables: [], error: null,
      agentes: Object.fromEntries(AGENTS.map((a) => [a, { estado: 'libre', tarea: '', trabajos: 0 }])), eventos: [], uso: { entrada: 0, salida: 0 }, archivos: {} };
    save(); return JOBS[id];
  }
  const ev = (j, agente, tipo, texto) => { j.eventos.push({ t: Date.now() / 1000, agente, tipo, texto: String(texto).slice(0, 600) }); save(); };
  function setAgent(j, a, estado, tarea) { const x = j.agentes[a]; x.estado = estado; if (tarea) x.tarea = tarea.slice(0, 200); if (estado === 'trabajando') x.trabajos++; save(); }
  const usage = (j, m) => { if (m.usage) { j.uso.entrada += (m.usage.input_tokens || 0) + (m.usage.cache_read_input_tokens || 0); j.uso.salida += m.usage.output_tokens || 0; } };
  function checkName(n) {
    n = String(n || '').trim().replace(/^[/\\]+/, '');
    if (!n || n.split('/').some((x) => x === '..')) throw new Error('Nombre no permitido');
    if (!EXT.some((e) => n.toLowerCase().endsWith(e))) throw new Error('Extensión no permitida. Usa: ' + EXT.join(', '));
    return n;
  }
  function fileTools(j, canWrite) {
    const tools = [
      { name: 'listar_archivos', description: 'Lista los archivos del trabajo.', input_schema: { type: 'object', properties: {} } },
      { name: 'leer_archivo', description: 'Lee un archivo del trabajo.', input_schema: { type: 'object', properties: { nombre: { type: 'string' } }, required: ['nombre'] } },
    ];
    const handlers = {
      listar_archivos: () => Object.keys(j.archivos).sort(),
      leer_archivo: (i) => { const n = checkName(i.nombre); if (!(n in j.archivos)) return 'No existe. Archivos: ' + Object.keys(j.archivos).join(', '); return j.archivos[n]; },
    };
    if (canWrite) {
      tools.push({ name: 'guardar_archivo', description: 'Crea o reemplaza un archivo del trabajo (.md, .html, .svg, .txt, .json, .csv, .css).',
        input_schema: { type: 'object', properties: { nombre: { type: 'string' }, contenido: { type: 'string' } }, required: ['nombre', 'contenido'] } });
      handlers.guardar_archivo = (i) => { const n = checkName(i.nombre); j.archivos[n] = String(i.contenido); save(); return 'Guardado: ' + n; };
    }
    return { tools, handlers };
  }
  function describe(b) {
    const i = b.input || {};
    if (b.type === 'server_tool_use') return b.name === 'web_search' ? '🔎 ' + (i.query || '') : '🌐 ' + (i.url || '');
    if (b.type === 'tool_use' && b.name === 'guardar_archivo') return '💾 ' + i.nombre;
    if (b.type === 'tool_use' && b.name === 'leer_archivo') return '📖 ' + i.nombre;
    return null;
  }

  async function runSub(j, key, tarea) {
    const spec = SUB[key];
    setAgent(j, key, 'trabajando', tarea); ev(j, key, 'inicio', tarea);
    try {
      const ft = fileTools(j, key !== 'revisa');
      const r = await Claude.run({ system: spec.system + '\n\nEncargo original del usuario (contexto): ' + j.encargo, effort: 'medium', maxTurns: 20,
        tools: ft.tools.concat(spec.web ? Claude.WEB_TOOLS : []), handlers: ft.handlers, messages: [{ role: 'user', content: tarea }],
        onStep: (m) => { usage(j, m); for (const b of m.content || []) { const d = describe(b); if (d) ev(j, key, 'accion', d); } } });
      const out = r.text || 'Hecho.';
      ev(j, key, 'resultado', out); setAgent(j, key, 'hecho');
      return out;
    } catch (e) {
      ev(j, key, 'error', e.message); setAgent(j, key, 'error');
      return 'ERROR de ' + spec.nombre + ': ' + e.message;
    }
  }

  async function runJob(j) {
    active.add(j.id);
    let delivered = null;
    const ft = fileTools(j, false);
    const tools = [
      { name: 'delegar', description: 'Encarga tareas a los subagentes. Las de la lista se ejecutan EN PARALELO; si una depende de otra, delégala después. Devuelve el resultado de cada uno.',
        input_schema: { type: 'object', required: ['tareas'], properties: { tareas: { type: 'array', items: { type: 'object', required: ['subagente', 'tarea'],
          properties: { subagente: { type: 'string', enum: ['busca', 'escribe', 'disena', 'revisa'] }, tarea: { type: 'string', description: 'autosuficiente: objetivo, contexto, formato y nombres de archivos' } } } } } } },
      { name: 'entregar', description: 'Entrega el trabajo terminado. Solo cuando Revisa lo haya aprobado (o tras 2 rondas).',
        input_schema: { type: 'object', required: ['resumen', 'archivos'], properties: { resumen: { type: 'string', description: 'máx. 8 líneas' }, archivos: { type: 'array', items: { type: 'string' } } } } },
      ...ft.tools,
    ];
    const handlers = Object.assign({}, ft.handlers, {
      delegar: async (i) => {
        const tareas = (i.tareas || []).filter((t) => SUB[t.subagente]).slice(0, 6);
        tareas.forEach((t) => ev(j, 'jefe', 'delega', `→ ${SUB[t.subagente].nombre}: ${t.tarea}`));
        const res = await Promise.all(tareas.map((t) => runSub(j, t.subagente, t.tarea)));
        return tareas.map((t, k) => `## ${SUB[t.subagente].nombre}\n${res[k]}`).join('\n\n');
      },
      entregar: (i) => {
        const files = (i.archivos || []).filter((f) => f in j.archivos);
        delivered = { resumen: i.resumen, archivos: files.length ? files : Object.keys(j.archivos).sort() };
        ev(j, 'jefe', 'entrega', i.resumen); return 'Entregado. Termina aquí con una frase.';
      },
    });
    setAgent(j, 'jefe', 'trabajando', 'Planificando el encargo'); ev(j, 'jefe', 'inicio', j.encargo);
    try {
      await Claude.run({ system: JEFE, effort: 'high', maxTurns: 18, tools, handlers, messages: [{ role: 'user', content: j.encargo }],
        onStep: (m) => { usage(j, m); const t = Claude.textOf(m); if (t) ev(j, 'jefe', 'mensaje', t); } });
      setAgent(j, 'jefe', 'hecho');
      Object.assign(j, { estado: 'hecho', fin: new Date().toISOString(),
        resumen: delivered ? delivered.resumen : 'El equipo terminó sin una entrega formal. Revisa los archivos.',
        entregables: delivered ? delivered.archivos : Object.keys(j.archivos).sort() });
    } catch (e) {
      ev(j, 'jefe', 'error', e.message); setAgent(j, 'jefe', 'error');
      Object.assign(j, { estado: 'error', error: e.message, fin: new Date().toISOString(), entregables: Object.keys(j.archivos).sort() });
    } finally {
      for (const a of Object.values(j.agentes)) if (a.estado === 'trabajando') a.estado = 'libre';
      save(); active.delete(j.id);
    }
  }

  async function handle(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const [route, query] = path.replace(/^api\//, '').split('?');
    const p = route.split('/');
    if (p[0] === 'trabajos' && !p[1] && method === 'POST') {
      const enc = String(JSON.parse(opts.body).encargo || '').trim();
      if (enc.length < 5) throw new Error('Describe un poco más el encargo');
      if (active.size >= 1) throw new Error('El equipo ya está con un trabajo; espera a que termine');
      const j = newJob(enc); runJob(j); return { id: j.id };
    }
    if (p[0] === 'trabajos' && !p[1]) return Object.values(JOBS).sort((a, b) => b.id.localeCompare(a.id)).map((j) => ({ id: j.id, encargo: j.encargo, estado: j.estado, creado: j.creado }));
    if (p[0] === 'trabajos' && p[1] && !p[2]) {
      const j = JOBS[p[1]]; if (!j) throw new Error('No existe');
      const desde = +(new URLSearchParams(query || '').get('desde') || 0);
      return Object.assign({}, j, { total_eventos: j.eventos.length, eventos: j.eventos.slice(desde), archivos: Object.keys(j.archivos).sort() });
    }
    if (p[0] === 'trabajos' && p[2] === 'archivos') {
      const j = JOBS[p[1]], n = decodeURIComponent(p.slice(3).join('/'));
      if (!j || !(n in j.archivos)) throw new Error('No existe');
      return j.archivos[n];
    }
    throw new Error('Ruta desconocida: ' + path);
  }
  window.EquipoLocal = { handle };
})();
