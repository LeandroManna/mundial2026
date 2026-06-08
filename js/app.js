/* ============================================================
   MUNDIAL 2026 — app.js
   Lee datos desde /json/*.json. Sin lógica de escritura.
   Para actualizar resultados editá /json/resultados.json.
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

// ── DATE HELPERS ─────────────────────────────────────────────
const DIAS  = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb'];
const MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul'];

function fmtDate(iso) {
  const d = new Date(iso + 'T12:00:00');
  return `${DIAS[d.getDay()]} ${d.getDate()} ${MESES[d.getMonth()]}`;
}

// ── STATE ────────────────────────────────────────────────────
const DATA = { partidos:[], grupos:{}, eliminatorias:[], resultados:{ partidos:{}, eliminatorias:{}, terceros:{} } };

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

// Returns { 1: "TeamName", 2: "TeamName", 3: "TeamName" } for a group
function getGroupPositions(letter) {
  const rows = computeGroup(letter);
  return { 1: rows[0]?.name, 2: rows[1]?.name, 3: rows[2]?.name, 4: rows[3]?.name };
}

// ============================================================
// SLOT RESOLVER
// Resolves a slot definition to { team, known }
// known = true  → name is a real team (show flag, bold)
// known = false → name is a placeholder (grey, no flag)
// ============================================================
function resolveSlot(slot) {
  if (!slot) return { team: '?', known: false };

  // 1º / 2º de grupo — auto desde tabla
  if (slot.type === 'group_pos') {
    const pos  = getGroupPositions(slot.group);
    const team = pos[slot.pos];
    if (team) return { team, known: true };
    // group not finished yet, show placeholder
    return { team: `${slot.pos === 1 ? '1º' : '2º'} Grupo ${slot.group}`, known: false };
  }

  // 3º mejor — cargado manualmente en resultados.terceros
  if (slot.type === 'third') {
    const team = DATA.resultados.terceros?.[slot.key];
    if (team) return { team, known: true };
    return { team: slot.label, known: false };
  }

  // Ganador de partido anterior
  if (slot.type === 'winner') {
    const team = resolveMatchWinner(slot.matchId);
    if (team) return { team, known: true };
    // find the match num for label
    const matchNum = findMatchNum(slot.matchId);
    return { team: `G. ${matchNum}`, known: false };
  }

  // Perdedor de partido anterior (3er puesto)
  if (slot.type === 'loser') {
    const team = resolveMatchLoser(slot.matchId);
    if (team) return { team, known: true };
    const matchNum = findMatchNum(slot.matchId);
    return { team: `Perd. ${matchNum}`, known: false };
  }

  return { team: '?', known: false };
}

function findMatchNum(matchId) {
  for (const round of DATA.eliminatorias) {
    for (const m of round.matches) {
      if (m.id === matchId) return m.num;
    }
  }
  return matchId;
}

// Returns winner team name from a KO match, or null if not played/draw (needs ET logic, use score for now)
function resolveMatchWinner(matchId) {
  const sc = DATA.resultados.eliminatorias?.[matchId];
  if (!sc || sc.scoreH == null || sc.scoreA == null) return null;

  // Find the match to get its slots
  for (const round of DATA.eliminatorias) {
    const m = round.matches.find(x => x.id === matchId);
    if (!m) continue;
    const home = resolveSlot(m.homeSlot);
    const away = resolveSlot(m.awaySlot);
    if (+sc.scoreH > +sc.scoreA) return home.known ? home.team : null;
    if (+sc.scoreA > +sc.scoreH) return away.known ? away.team : null;
    // Draw — in KO there's ET/penalties. If score is a draw we check for penalties field
    if (sc.penH != null && sc.penA != null) {
      return +sc.penH > +sc.penA ? (home.known ? home.team : null)
                                 : (away.known ? away.team : null);
    }
    return null; // draw without penalties info yet
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
    if (sc.penH != null && sc.penA != null) {
      return +sc.penH > +sc.penA ? (away.known ? away.team : null)
                                 : (home.known ? home.team : null);
    }
    return null;
  }
  return null;
}

// ============================================================
// RENDER FIXTURE
// ============================================================
function renderFixture(filterDate = 'all') {
  const res  = DATA.resultados.partidos || {};
  const list = filterDate === 'all'
    ? DATA.partidos
    : DATA.partidos.filter(m => m.date === filterDate);

  const byDate = {};
  list.forEach(m => { (byDate[m.date] = byDate[m.date] || []).push(m); });

  if (!Object.keys(byDate).length) {
    document.getElementById('fixtureContainer').innerHTML =
      '<div class="empty-state">Sin partidos para esta fecha.</div>';
    return;
  }

  let html = '';
  Object.keys(byDate).sort().forEach(date => {
    html += `<div class="day-block"><div class="day-label">${fmtDate(date)}</div>`;
    byDate[date].forEach(m => {
      const sc      = res[m.id];
      const played  = sc && sc.scoreH != null && sc.scoreA != null;
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

function buildDayFilter() {
  const dates = [...new Set(DATA.partidos.map(m => m.date))].sort();
  const bar   = document.getElementById('dayFilter');
  let html    = '<button class="day-btn active" data-date="all">Todos</button>';
  dates.forEach(d => { html += `<button class="day-btn" data-date="${d}">${fmtDate(d)}</button>`; });
  bar.innerHTML = html;
  bar.querySelectorAll('.day-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      bar.querySelectorAll('.day-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderFixture(btn.dataset.date);
    });
  });
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
// RENDER ELIMINATORIAS
// ============================================================
function renderEliminatorias() {
  const res = DATA.resultados.eliminatorias || {};
  let html  = '';

  DATA.eliminatorias.forEach(round => {
    const isFinal  = round.id === 'final';
    const isWide   = ['sf','tercero'].includes(round.id);
    html += `<div class="ko-section${isFinal?' ko-final':isWide?' ko-wide':''}">
      <div class="ko-round-title">${round.name}</div>
      <div class="ko-grid">`;

    round.matches.forEach(m => {
      const sc     = res[m.id];
      const played = sc && sc.scoreH != null && sc.scoreA != null;
      const hasPen = played && sc.penH != null && sc.penA != null;

      const hSlot  = resolveSlot(m.homeSlot);
      const aSlot  = resolveSlot(m.awaySlot);

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
  buildDayFilter();
  renderFixture();
  initNav();
});