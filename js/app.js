/* ============================================================
   MUNDIAL 2026 — app.js
   ============================================================ */
'use strict';

// ── FLAGS ────────────────────────────────────────────────────
const FLAG_EMOJI = {
  'Argentina':'🇦🇷','Argelia':'🇩🇿','Austria':'🇦🇹','Jordania':'🇯🇴',
  'México':'🇲🇽','Sudáfrica':'🇿🇦','Corea del Sur':'🇰🇷','Rep. Checa':'🇨🇿',
  'Canadá':'🇨🇦','Bosnia y Herz.':'🇧🇦','Qatar':'🇶🇦','Suiza':'🇨🇭',
  'Brasil':'🇧🇷','Marruecos':'🇲🇦','Haití':'🇭🇹','Escocia':'🏴󠁧󠁢󠁳󠁣󠁴󠁿',
  'Estados Unidos':'🇺🇸','Paraguay':'🇵🇾','Australia':'🇦🇺','Turquía':'🇹🇷',
  'Alemania':'🇩🇪','Curazao':'🇨🇼','Costa de Marfil':'🇨🇮','Ecuador':'🇪🇨',
  'Países Bajos':'🇳🇱','Japón':'🇯🇵','Suecia':'🇸🇪','Túnez':'🇹🇳',
  'España':'🇪🇸','Cabo Verde':'🇨🇻','Arabia Saudita':'🇸🇦','Uruguay':'🇺🇾',
  'Irán':'🇮🇷','Nueva Zelanda':'🇳🇿','Bélgica':'🇧🇪','Egipto':'🇪🇬',
  'Francia':'🇫🇷','Senegal':'🇸🇳','Irak':'🇮🇶','Noruega':'🇳🇴',
  'Portugal':'🇵🇹','RD Congo':'🇨🇩','Uzbekistán':'🇺🇿','Colombia':'🇨🇴',
  'Inglaterra':'🏴󠁧󠁢󠁥󠁮󠁧󠁿','Croacia':'🇭🇷','Ghana':'🇬🇭','Panamá':'🇵🇦',
};

function nameToSlug(name) {
  return name.toLowerCase()
    .replace(/\s+/g,'-').replace(/\./g,'')
    .replace(/[áà]/g,'a').replace(/[éè]/g,'e').replace(/[íì]/g,'i')
    .replace(/[óò]/g,'o').replace(/[úù]/g,'u').replace(/ñ/g,'n');
}

function flagImg(team, cls='team-flag') {
  if (!team || team.startsWith('1º') || team.startsWith('2º') ||
      team.startsWith('3º') || team.startsWith('G.') ||
      team.startsWith('Perd.') || team.startsWith('?')) return '';
  const slug  = nameToSlug(team);
  const emoji = FLAG_EMOJI[team] || '';
  return `<img class="${cls}" src="img/flags/${slug}.png" alt="${team}"
    onerror="this.style.display='none';this.nextElementSibling.style.display='inline'"><span
    class="flag-emoji" style="display:none">${emoji}</span>`;
}

const DIAS  = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
const MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul'];

function fmtDate(iso) {
  const d = new Date(iso + 'T12:00:00');
  return `${DIAS[d.getDay()]} ${d.getDate()} ${MESES[d.getMonth()]}`;
}

// ── STATE ────────────────────────────────────────────────────
const DATA = { partidos:[], grupos:{}, eliminatorias:[], resultados:{ partidos:{}, eliminatorias:{}, terceros:{} } };

// Filtros activos
const FILTROS = { fecha: 'all', grupo: 'all', equipo: 'all', fase: 'grupos' };

// ── LOAD ─────────────────────────────────────────────────────
async function loadData() {
  const [partidos, grupos, eliminatorias, resultados] = await Promise.all([
    fetch('json/partidos.json').then(r => r.json()),
    fetch('json/grupos.json').then(r => r.json()),
    fetch('json/eliminatorias.json').then(r => r.json()),
    fetch('json/resultados.json').then(r => r.json()).catch(() => ({ partidos:{}, eliminatorias:{}, terceros:{} })),
  ]);
  DATA.partidos      = partidos;
  DATA.grupos        = grupos;
  DATA.eliminatorias = eliminatorias;
  DATA.resultados    = { partidos:{}, eliminatorias:{}, terceros:{}, ...resultados };
}

// ============================================================
// GRUPO TABLE COMPUTATION
// ============================================================
function computeGroup(letter) {
  const teams = DATA.grupos[letter];
  const res   = DATA.resultados.partidos || {};
  const tbl   = {};
  teams.forEach(t => { tbl[t] = { pj:0, pg:0, pe:0, pp:0, gf:0, gc:0, pts:0 }; });

  DATA.partidos.filter(m => m.group === letter).forEach(m => {
    const sc = res[m.id];
    if (!sc || sc.scoreH == null || sc.scoreA == null) return;
    const h = +sc.scoreH, a = +sc.scoreA;
    tbl[m.home].pj++; tbl[m.home].gf += h; tbl[m.home].gc += a;
    tbl[m.away].pj++; tbl[m.away].gf += a; tbl[m.away].gc += h;
    if      (h > a) { tbl[m.home].pg++; tbl[m.home].pts+=3; tbl[m.away].pp++; }
    else if (h < a) { tbl[m.away].pg++; tbl[m.away].pts+=3; tbl[m.home].pp++; }
    else            { tbl[m.home].pe++; tbl[m.home].pts++;   tbl[m.away].pe++; tbl[m.away].pts++; }
  });

  return teams
    .map(name => ({ name, ...tbl[name], dif: tbl[name].gf - tbl[name].gc }))
    .sort((a, b) => b.pts - a.pts || b.dif - a.dif || b.gf - a.gf);
}

function getGroupPositions(letter) {
  const rows = computeGroup(letter);
  return { 1: rows[0]?.name, 2: rows[1]?.name, 3: rows[2]?.name, 4: rows[3]?.name };
}

function isGroupComplete(letter) {
  const res     = DATA.resultados.partidos || {};
  const matches = DATA.partidos.filter(m => m.group === letter);
  const played  = matches.filter(m => {
    const sc = res[m.id];
    return sc && sc.scoreH != null && sc.scoreA != null;
  });
  return played.length === matches.length && matches.length > 0;
}

// ============================================================
// SLOT RESOLVER
// ============================================================
function resolveSlot(slot) {
  if (!slot) return { team: '?', known: false };

  if (slot.type === 'group_pos') {
    const posLabel = slot.pos === 1 ? '1º' : '2º';
    if (!isGroupComplete(slot.group))
      return { team: `${posLabel} Grupo ${slot.group}`, known: false };
    const pos  = getGroupPositions(slot.group);
    const team = pos[slot.pos];
    if (team) return { team, known: true };
    return { team: `${posLabel} Grupo ${slot.group}`, known: false };
  }

  if (slot.type === 'third') {
    const team = DATA.resultados.terceros?.[slot.key];
    if (team) return { team, known: true };
    return { team: slot.label, known: false };
  }

  if (slot.type === 'winner') {
    const team = resolveMatchWinner(slot.matchId);
    if (team) return { team, known: true };
    return { team: `G. ${findMatchNum(slot.matchId)}`, known: false };
  }

  if (slot.type === 'loser') {
    const team = resolveMatchLoser(slot.matchId);
    if (team) return { team, known: true };
    return { team: `Perd. ${findMatchNum(slot.matchId)}`, known: false };
  }

  return { team: '?', known: false };
}

function findMatchNum(matchId) {
  for (const round of DATA.eliminatorias)
    for (const m of round.matches)
      if (m.id === matchId) return m.num;
  return matchId;
}

function resolveMatchWinner(matchId) {
  const sc = DATA.resultados.eliminatorias?.[matchId];
  if (!sc || sc.scoreH == null || sc.scoreA == null) return null;
  for (const round of DATA.eliminatorias) {
    const m = round.matches.find(x => x.id === matchId);
    if (!m) continue;
    const home = resolveSlot(m.homeSlot);
    const away = resolveSlot(m.awaySlot);
    if (+sc.scoreH > +sc.scoreA) return home.known ? home.team : null;
    if (+sc.scoreA > +sc.scoreH) return away.known ? away.team : null;
    if (sc.penH != null && sc.penA != null)
      return +sc.penH > +sc.penA ? (home.known ? home.team : null)
                                  : (away.known ? away.team : null);
    return null;
  }
  return null;
}

function resolveMatchLoser(matchId) {
  const sc = DATA.resultados.eliminatorias?.[matchId];
  if (!sc || sc.scoreH == null || sc.scoreA == null) return null;
  for (const round of DATA.eliminatorias) {
    const m = round.matches.find(x => x.id === matchId);
    if (!m) continue;
    const home = resolveSlot(m.homeSlot);
    const away = resolveSlot(m.awaySlot);
    if (+sc.scoreH > +sc.scoreA) return away.known ? away.team : null;
    if (+sc.scoreA > +sc.scoreH) return home.known ? home.team : null;
    if (sc.penH != null && sc.penA != null)
      return +sc.penH > +sc.penA ? (away.known ? away.team : null)
                                  : (home.known ? home.team : null);
    return null;
  }
  return null;
}

// ============================================================
// FILTROS — BUILD & RENDER
// ============================================================
function buildFiltros() {
  const allDates  = [...new Set(DATA.partidos.map(m => m.date))].sort();
  const allGroups = [...new Set(DATA.partidos.map(m => m.group))].sort();
  const allTeams  = [...new Set(DATA.partidos.flatMap(m => [m.home, m.away]))].sort();

  const container = document.getElementById('filtrosBar');

  container.innerHTML = `
    <div class="filtro-group">
      <label class="filtro-label">Fase</label>
      <select class="filtro-select" id="f-fase">
        <option value="grupos">Fase de Grupos</option>
        <option value="elim">Eliminatorias</option>
      </select>
    </div>
    <div class="filtro-group" id="fg-fecha">
      <label class="filtro-label">Fecha</label>
      <select class="filtro-select" id="f-fecha">
        <option value="all">Todas las fechas</option>
        ${allDates.map(d => `<option value="${d}">${fmtDate(d)}</option>`).join('')}
      </select>
    </div>
    <div class="filtro-group" id="fg-grupo">
      <label class="filtro-label">Grupo</label>
      <select class="filtro-select" id="f-grupo">
        <option value="all">Todos los grupos</option>
        ${allGroups.map(g => `<option value="${g}">Grupo ${g}</option>`).join('')}
      </select>
    </div>
    <div class="filtro-group" id="fg-equipo">
      <label class="filtro-label">Equipo</label>
      <select class="filtro-select" id="f-equipo">
        <option value="all">Todos los equipos</option>
        ${allTeams.map(t => `<option value="${t}">${FLAG_EMOJI[t]||''} ${t}</option>`).join('')}
      </select>
    </div>
    <button class="filtro-reset" id="f-reset">✕ Limpiar</button>
  `;

  // Eventos
  document.getElementById('f-fase').addEventListener('change', e => {
    FILTROS.fase = e.target.value;
    // En eliminatorias ocultamos fecha/grupo/equipo
    const esElim = FILTROS.fase === 'elim';
    ['fg-fecha','fg-grupo','fg-equipo'].forEach(id =>
      document.getElementById(id).style.display = esElim ? 'none' : '');
    applyFiltros();
  });

  document.getElementById('f-fecha').addEventListener('change', e => {
    FILTROS.fecha = e.target.value;
    // Si elige fecha, resetear grupo y equipo
    if (e.target.value !== 'all') {
      document.getElementById('f-grupo').value = 'all';
      document.getElementById('f-equipo').value = 'all';
      FILTROS.grupo = 'all';
      FILTROS.equipo = 'all';
    }
    applyFiltros();
  });

  document.getElementById('f-grupo').addEventListener('change', e => {
    FILTROS.grupo = e.target.value;
    if (e.target.value !== 'all') {
      document.getElementById('f-fecha').value = 'all';
      document.getElementById('f-equipo').value = 'all';
      FILTROS.fecha = 'all';
      FILTROS.equipo = 'all';
    }
    applyFiltros();
  });

  document.getElementById('f-equipo').addEventListener('change', e => {
    FILTROS.equipo = e.target.value;
    if (e.target.value !== 'all') {
      document.getElementById('f-fecha').value = 'all';
      document.getElementById('f-grupo').value = 'all';
      FILTROS.fecha = 'all';
      FILTROS.grupo = 'all';
    }
    applyFiltros();
  });

  document.getElementById('f-reset').addEventListener('click', () => {
    FILTROS.fecha = 'all'; FILTROS.grupo = 'all';
    FILTROS.equipo = 'all'; FILTROS.fase = 'grupos';
    document.getElementById('f-fecha').value  = 'all';
    document.getElementById('f-grupo').value  = 'all';
    document.getElementById('f-equipo').value = 'all';
    document.getElementById('f-fase').value   = 'grupos';
    ['fg-fecha','fg-grupo','fg-equipo'].forEach(id =>
      document.getElementById(id).style.display = '');
    applyFiltros();
  });
}

function applyFiltros() {
  const container = document.getElementById('fixtureContainer');

  if (FILTROS.fase === 'elim') {
    renderEliminatoriasInFixture();
    return;
  }

  // Filtrar partidos de grupos
  let list = DATA.partidos;
  if (FILTROS.fecha  !== 'all') list = list.filter(m => m.date === FILTROS.fecha);
  if (FILTROS.grupo  !== 'all') list = list.filter(m => m.group === FILTROS.grupo);
  if (FILTROS.equipo !== 'all') list = list.filter(m => m.home === FILTROS.equipo || m.away === FILTROS.equipo);

  renderFixtureList(list);
}

// ============================================================
// RENDER FIXTURE
// ============================================================
function renderFixtureList(list) {
  const res = DATA.resultados.partidos || {};

  if (!list.length) {
    document.getElementById('fixtureContainer').innerHTML =
      '<div class="empty-state">Sin partidos para los filtros seleccionados.</div>';
    return;
  }

  const byDate = {};
  list.forEach(m => { (byDate[m.date] = byDate[m.date] || []).push(m); });

  let html = '';
  Object.keys(byDate).sort().forEach(date => {
    html += `<div class="day-block"><div class="day-label">${fmtDate(date)}</div>`;
    byDate[date].forEach(m => {
      const sc     = res[m.id];
      const played = sc && sc.scoreH != null && sc.scoreA != null;
      html += `
      <div class="match-card${m.argentina ? ' argentina' : ''}${played ? ' has-result' : ''}">
        <div class="match-time">${m.time}</div>
        <div class="team-col home">
          ${flagImg(m.home)}
          <span class="team-name${m.home === 'Argentina' ? ' arg' : ''}">${m.home}</span>
        </div>
        <div class="score-area">
          ${played
            ? `<div class="score-display">
                <span class="score-val">${sc.scoreH}</span>
                <span class="score-sep">:</span>
                <span class="score-val">${sc.scoreA}</span>
               </div>`
            : `<span class="vs-label">VS</span>`}
        </div>
        <div class="team-col away">
          ${flagImg(m.away)}
          <span class="team-name${m.away === 'Argentina' ? ' arg' : ''}">${m.away}</span>
        </div>
        <div class="match-meta">
          <div class="meta-group">GRUPO ${m.group}</div>
          <div class="meta-stadium">${m.stadium}</div>
          <div class="meta-city">${m.city}</div>
          <div class="meta-tv">${m.tv.map(t => `<span class="tv-badge">${t}</span>`).join('')}</div>
        </div>
      </div>`;
    });
    html += '</div>';
  });

  document.getElementById('fixtureContainer').innerHTML = html;
}

// Eliminatorias mostradas dentro de la pestaña Fixture (cuando se filtra por Fase=Eliminatorias)
function renderEliminatoriasInFixture() {
  const res = DATA.resultados.eliminatorias || {};
  let html  = '';

  DATA.eliminatorias.forEach(round => {
    const isFinal = round.id === 'final';
    html += `<div class="day-block">
      <div class="day-label" style="color:var(--red);letter-spacing:3px">${round.name}</div>`;

    round.matches.forEach(m => {
      const sc      = res[m.id];
      const played  = sc && sc.scoreH != null && sc.scoreA != null;
      const hasPen  = played && sc.penH != null;
      const hSlot   = resolveSlot(m.homeSlot);
      const aSlot   = resolveSlot(m.awaySlot);
      const tvBadges = (m.tv || []).map(t => `<span class="tv-badge">${t}</span>`).join('');

      html += `
      <div class="match-card${played ? ' has-result' : ''}${isFinal ? ' argentina' : ''}">
        <div class="match-time" style="font-size:1rem;line-height:1.2">
          <span style="font-size:.75rem;color:var(--muted);display:block">${m.num}</span>
          ${m.time}
        </div>
        <div class="team-col home">
          ${flagImg(hSlot.team)}
          <span class="team-name" style="${!hSlot.known?'color:var(--muted);font-weight:500':''}">${hSlot.team}</span>
        </div>
        <div class="score-area">
          ${played
            ? `<div class="score-display">
                <span class="score-val">${sc.scoreH}</span>
                <span class="score-sep">:</span>
                <span class="score-val">${sc.scoreA}</span>
               </div>
               ${hasPen ? `<div style="text-align:center;font-size:10px;color:var(--muted);margin-top:2px">Pen ${sc.penH}–${sc.penA}</div>` : ''}`
            : `<span class="vs-label">VS</span>`}
        </div>
        <div class="team-col away">
          ${flagImg(aSlot.team)}
          <span class="team-name" style="${!aSlot.known?'color:var(--muted);font-weight:500':''}">${aSlot.team}</span>
        </div>
        <div class="match-meta">
          <div class="meta-group">${fmtDate(m.date)}</div>
          <div class="meta-stadium">${m.stadium}</div>
          <div class="meta-city">${m.city}</div>
          <div class="meta-tv">${tvBadges}</div>
        </div>
      </div>`;
    });

    html += '</div>';
  });

  document.getElementById('fixtureContainer').innerHTML = html;
}

// ============================================================
// RENDER GRUPOS
// ============================================================
function renderGrupos() {
  let html = '';
  Object.keys(DATA.grupos).forEach(g => {
    const rows = computeGroup(g);
    html += `<div class="grupo-card">
      <div class="grupo-header"><span class="grupo-name">GRUPO ${g}</span></div>
      <table class="grupo-table">
        <thead><tr>
          <th colspan="2">Equipo</th>
          <th title="Partidos jugados">PJ</th>
          <th title="Ganados">G</th>
          <th title="Empatados">E</th>
          <th title="Perdidos">P</th>
          <th title="Diferencia">Dif</th>
          <th title="Puntos">Pts</th>
        </tr></thead><tbody>`;
    rows.forEach((row, i) => {
      const isArg = row.name === 'Argentina';
      const qual  = i < 2;
      const dif   = row.dif;
      html += `<tr class="${isArg ? 'cl-arg' : qual ? 'cl-direct' : ''}">
        <td class="pos-num">${i+1}</td>
        <td><div class="team-cell">${flagImg(row.name)}<span>${row.name}</span></div></td>
        <td>${row.pj}</td><td>${row.pg}</td><td>${row.pe}</td><td>${row.pp}</td>
        <td class="${dif>0?'dif-pos':dif<0?'dif-neg':''}">${dif>0?'+':''}${dif}</td>
        <td class="pts-cell">${row.pts}</td>
      </tr>`;
    });
    html += '</tbody></table></div>';
  });
  document.getElementById('gruposContainer').innerHTML = html;
}

// ============================================================
// RENDER ELIMINATORIAS (pestaña propia)
// ============================================================
function renderEliminatorias() {
  const res = DATA.resultados.eliminatorias || {};
  let html  = '';

  DATA.eliminatorias.forEach(round => {
    const isFinal = round.id === 'final';
    const isWide  = ['sf','tercero'].includes(round.id);
    html += `<div class="ko-section${isFinal?' ko-final':isWide?' ko-wide':''}">
      <div class="ko-round-title">${round.name}</div>
      <div class="ko-grid">`;

    round.matches.forEach(m => {
      const sc      = res[m.id];
      const played  = sc && sc.scoreH != null && sc.scoreA != null;
      const hasPen  = played && sc.penH != null && sc.penA != null;
      const hSlot   = resolveSlot(m.homeSlot);
      const aSlot   = resolveSlot(m.awaySlot);
      const tvBadges = (m.tv || []).map(t => `<span class="tv-badge">${t}</span>`).join('');

      html += `<div class="ko-card${isFinal?' final-card':''}">
        <div class="ko-card-top">
          <span class="ko-num">${m.num}</span>
          <div class="ko-meta"><strong>${fmtDate(m.date)}</strong> · ${m.time}<br>${m.stadium}, ${m.city}</div>
        </div>
        <div class="ko-match-row">
          <div class="ko-team${hSlot.known?' known':''}">
            ${flagImg(hSlot.team)}
            <span>${hSlot.team}</span>
          </div>
          <div class="ko-score-wrap">
            ${played
              ? `<span class="ko-score-val">${sc.scoreH}</span>
                 <span class="score-sep">:</span>
                 <span class="ko-score-val">${sc.scoreA}</span>`
              : `<span class="ko-score-val pending">—</span>
                 <span class="score-sep">:</span>
                 <span class="ko-score-val pending">—</span>`}
          </div>
          <div class="ko-team right${aSlot.known?' known':''}">
            <span>${aSlot.team}</span>
            ${flagImg(aSlot.team)}
          </div>
        </div>
        ${hasPen ? `<div class="ko-pen-row">Penales: <strong>${sc.penH} – ${sc.penA}</strong></div>` : ''}
        ${tvBadges ? `<div class="meta-tv" style="margin-top:8px;padding-top:6px;border-top:1px solid var(--border)">${tvBadges}</div>` : ''}
      </div>`;
    });

    html += '</div></div>';
  });

  document.getElementById('knockoutContainer').innerHTML = html;
}

// ============================================================
// NAV
// ============================================================
function initNav() {
  const burger = document.getElementById('hamburger');
  const drawer = document.getElementById('navDrawer');

  burger.addEventListener('click', () => {
    burger.classList.toggle('open');
    drawer.classList.toggle('open');
  });
  document.addEventListener('click', e => {
    if (!burger.contains(e.target) && !drawer.contains(e.target)) {
      burger.classList.remove('open');
      drawer.classList.remove('open');
    }
  });

  function activate(tabId) {
    document.querySelectorAll('.nav-btn,.drawer-btn').forEach(b =>
      b.classList.toggle('active', b.dataset.tab === tabId));
    document.querySelectorAll('.tab-panel').forEach(p =>
      p.classList.toggle('active', p.id === 'tab-' + tabId));
    if (tabId === 'grupos') renderGrupos();
    if (tabId === 'elim')   renderEliminatorias();
    burger.classList.remove('open');
    drawer.classList.remove('open');
  }

  document.querySelectorAll('.nav-btn,.drawer-btn').forEach(btn =>
    btn.addEventListener('click', () => activate(btn.dataset.tab)));
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
  try { await loadData(); }
  catch (e) { console.error('Error cargando datos:', e); }
  buildFiltros();
  applyFiltros();
  initNav();
});