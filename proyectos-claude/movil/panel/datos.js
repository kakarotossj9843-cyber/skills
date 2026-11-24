/* Panel de tu vida — versión móvil: todos los datos viven en el teléfono (localStorage).
 * Reproduce la API del servidor (panel/server.py + db.py) para que la interfaz sea la misma. */
(function () {
  const { Store } = window.Movil;
  const CURRENCIES = { PEN: 'S/', USD: '$', BOB: 'Bs', EUR: '€' };
  const DEFAULT_RATES = { USD: 1, PEN: 3.75, BOB: 6.96, EUR: 0.92 };
  const DEFAULTS = { sales_goal_month: '50000', savings_goal_month: '10000', base_currency: 'PEN',
    rates: JSON.stringify(DEFAULT_RATES), rates_updated: '' };

  let D = Store.load('panel-datos', null);
  if (!D) D = { sales: [], clients: [], habits: [], habitLog: {}, tasks: [], money: [], settings: {}, next: 1 };
  const save = () => Store.save('panel-datos', D);
  const nid = () => D.next++;

  // ---------- fechas (hora local del teléfono) ----------
  const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  const today = () => { const d = new Date(); d.setHours(12, 0, 0, 0); return d; };
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const monthStart = (d) => new Date(d.getFullYear(), d.getMonth(), 1, 12);
  const addMonths = (d, n) => new Date(d.getFullYear(), d.getMonth() + n, 1, 12);

  // ---------- ajustes y monedas ----------
  const settings = () => Object.assign({}, DEFAULTS, D.settings);
  function rates() {
    const r = Object.assign({}, DEFAULT_RATES);
    try { for (const [k, v] of Object.entries(JSON.parse(settings().rates))) if (+v > 0) r[k.toUpperCase()] = +v; } catch (e) { /* tasas por defecto */ }
    return r;
  }
  const ALIAS = { '$': 'USD', 'us$': 'USD', usd: 'USD', dolar: 'USD', 'dólar': 'USD', dolares: 'USD', 'dólares': 'USD',
    's/': 'PEN', pen: 'PEN', sol: 'PEN', soles: 'PEN', bs: 'BOB', bob: 'BOB', boliviano: 'BOB', bolivianos: 'BOB',
    '€': 'EUR', eur: 'EUR', euro: 'EUR', euros: 'EUR' };
  function normCurrency(c) {
    const k = String(c || '').trim().toLowerCase().replace(/\./g, '');
    if (!k) return settings().base_currency;
    return ALIAS[k] || k.toUpperCase().slice(0, 3);
  }
  function setSetting(key, value) {
    if (!(key in DEFAULTS)) throw new Error('ajuste desconocido');
    if (key === 'base_currency') {
      value = normCurrency(value);
      const fx = rates();
      if (!fx[value]) throw new Error('Moneda sin tipo de cambio: ' + value);
      const old = settings().base_currency;
      if (old !== value) for (const g of ['sales_goal_month', 'savings_goal_month'])
        D.settings[g] = String(Math.round(+settings()[g] * fx[value] / (fx[old] || 1)));
    }
    if (key === 'rates') {
      const parsed = {};
      for (const [k, v] of Object.entries(JSON.parse(value))) { if (!(+v > 0)) throw new Error('Los tipos de cambio deben ser positivos'); parsed[k.toUpperCase()] = +v; }
      value = JSON.stringify(parsed);
    }
    D.settings[key] = String(value); save();
  }

  // ---------- escritura ----------
  function addClient(name, since) {
    name = String(name || '').trim(); if (!name) return;
    const c = D.clients.find((x) => x.name.toLowerCase() === name.toLowerCase());
    if (c) c.active = true; else D.clients.push({ name, since: since || iso(today()), active: true });
  }
  function addSale(amount, client = '', concept = '', day, currency, source = 'manual') {
    if (!(+amount > 0)) throw new Error('Importe no válido');
    D.sales.push({ id: nid(), day: day || iso(today()), amount: +amount, client: String(client || '').trim(), concept: String(concept || '').trim(), currency: normCurrency(currency), source });
    if (String(client || '').trim()) addClient(client, day);
    save();
  }
  function addMoney(kind, amount, concept = '', category = '', day, currency) {
    if (!['ingreso', 'gasto'].includes(kind)) throw new Error("tipo debe ser 'ingreso' o 'gasto'");
    D.money.push({ id: nid(), day: day || iso(today()), kind, amount: Math.abs(+amount), concept, category, currency: normCurrency(currency) });
    save();
  }
  function habitByName(name) {
    const n = String(name).trim().toLowerCase();
    return D.habits.find((h) => h.active && h.name.toLowerCase().includes(n));
  }
  function addHabit(name) {
    name = String(name).trim();
    const h = D.habits.find((x) => x.name.toLowerCase() === name.toLowerCase());
    if (h) h.active = true; else D.habits.push({ id: nid(), name, active: true });
    save();
  }
  function setHabit(id, done, day) {
    const k = id + '|' + (day || iso(today()));
    if (done) D.habitLog[k] = 1; else delete D.habitLog[k];
    save();
  }

  // ---------- métricas (equivale a db.dashboard) ----------
  function dashboard() {
    const t = today(), m0 = monthStart(t), s = settings(), base = s.base_currency, fx = rates();
    const conv = (amount, cur) => amount * (fx[base] / (fx[cur || base] || fx[base]));
    const months = []; for (let i = 11; i >= 0; i--) months.push(addMonths(m0, -i));
    const ym = (d) => iso(d).slice(0, 7);
    const sinTasa = [...new Set([...D.sales, ...D.money].map((x) => x.currency).filter((c) => c && !fx[c]))].sort();

    // Ventas
    const salesBy = {};
    for (const x of D.sales) if (x.day >= iso(months[0])) salesBy[x.day.slice(0, 7)] = (salesBy[x.day.slice(0, 7)] || 0) + conv(x.amount, x.currency);
    const salesMonths = months.map((m) => ({ month: ym(m), total: Math.round((salesBy[ym(m)] || 0) * 100) / 100 }));
    const cur = salesMonths[11].total, prev = salesMonths[10].total;
    const prevEnd = iso(addDays(months[10], t.getDate() - 1));
    const prevSame = D.sales.filter((x) => x.day >= iso(months[10]) && x.day <= prevEnd).reduce((a, x) => a + conv(x.amount, x.currency), 0);
    const porMonedaMap = {};
    for (const x of D.sales) if (x.day >= iso(m0)) { const c = x.currency || base; porMonedaMap[c] = porMonedaMap[c] || { currency: c, total: 0, n: 0 }; porMonedaMap[c].total += x.amount; porMonedaMap[c].n++; }
    const byRecent = (a, b) => (b.day.localeCompare(a.day)) || (b.id - a.id);
    const recentSales = D.sales.slice().sort(byRecent).slice(0, 8);

    // Hábitos
    const habits = D.habits.filter((h) => h.active).map((h) => ({ id: h.id, name: h.name }));
    const start = addDays(t, -83), todayIso = iso(t), doneByDay = {};
    for (const k of Object.keys(D.habitLog)) { const day = k.split('|')[1]; if (day >= iso(start)) doneByDay[day] = (doneByDay[day] || 0) + 1; }
    let hechos = 0;
    for (const h of habits) {
      h.done = !!D.habitLog[h.id + '|' + todayIso]; if (h.done) hechos++;
      let streak = 0, d = h.done ? t : addDays(t, -1);
      while (D.habitLog[h.id + '|' + iso(d)]) { streak++; d = addDays(d, -1); }
      h.streak = streak;
    }
    const heat = []; for (let i = 0; i < 84; i++) { const day = iso(addDays(start, i)); heat.push({ day, done: doneByDay[day] || 0 }); }

    // Tareas
    const tasks = D.tasks.filter((x) => !x.done_at || x.done_at >= todayIso)
      .sort((a, b) => (!!a.done_at - !!b.done_at) || (b.id - a.id)).map((x) => ({ id: x.id, title: x.title, done_at: x.done_at }));
    const weekAgo = iso(addDays(t, -6));
    const doneWeek = D.tasks.filter((x) => x.done_at && x.done_at >= weekAgo).length;

    // Negocio
    const active = D.clients.filter((c) => c.active);
    let acc = active.filter((c) => c.since < iso(months[0])).length;
    const newBy = {}; for (const c of active) if (c.since >= iso(months[0])) newBy[c.since.slice(0, 7)] = (newBy[c.since.slice(0, 7)] || 0) + 1;
    const serie = months.map((m) => (acc += newBy[ym(m)] || 0));
    const d90 = iso(addDays(t, -90));
    const last90 = D.sales.filter((x) => x.day >= d90);
    const ticket = last90.length ? last90.reduce((a, x) => a + conv(x.amount, x.currency), 0) / last90.length : 0;
    const topMap = {}; for (const x of last90) if (x.client) topMap[x.client] = (topMap[x.client] || 0) + conv(x.amount, x.currency);
    const top = Object.entries(topMap).map(([client, total]) => ({ client, total })).sort((a, b) => b.total - a.total).slice(0, 5);

    // Dinero
    const mm = {};
    for (const x of D.money) if (x.day >= iso(months[0])) { const k = x.day.slice(0, 7); mm[k] = mm[k] || { ingreso: 0, gasto: 0 }; mm[k][x.kind] += conv(x.amount, x.currency); }
    let cum = 0;
    const moneyMonths = months.map((m) => { const v = mm[ym(m)] || { ingreso: 0, gasto: 0 }; return { month: ym(m), ingresos: r2(v.ingreso), gastos: r2(v.gasto), ahorro: r2(v.ingreso - v.gasto) }; });
    const acumulado = moneyMonths.map((x) => r2(cum += x.ahorro));
    const catMap = {}; for (const x of D.money) if (x.kind === 'gasto' && x.day >= iso(m0)) { const c = x.category || 'Otros'; catMap[c] = (catMap[c] || 0) + conv(x.amount, x.currency); }
    const gastosTop = Object.entries(catMap).map(([category, total]) => ({ category, total })).sort((a, b) => b.total - a.total).slice(0, 5);
    const recentMoney = D.money.slice().sort(byRecent).slice(0, 8);

    return {
      today: todayIso, settings: s,
      monedas: { base, simbolos: CURRENCIES, tasas: fx, sin_tasa: sinTasa, actualizado: s.rates_updated || '' },
      ventas: { mes: r2(cur), mes_anterior: r2(prev), pct_vs_mismo_punto: prevSame ? Math.round((cur - prevSame) / prevSame * 1000) / 10 : null,
        objetivo: +s.sales_goal_month, meses: salesMonths, recientes: recentSales,
        por_moneda: Object.values(porMonedaMap).sort((a, b) => b.total - a.total) },
      habitos: { lista: habits, hechos_hoy: hechos, total: habits.length, calor: heat },
      tareas: { lista: tasks, pendientes: tasks.filter((x) => !x.done_at).length, hechas_semana: doneWeek },
      negocio: { clientes_activos: active.length, nuevos_mes: newBy[ym(m0)] || 0, serie_activos: serie, meses: months.map(ym),
        ticket_medio: r2(ticket), top_clientes: top },
      dinero: { ahorro_mes: moneyMonths[11].ahorro, objetivo_ahorro: +s.savings_goal_month, meses: moneyMonths, acumulado,
        gastos_top: gastosTop, recientes: recentMoney },
      vacio: !D.sales.length && !D.money.length && !D.habits.length && !D.tasks.length,
    };
  }
  const r2 = (n) => Math.round(n * 100) / 100;

  // ---------- CSV ----------
  const COLS = { day: ['fecha', 'date', 'dia', 'día', 'created', 'fecha operacion', 'fecha operación', 'fecha valor'],
    amount: ['importe', 'amount', 'cantidad', 'total', 'precio', 'valor', 'net', 'monto'],
    client: ['cliente', 'client', 'customer', 'nombre', 'name', 'customer email'],
    concept: ['concepto', 'concept', 'descripcion', 'descripción', 'description', 'detalle', 'producto'],
    category: ['categoria', 'categoría', 'category'], currency: ['moneda', 'currency', 'divisa'] };
  function parseCsv(text) {
    const first = text.split(/\r?\n/)[0] || '';
    const delim = [';', '\t', ','].sort((a, b) => first.split(b).length - first.split(a).length)[0];
    const rows = []; let row = [], f = '', q = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (q) { if (ch === '"' && text[i + 1] === '"') { f += '"'; i++; } else if (ch === '"') q = false; else f += ch; }
      else if (ch === '"') q = true;
      else if (ch === delim) { row.push(f); f = ''; }
      else if (ch === '\n' || ch === '\r') { if (ch === '\r' && text[i + 1] === '\n') i++; row.push(f); rows.push(row); row = []; f = ''; }
      else f += ch;
    }
    if (f || row.length) { row.push(f); rows.push(row); }
    return rows.filter((r) => r.some((c) => c.trim()));
  }
  function num(s) {
    s = String(s).trim().replace(/[^\d,.\-]/g, '');
    if (s.includes(',') && s.includes('.')) s = s.lastIndexOf(',') > s.lastIndexOf('.') ? s.replace(/\./g, '').replace(',', '.') : s.replace(/,/g, '');
    else if (s.includes(',')) s = s.replace(',', '.');
    const n = parseFloat(s); if (isNaN(n)) throw new Error('importe'); return n;
  }
  function date(s) {
    s = String(s).trim();
    let m;
    if ((m = s.match(/^(\d{4})[-/](\d{1,2})[-/](\d{1,2})/))) return `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`;
    if ((m = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})/))) { const y = m[3].length === 2 ? '20' + m[3] : m[3]; return `${y}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`; }
    throw new Error('fecha');
  }
  function importCsv(text, kind, currency) {
    const rows = parseCsv(text.replace(/^﻿/, ''));
    if (rows.length < 2) throw new Error('El archivo está vacío');
    const head = rows[0].map((h) => h.trim().toLowerCase());
    const col = {}; for (const [k, names] of Object.entries(COLS)) { const i = head.findIndex((h) => names.includes(h)); col[k] = i >= 0 ? i : null; }
    if (col.day === null || col.amount === null) throw new Error('No encuentro columnas de fecha e importe. Columnas: ' + head.join(', '));
    let ok = 0, errores = 0;
    for (const r of rows.slice(1)) {
      try {
        const day = date(r[col.day]), amount = num(r[col.amount]);
        const g = (k) => (col[k] !== null ? (r[col[k]] || '').trim() : '');
        const cur = g('currency') || currency;
        if (kind === 'ventas') addSale(amount, g('client'), g('concept'), day, cur, 'csv');
        else addMoney(amount < 0 ? 'gasto' : 'ingreso', Math.abs(amount), g('concept'), g('category'), day, cur);
        ok++;
      } catch (e) { errores++; }
    }
    return { importadas: ok, errores };
  }

  async function updateRatesOnline() {
    let r;
    try { r = await fetch('https://open.er-api.com/v6/latest/USD'); } catch (e) { throw new Error('Sin conexión para descargar los tipos de cambio'); }
    const j = await r.json();
    if (j.result !== 'success') throw new Error('El servicio de tipos de cambio no respondió bien');
    const nr = rates(); for (const c of Object.keys(nr)) if (j.rates[c]) nr[c] = +j.rates[c];
    D.settings.rates = JSON.stringify(nr); D.settings.rates_updated = new Date().toISOString().slice(0, 16); save();
    return { tasas: nr };
  }

  // ---------- datos de ejemplo ----------
  function seed() {
    let seedN = 7; const rnd = () => ((seedN = (seedN * 16807) % 2147483647) / 2147483647);
    const pick = (a) => a[Math.floor(rnd() * a.length)];
    D = { sales: [], clients: [], habits: [], habitLog: {}, tasks: [], money: [], settings: {}, next: 1 };
    const t = today(), start = addDays(t, -364);
    const CL = ['Marta López', 'Carlos Ruiz', 'Lucía Gómez', 'Estudio Norte', 'Pablo Díaz', 'Ana Torres', 'Bar La Esquina', 'Clínica Vida',
      'Elena Martín', 'Hugo Sanz', 'Tienda Verde', 'Diego Ortega', 'Gimnasio Fit', 'Academia Uno', 'Rubén Ríos', 'Noelia Soto'];
    CL.forEach((c, i) => D.clients.push({ name: c, since: iso(addDays(start, Math.floor(i * 340 / CL.length))), active: true }));
    for (let d = start; d <= t; d = addDays(d, 1)) {
      const growth = 0.55 + 0.45 * ((d - start) / 864e5) / 364;
      const n = pick([0, 0, 1, 1, 1, 2]);
      for (let k = 0; k < n; k++) {
        const usd = (180 + rnd() * 720) * growth, cur = rnd() < 0.5 ? 'USD' : rnd() < 0.6 ? 'PEN' : 'BOB';
        D.sales.push({ id: nid(), day: iso(d), amount: r2(usd * DEFAULT_RATES[cur]), client: pick(CL.slice(0, Math.max(3, Math.floor(CL.length * growth)))),
          concept: pick(['Web', 'Consultoría', 'Mantenimiento', 'Formación', 'Diseño']), currency: cur, source: 'ejemplo' });
      }
      if (d.getDate() === 1) {
        D.money.push({ id: nid(), day: iso(d), kind: 'ingreso', amount: 2800, concept: 'Sueldo', category: 'Negocio', currency: 'USD' });
        D.money.push({ id: nid(), day: iso(d), kind: 'gasto', amount: 3200, concept: 'Alquiler', category: 'Casa', currency: 'PEN' });
      }
      if (d.getDate() === 15) D.money.push({ id: nid(), day: iso(d), kind: 'ingreso', amount: r2((1500 + rnd() * 3500) * growth), concept: 'Extra proyectos', category: 'Negocio', currency: 'PEN' });
      if (rnd() < 0.5) D.money.push({ id: nid(), day: iso(d), kind: 'gasto', amount: r2(50 + rnd() * 350), concept: pick(['Súper', 'Restaurante', 'Gasolina', 'Cine']), category: pick(['Comida', 'Ocio', 'Transporte']), currency: 'BOB' });
    }
    ['Gimnasio', 'Leer 20 min', 'Dormir 8 h'].forEach((h) => D.habits.push({ id: nid(), name: h, active: true }));
    D.habits.forEach((h, i) => { for (let k = 1; k < 84; k++) if (rnd() < [0.6, 0.75, 0.5][i] + 0.25 * (84 - k) / 84) D.habitLog[h.id + '|' + iso(addDays(t, -k))] = 1; });
    ['Enviar presupuesto', 'Grabar vídeo', 'Llamar a Marta', 'Preparar factura del mes'].forEach((x) => D.tasks.push({ id: nid(), title: x, created: iso(t), done_at: null }));
    D.tasks[0].done_at = iso(t);
    save();
  }

  // ---------- Claude ----------
  const TOOLS = [
    { name: 'registrar_venta', description: 'Registra una venta (ingreso del negocio). Si el cliente es nuevo, se añade a clientes activos.',
      input_schema: { type: 'object', properties: { importe: { type: 'number', description: 'Importe sin símbolo' }, cliente: { type: 'string' }, concepto: { type: 'string' },
        fecha: { type: 'string', description: 'AAAA-MM-DD, vacío = hoy' }, moneda: { type: 'string', description: 'USD (dólares, $), PEN (soles, S/), BOB (bolivianos, Bs), EUR. Vacío = moneda principal' } }, required: ['importe'] } },
    { name: 'registrar_movimiento', description: 'Registra dinero personal: un ingreso o un gasto. Las ventas del negocio van con registrar_venta.',
      input_schema: { type: 'object', properties: { tipo: { type: 'string', enum: ['ingreso', 'gasto'] }, importe: { type: 'number' }, concepto: { type: 'string' },
        categoria: { type: 'string', description: 'Casa, Comida, Ocio, Transporte, Negocio, Suscripciones, Otros…' }, fecha: { type: 'string' }, moneda: { type: 'string' } }, required: ['tipo', 'importe'] } },
    { name: 'marcar_habito', description: 'Marca (o desmarca) un hábito como hecho. Si no existe, lo crea.',
      input_schema: { type: 'object', properties: { nombre: { type: 'string' }, hecho: { type: 'boolean' }, fecha: { type: 'string' } }, required: ['nombre'] } },
    { name: 'anadir_tarea', description: 'Añade una tarea pendiente.', input_schema: { type: 'object', properties: { titulo: { type: 'string' } }, required: ['titulo'] } },
    { name: 'completar_tarea', description: 'Marca como hecha la tarea pendiente que mejor coincida con el texto.', input_schema: { type: 'object', properties: { texto: { type: 'string' } }, required: ['texto'] } },
    { name: 'cambiar_cliente', description: 'Añade un cliente activo o lo da de baja.', input_schema: { type: 'object', properties: { nombre: { type: 'string' }, activo: { type: 'boolean' } }, required: ['nombre', 'activo'] } },
  ];
  const HANDLERS = {
    registrar_venta: (i) => { addSale(i.importe, i.cliente, i.concepto, i.fecha || undefined, i.moneda); return `Venta de ${i.importe} ${normCurrency(i.moneda)} registrada`; },
    registrar_movimiento: (i) => { addMoney(i.tipo, i.importe, i.concepto, i.categoria, i.fecha || undefined, i.moneda); return `${i.tipo} de ${i.importe} ${normCurrency(i.moneda)} registrado`; },
    marcar_habito: (i) => { let h = habitByName(i.nombre); if (!h) { addHabit(i.nombre); h = habitByName(i.nombre); } setHabit(h.id, i.hecho !== false, i.fecha || undefined); return `Hábito '${i.nombre}' actualizado`; },
    anadir_tarea: (i) => { D.tasks.push({ id: nid(), title: String(i.titulo).trim(), created: iso(today()), done_at: null }); save(); return 'Tarea añadida'; },
    completar_tarea: (i) => {
      const words = new Set(String(i.texto).toLowerCase().split(/\s+/));
      const pend = D.tasks.filter((x) => !x.done_at);
      let best = null, score = 0;
      for (const x of pend) { const s = x.title.toLowerCase().split(/\s+/).filter((w) => words.has(w)).length; if (s > score) { best = x; score = s; } }
      if (!best) return 'No encuentro esa tarea. Pendientes: ' + pend.map((x) => x.title).join('; ');
      best.done_at = iso(today()); save(); return 'Tarea completada: ' + best.title;
    },
    cambiar_cliente: (i) => {
      if (i.activo) { addClient(i.nombre); save(); return 'Cliente activo: ' + i.nombre; }
      const c = D.clients.find((x) => x.name.toLowerCase() === String(i.nombre).toLowerCase());
      if (!c) return 'No existe el cliente ' + i.nombre; c.active = false; save(); return 'Cliente dado de baja';
    },
  };
  async function apuntar(text) {
    const s = settings();
    const r = await Claude.run({
      system: 'Eres el asistente del «Panel de tu vida». El usuario te cuenta en lenguaje natural cosas que han pasado (ventas, gastos, hábitos, tareas, clientes). ' +
        'Regístralo TODO con las herramientas, en paralelo si son varias. Hoy es ' + iso(today()) + '. Hábitos actuales: ' + D.habits.filter((h) => h.active).map((h) => h.name).join(', ') +
        '. Moneda principal: ' + s.base_currency + '. Si dice soles o S/ usa PEN; bolivianos o Bs, BOB; dólares o $, USD; euros, EUR. Si no dice moneda, la principal. ' +
        'Después confirma en una o dos frases en español qué has apuntado. Si algo es ambiguo, pregunta en vez de inventar.',
      messages: [{ role: 'user', content: text }], tools: TOOLS, handlers: HANDLERS, effort: 'low', max_tokens: 8000, maxTurns: 8,
    });
    return r.text || 'Apuntado.';
  }
  async function analizar() {
    const d = dashboard(); delete d.ventas.recientes; delete d.dinero.recientes; delete d.habitos.calor;
    const r = await Claude.run({
      system: 'Eres un coach de negocio y vida, directo y concreto. Analiza los datos del panel y responde en español con: 1) Lo mejor (1-2 líneas), ' +
        '2) Lo que preocupa (1-2 líneas), 3) Tres acciones concretas para esta semana. Usa números reales (ya convertidos a la moneda principal de monedas.base). Máximo 12 líneas, sin tablas.',
      messages: [{ role: 'user', content: JSON.stringify(d) }], effort: 'medium', max_tokens: 4000,
    });
    return r.text;
  }

  // ---------- «API» local con las mismas rutas que el servidor ----------
  async function handle(path, opts = {}) {
    const method = (opts.method || 'GET').toUpperCase();
    const body = opts.body && !(opts.body instanceof FormData) ? JSON.parse(opts.body) : opts.body || {};
    const p = path.replace(/^api\//, '').split('?')[0].split('/');
    const ok = { ok: true };
    if (p[0] === 'dashboard') return dashboard();
    if (method === 'POST' && p[0] === 'ventas') { addSale(body.amount, body.client, body.concept, body.day, body.currency); return ok; }
    if (method === 'POST' && p[0] === 'dinero') { addMoney(body.kind, body.amount, body.concept, body.category, body.day, body.currency); return ok; }
    if (p[0] === 'habitos') {
      if (method === 'POST' && !p[1]) { addHabit(body.name); return ok; }
      if (method === 'POST') { setHabit(+p[1], body.done, body.day); return ok; }
      if (method === 'DELETE') { const h = D.habits.find((x) => x.id === +p[1]); if (h) h.active = false; save(); return ok; }
    }
    if (p[0] === 'tareas' && method === 'POST' && !p[1]) { D.tasks.push({ id: nid(), title: String(body.name).trim(), created: iso(today()), done_at: null }); save(); return ok; }
    if (p[0] === 'tareas' && method === 'POST') { const x = D.tasks.find((y) => y.id === +p[1]); if (x) x.done_at = body.done ? iso(today()) : null; save(); return ok; }
    if (method === 'DELETE') {
      const table = { tareas: 'tasks', ventas: 'sales', dinero: 'money' }[p[0]];
      if (table) { D[table] = D[table].filter((x) => x.id !== +p[1]); save(); return ok; }
    }
    if (p[0] === 'clientes') { addClient(body.name); save(); return ok; }
    if (p[0] === 'ajustes') { setSetting(body.key, body.value); return ok; }
    if (p[0] === 'importar') {
      const f = body.get('file'); if (!f || !f.size) throw new Error('Elige un archivo .csv');
      return importCsv(await f.text(), body.get('kind') === 'ventas' ? 'ventas' : 'banco', body.get('currency') || '');
    }
    if (p[0] === 'tipos-de-cambio') return updateRatesOnline();
    if (p[0] === 'claude' && p[1] === 'apuntar') return { reply: await apuntar(body.text) };
    if (p[0] === 'claude' && p[1] === 'analisis') return { reply: await analizar() };
    if (p[0] === 'ejemplo') { seed(); return ok; }
    if (p[0] === 'copia' && method === 'GET') return D;
    if (p[0] === 'copia' && method === 'POST') {
      if (!body || !Array.isArray(body.sales) || !Array.isArray(body.money)) throw new Error('Ese archivo no es una copia del panel');
      D = body; save(); return ok;
    }
    if (p[0] === 'borrar-todo') { D = { sales: [], clients: [], habits: [], habitLog: {}, tasks: [], money: [], settings: {}, next: 1 }; save(); return ok; }
    throw new Error('Ruta desconocida: ' + path);
  }

  window.PanelLocal = { handle };
})();
