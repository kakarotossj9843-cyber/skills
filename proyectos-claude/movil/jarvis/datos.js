/* Jarvis de bolsillo — versión móvil: agenda, tareas, memoria, internet y mensajes listos para enviar.
 * Todo se guarda en el teléfono. */
(function () {
  const { Store } = window.Movil;
  let J = Store.load('jarvis-datos', null) || { eventos: [], tareas: [], memoria: [], chat: [], next: 1 };
  const save = () => { J.chat = J.chat.slice(-40); Store.save('jarvis-datos', J); };
  const pad = (n) => String(n).padStart(2, '0');
  const isoDay = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const nowText = () => new Date().toLocaleString('es-PE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  let acciones = [];   // botones (WhatsApp, correo, llamar) que Jarvis deja preparados en su respuesta

  function eventosEntre(desde, dias) {
    const a = isoDay(desde), b = isoDay(new Date(desde.getTime() + dias * 864e5));
    return J.eventos.filter((e) => e.inicio.slice(0, 10) >= a && e.inicio.slice(0, 10) < b).sort((x, y) => x.inicio.localeCompare(y.inicio));
  }
  const telefono = (t) => String(t || '').replace(/[^\d]/g, '');

  const TOOLS = [
    { name: 'ver_agenda', description: 'Lista los eventos de la agenda desde hoy hasta dentro de N días.',
      input_schema: { type: 'object', properties: { dias: { type: 'integer', description: '1 = hoy, 7 = semana' } } } },
    { name: 'crear_evento', description: 'Crea un evento en la agenda del teléfono.',
      input_schema: { type: 'object', required: ['titulo', 'inicio'], properties: { titulo: { type: 'string' }, inicio: { type: 'string', description: 'AAAA-MM-DDTHH:MM (hora local)' },
        fin: { type: 'string', description: 'AAAA-MM-DDTHH:MM, opcional' }, lugar: { type: 'string' }, notas: { type: 'string' } } } },
    { name: 'borrar_evento', description: 'Borra un evento por su id. Confirma con el usuario antes.', input_schema: { type: 'object', required: ['id'], properties: { id: { type: 'integer' } } } },
    { name: 'ver_tareas', description: 'Lista las tareas pendientes y las hechas hoy.', input_schema: { type: 'object', properties: {} } },
    { name: 'anadir_tarea', description: 'Añade una tarea pendiente.', input_schema: { type: 'object', required: ['titulo'], properties: { titulo: { type: 'string' }, para: { type: 'string', description: 'fecha límite AAAA-MM-DD, opcional' } } } },
    { name: 'completar_tarea', description: 'Marca una tarea como hecha por su id.', input_schema: { type: 'object', required: ['id'], properties: { id: { type: 'integer' } } } },
    { name: 'recordar', description: 'Guarda en la memoria permanente un dato importante del usuario (personas, teléfonos, preferencias, rutinas).',
      input_schema: { type: 'object', required: ['dato'], properties: { dato: { type: 'string' } } } },
    { name: 'preparar_whatsapp', description: 'Deja listo un mensaje de WhatsApp para que el usuario lo envíe con un toque (no se envía solo).',
      input_schema: { type: 'object', required: ['mensaje'], properties: { telefono: { type: 'string', description: 'con código de país, p. ej. 51987654321. Vacío = elegir contacto' }, mensaje: { type: 'string' } } } },
    { name: 'preparar_correo', description: 'Deja listo un correo para que el usuario lo revise y envíe desde su app de correo.',
      input_schema: { type: 'object', required: ['asunto', 'cuerpo'], properties: { para: { type: 'string' }, asunto: { type: 'string' }, cuerpo: { type: 'string' } } } },
    { name: 'preparar_llamada', description: 'Deja listo un botón para llamar a un número.', input_schema: { type: 'object', required: ['telefono'], properties: { telefono: { type: 'string' }, nombre: { type: 'string' } } } },
    ...Claude.WEB_TOOLS,
  ];
  const HANDLERS = {
    ver_agenda: (i) => eventosEntre(new Date(), Math.max(1, Math.min(31, i.dias || 1))),
    crear_evento: (i) => {
      if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(i.inicio)) throw new Error('inicio debe ser AAAA-MM-DDTHH:MM');
      const e = { id: J.next++, titulo: i.titulo, inicio: i.inicio.slice(0, 16), fin: (i.fin || '').slice(0, 16), lugar: i.lugar || '', notas: i.notas || '' };
      J.eventos.push(e); save(); return 'Evento creado: ' + JSON.stringify(e);
    },
    borrar_evento: (i) => { const n = J.eventos.length; J.eventos = J.eventos.filter((e) => e.id !== i.id); save(); return n === J.eventos.length ? 'No existe ese evento' : 'Evento borrado'; },
    ver_tareas: () => { const hoy = isoDay(new Date()); return J.tareas.filter((t) => !t.hecha || t.hecha >= hoy); },
    anadir_tarea: (i) => { const t = { id: J.next++, titulo: i.titulo, para: i.para || '', hecha: null }; J.tareas.push(t); save(); return 'Tarea añadida: ' + JSON.stringify(t); },
    completar_tarea: (i) => { const t = J.tareas.find((x) => x.id === i.id); if (!t) return 'No existe esa tarea'; t.hecha = isoDay(new Date()); save(); return 'Tarea completada: ' + t.titulo; },
    recordar: (i) => { J.memoria.push({ fecha: isoDay(new Date()), dato: i.dato }); save(); return 'Guardado en memoria'; },
    preparar_whatsapp: (i) => {
      const tel = telefono(i.telefono);
      acciones.push({ icono: '💬', texto: 'Enviar WhatsApp' + (tel ? ' a +' + tel : ''), url: `https://wa.me/${tel}?text=${encodeURIComponent(i.mensaje)}` });
      return 'Botón de WhatsApp preparado. Dile al usuario que lo pulse para enviarlo.';
    },
    preparar_correo: (i) => {
      acciones.push({ icono: '✉️', texto: 'Abrir correo' + (i.para ? ' para ' + i.para : ''), url: `mailto:${encodeURIComponent(i.para || '')}?subject=${encodeURIComponent(i.asunto)}&body=${encodeURIComponent(i.cuerpo)}` });
      return 'Botón de correo preparado.';
    },
    preparar_llamada: (i) => { acciones.push({ icono: '📞', texto: 'Llamar' + (i.nombre ? ' a ' + i.nombre : ''), url: 'tel:+' + telefono(i.telefono) }); return 'Botón de llamada preparado.'; },
  };

  const SYSTEM = `Eres Jarvis, el asistente personal del usuario, en su teléfono. Le resuelves el día a día: agenda, tareas, memoria, búsquedas en internet y mensajes listos para enviar.

Cómo trabajas:
- Responde en español, breve y directo, como un buen asistente ejecutivo: frases cortas y listas con guiones, sin tablas.
- Usa las herramientas para consultar la agenda y las tareas reales en vez de suponer. Para datos actuales (noticias, precios, horarios, clima…) busca en internet y cita la fuente.
- Para enviar mensajes, usa preparar_whatsapp / preparar_correo / preparar_llamada: el usuario confirma con un toque. Nunca digas que ya lo enviaste.
- Antes de borrar algo, pide confirmación.
- Cuando el usuario cuente algo útil para el futuro (personas, teléfonos, preferencias, rutinas), guárdalo con recordar.
- Sé proactivo: si ves choques en la agenda o tareas atrasadas, avísalo.`;

  function contexto() {
    const mem = J.memoria.slice(-60).map((m) => `- [${m.fecha}] ${m.dato}`).join('\n');
    return `Fecha y hora actual: ${nowText()}.` + (mem ? `\nLo que recuerdas del usuario:\n${mem}` : '');
  }

  async function ask(text) {
    acciones = [];
    const hist = J.chat.slice(-16).map((m) => ({ role: m.role, content: m.content }));
    while (hist.length && hist[0].role !== 'user') hist.shift();
    const r = await Claude.run({ system: SYSTEM, tools: TOOLS, handlers: HANDLERS, effort: 'medium', maxTurns: 20,
      messages: [...hist, { role: 'user', content: `<contexto>${contexto()}</contexto>\n\n${text}` }] });
    const reply = r.text || 'Hecho.';
    J.chat.push({ role: 'user', content: text }, { role: 'assistant', content: reply }); save();
    return { reply, acciones };
  }
  const brief = () => ask('Prepárame el resumen del día: 1) mi agenda de hoy y mañana, 2) tareas pendientes y atrasadas, 3) qué debería priorizar hoy. Máximo 12 líneas.');

  async function handle(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const body = opts.body ? JSON.parse(opts.body) : {};
    const p = path.replace(/^api\//, '').split('/');
    if (p[0] === 'chat') return ask(body.message);
    if (p[0] === 'brief') return brief();
    if (p[0] === 'datos') return { eventos: eventosEntre(new Date(), 31), tareas: HANDLERS.ver_tareas(), memoria: J.memoria.slice().reverse(), chat: J.chat.slice(-12) };
    if (p[0] === 'evento' && method === 'POST') return { r: HANDLERS.crear_evento(body) };
    if (p[0] === 'evento' && method === 'DELETE') return { r: HANDLERS.borrar_evento({ id: +p[1] }) };
    if (p[0] === 'tarea' && method === 'POST' && !p[1]) return { r: HANDLERS.anadir_tarea(body) };
    if (p[0] === 'tarea' && method === 'POST') { const t = J.tareas.find((x) => x.id === +p[1]); if (t) t.hecha = body.hecha ? isoDay(new Date()) : null; save(); return { ok: true }; }
    if (p[0] === 'tarea' && method === 'DELETE') { J.tareas = J.tareas.filter((x) => x.id !== +p[1]); save(); return { ok: true }; }
    if (p[0] === 'memoria' && method === 'DELETE') { J.memoria.splice(J.memoria.length - 1 - (+p[1]), 1); save(); return { ok: true }; }
    if (p[0] === 'olvidar-chat') { J.chat = []; save(); return { ok: true }; }
    if (p[0] === 'copia' && method === 'GET') return J;
    if (p[0] === 'copia' && method === 'POST') { if (!body || !Array.isArray(body.eventos)) throw new Error('Ese archivo no es una copia de Jarvis'); J = body; save(); return { ok: true }; }
    throw new Error('Ruta desconocida: ' + path);
  }
  window.JarvisLocal = { handle };
})();
