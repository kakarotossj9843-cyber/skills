/* Utilidades del móvil: guardar datos, copiar, compartir copias de seguridad y abrir enlaces.
 * Dentro del APK usa el puente nativo `Android`; en un navegador normal, las APIs web. */
(function () {
  const native = window.Android;

  const Store = {
    load(name, fallback) {
      try { const v = localStorage.getItem(name); return v ? JSON.parse(v) : fallback; } catch (e) { return fallback; }
    },
    save(name, value) {
      try { localStorage.setItem(name, JSON.stringify(value)); return true; }
      catch (e) { toast('⚠️ No se pudo guardar (memoria llena)'); return false; }
    },
  };

  function toast(text) {
    let el = document.getElementById('mv-toast');
    if (!el) {
      el = document.createElement('div'); el.id = 'mv-toast';
      el.style.cssText = 'position:fixed;left:50%;bottom:22px;transform:translateX(-50%);z-index:2000;padding:10px 16px;border-radius:12px;' +
        'font:700 14px system-ui,sans-serif;background:var(--cl-accent,#ff7a3d);color:#111;opacity:0;transition:opacity .2s;max-width:90vw;text-align:center';
      document.body.appendChild(el);
    }
    el.textContent = text; el.style.opacity = 1;
    clearTimeout(el._t); el._t = setTimeout(() => (el.style.opacity = 0), 2200);
  }

  async function copy(text) {
    try {
      if (native && native.copy) native.copy(text);
      else await navigator.clipboard.writeText(text);
      toast('Copiado');
    } catch (e) {
      const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); toast('Copiado'); } catch (err) { toast('No se pudo copiar'); }
      ta.remove();
    }
  }

  /** Comparte/guarda un archivo de texto (copia de seguridad): en el APK abre «Compartir» (Drive, WhatsApp, correo…). */
  function shareFile(filename, text) {
    if (native && native.shareFile) { native.shareFile(filename, text); return; }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  }

  /** Pide un archivo al usuario y devuelve su texto. */
  function pickFile(accept) {
    return new Promise((resolve) => {
      const i = document.createElement('input'); i.type = 'file'; i.accept = accept || '*/*';
      i.onchange = () => {
        const f = i.files && i.files[0]; if (!f) return resolve(null);
        const r = new FileReader(); r.onload = () => resolve(String(r.result)); r.onerror = () => resolve(null); r.readAsText(f);
      };
      i.click();
    });
  }

  // Los enlaces externos se abren en el navegador del teléfono
  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('a[href^="http"]');
    if (a && native && native.openUrl) { e.preventDefault(); native.openUrl(a.href); }
  });

  window.Movil = { Store, toast, copy, shareFile, pickFile, isApp: !!native };
})();
