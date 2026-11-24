/* Agente de contenido — versión móvil. Investiga, mira noticias y escribe guiones desde el teléfono.
 * Reproduce la API del servidor (contenido/server.py + pipeline.py). */
(function () {
  const { Store } = window.Movil;
  const DEFAULT_CFG = {
    nicho: 'inteligencia artificial para emprendedores', competidores: '', plataforma: 'TikTok e Instagram Reels',
    idioma: 'español latinoamericano', pais: 'PE', num_guiones: 3, auto: false,
    marca: 'Tono cercano, directo y con energía. Tuteo. Frases cortas, ejemplos reales de negocios pequeños. ' +
      'Gancho en los 2 primeros segundos, una sola idea por vídeo y llamada a la acción clara. Nunca prometer dinero fácil ni inventar datos.',
  };
  const cfg = () => Object.assign({}, DEFAULT_CFG, Store.load('contenido-config', {}));
  let NIGHTS = Store.load('contenido-noches', {});
  const saveNights = () => {
    const days = Object.keys(NIGHTS).sort().reverse();
    for (const d of days.slice(20)) delete NIGHTS[d];   // guarda las últimas 20
    Store.save('contenido-noches', NIGHTS);
  };
  let running = false;
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };

  // Una ejecución que quedó a medias (se cerró la app) se marca como interrumpida
  for (const n of Object.values(NIGHTS)) if (n.estado && n.estado.estado === 'trabajando') {
    n.estado.estado = 'error'; n.estado.error = 'Se interrumpió (se cerró la app mientras trabajaba)';
    for (const s of n.estado.pasos) if (s.estado === 'trabajando' || s.estado === 'pendiente') { s.estado = 'error'; s.detalle = 'Interrumpido'; }
  }
  saveNights();

  const STEPS = [
    { id: 'competencia', titulo: 'Investiga a la competencia', icono: 'search' },
    { id: 'noticias', titulo: 'Mira las noticias del día', icono: 'news' },
    { id: 'guiones', titulo: 'Escribe los guiones', icono: 'doc' },
  ];
  const SCHEMA = { type: 'object', additionalProperties: false, required: ['guiones'], properties: { guiones: { type: 'array', items: {
    type: 'object', additionalProperties: false,
    required: ['titulo', 'formato', 'duracion_seg', 'gancho', 'guion', 'cta', 'texto_pantalla', 'descripcion', 'por_que_funciona', 'fuentes'],
    properties: { titulo: { type: 'string' }, formato: { type: 'string' }, duracion_seg: { type: 'integer' }, gancho: { type: 'string' },
      guion: { type: 'string', description: 'texto para leer a cámara, con [indicaciones visuales] entre corchetes' }, cta: { type: 'string' },
      texto_pantalla: { type: 'string' }, descripcion: { type: 'string', description: 'copy con hashtags' }, por_que_funciona: { type: 'string' },
      fuentes: { type: 'array', items: { type: 'string' } } } } } } };

  function newNight() {
    const day = today();
    NIGHTS[day] = { dia: day, competencia: null, noticias: null, guiones: null,
      estado: { dia: day, inicio: new Date().toISOString(), fin: null, estado: 'trabajando',
        pasos: STEPS.map((s) => Object.assign({}, s, { progreso: 0, estado: 'pendiente', detalle: '', busquedas: 0 })) } };
    saveNights(); return NIGHTS[day];
  }
  const step = (n, id) => n.estado.pasos.find((s) => s.id === id);
  function upd(n, id, kw) { Object.assign(step(n, id), kw); saveNights(); }

  async function research(n, id, system, prompt, expected) {
    upd(n, id, { estado: 'trabajando', progreso: 0.05, detalle: 'Pensando por dónde empezar…' });
    let uses = 0; const t0 = Date.now();
    const tick = setInterval(() => { const s = step(n, id); if (s.estado === 'trabajando') upd(n, id, { progreso: Math.min(0.9, s.progreso + 0.01) }); }, 3000);
    try {
      const r = await Claude.run({ system, effort: 'high', tools: Claude.WEB_TOOLS, maxTurns: 12,
        messages: [{ role: 'user', content: prompt }],
        onStep: (m) => {
          for (const b of m.content || []) if (b.type === 'server_tool_use') {
            uses++; const q = (b.input && (b.input.query || b.input.url)) || '';
            upd(n, id, { busquedas: uses, detalle: ((b.name === 'web_search' ? 'Buscando: ' : 'Leyendo: ') + q).slice(0, 140),
              progreso: Math.min(0.9, Math.max(step(n, id).progreso, 0.05 + 0.85 * uses / expected)) });
          }
        } });
      n[id] = r.text;
      upd(n, id, { estado: 'hecho', progreso: 1, detalle: `Listo en ${Math.round((Date.now() - t0) / 1000)} s` });
      return r.text;
    } finally { clearInterval(tick); }
  }

  async function runNight() {
    if (running) throw new Error('Ya está trabajando');
    running = true;
    const c = cfg(), n = newNight();
    const comp = c.competidores.trim() || '(no hay lista: encuentra tú los 5 creadores más relevantes del nicho)';
    try {
      const results = await Promise.allSettled([
        research(n, 'competencia', 'Eres analista de contenido para redes sociales. Investigas con búsquedas web reales y nunca inventas datos: si algo no lo encuentras, dilo.',
          `Nicho: ${c.nicho}. Plataforma: ${c.plataforma}. Competidores: ${comp}.\n\nInvestiga qué están publicando estos creadores/marcas últimamente. ` +
          'Devuélveme un informe en Markdown con:\n## Qué están publicando\n## Lo que mejor les funciona\n## Huecos y oportunidades\n## Fuentes\nSé concreto: máximo ~500 palabras.', 10),
        research(n, 'noticias', 'Eres editor de actualidad. Solo das noticias verificadas con búsqueda web, con fecha y enlace.',
          `Hoy es ${new Date().toLocaleDateString('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}. Busca las noticias más importantes ` +
          `de las últimas 24-48 horas sobre: ${c.nicho}. Prioriza lo que interesaría a la audiencia de ${c.plataforma} (país: ${c.pais}).\n\n` +
          'Devuélveme en Markdown las 5-8 mejores, cada una así:\n### Titular\n- **Qué ha pasado:** 2 frases\n- **Por qué importa:** 1 frase\n- **Ángulo para un vídeo:** 1 frase\n- **Fuente:** enlace (fecha)', 8),
      ]);
      results.forEach((r, i) => { if (r.status === 'rejected') upd(n, STEPS[i].id, { estado: 'error', detalle: r.reason.message.slice(0, 200) }); });
      if (results.every((r) => r.status === 'rejected')) throw results[0].reason;

      const t0 = Date.now();
      upd(n, 'guiones', { estado: 'trabajando', progreso: 0.1, detalle: `Escribiendo ${c.num_guiones} guiones…` });
      const tick = setInterval(() => { const s = step(n, 'guiones'); if (s.estado === 'trabajando') upd(n, 'guiones', { progreso: Math.min(0.92, s.progreso + 0.02) }); }, 2000);
      try {
        const r = await Claude.run({ effort: 'high', format: { type: 'json_schema', schema: SCHEMA }, max_tokens: 16000,
          system: `Eres guionista de vídeos cortos virales para ${c.plataforma}, en ${c.idioma}. Escribes como habla una persona, frases cortas, sin relleno, ` +
            'con un gancho brutal en los primeros 2 segundos. Nada de clickbait falso: todo dato debe venir de la investigación.\n\n<marca>\n' + c.marca + '\n</marca>',
          messages: [{ role: 'user', content: `Escribe ${c.num_guiones} guiones distintos (al menos uno basado en una noticia y otro en un hueco de la competencia).\n\n` +
            `<competencia>\n${n.competencia || '(sin datos)'}\n</competencia>\n\n<noticias>\n${n.noticias || '(sin datos)'}\n</noticias>` }] });
        n.guiones = Claude.parseJSON(r.text).guiones;
        if (!Array.isArray(n.guiones) || !n.guiones.length) throw new Error('La IA no devolvió guiones. Inténtalo otra vez.');
      } finally { clearInterval(tick); }
      upd(n, 'guiones', { estado: 'hecho', progreso: 1, detalle: `${n.guiones.length} guiones en ${Math.round((Date.now() - t0) / 1000)} s` });
      n.estado.estado = 'hecho';
    } catch (e) {
      n.estado.estado = 'error'; n.estado.error = e.message;
      for (const s of n.estado.pasos) if (s.estado !== 'hecho' && s.estado !== 'error') { s.estado = 'error'; s.detalle = e.message.slice(0, 200); }
    } finally {
      n.estado.fin = new Date().toISOString(); saveNights(); running = false;
    }
  }

  async function handle(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const p = path.replace(/^api\//, '').split('/');
    if (p[0] === 'info') {
      const c = cfg();
      return { nicho: c.nicho, plataforma: c.plataforma, competidores: c.competidores.split(',').map((x) => x.trim()).filter(Boolean),
        num_guiones: c.num_guiones, proxima: null, trabajando: running, noches: Object.keys(NIGHTS).sort().reverse(), auto: c.auto };
    }
    if (p[0] === 'noche') { const n = NIGHTS[p[1]]; if (!n) throw new Error('No existe'); return n; }
    if (p[0] === 'ejecutar' && method === 'POST') { if (running) throw new Error('Ya está trabajando'); runNight(); return { ok: true }; }
    if (p[0] === 'config' && method === 'GET') return cfg();
    if (p[0] === 'config' && method === 'POST') {
      const b = JSON.parse(opts.body); b.num_guiones = Math.max(1, Math.min(6, parseInt(b.num_guiones, 10) || 3)); b.auto = !!b.auto;
      Store.save('contenido-config', Object.assign(cfg(), b)); return { ok: true };
    }
    throw new Error('Ruta desconocida: ' + path);
  }
  window.ContenidoLocal = { handle, autoStart: () => cfg().auto && !NIGHTS[today()] && Claude.hasKey() };
})();
