// ---- 책 탭 (한눈에 보기 · 인사이트 · 반박·비평) + 원문 보기 + 내 입장 ----
const BK = D.book || {};
const INS = D.insights || {claims: [], insights: [], rebuttals: []};
const STR = {강: ['강', '--st-hi'], 중: ['중', '--st-mid'], 약: ['약', '--st-lo']};
const setHTML = (node, trusted) => { node.innerHTML = trusted || ''; };  // 서버에서 이스케이프한 HTML만 넣는다
const SRC = (BK.src || {blocks: {}, order: [], chapters: []});
const printOf = a => { const pg = D.pages[a.slice(0, 4)]; return pg ? pg.print : null; };

// 원문 서랍
let curAnc = null;
function openSrc(anc, extra) {
  let id = anc;
  if (!SRC.blocks[id]) { id = SRC.order.find(b => b.startsWith(anc.slice(0, 4))) || null; }
  const dr = $('drawer'); dr.hidden = false; curAnc = id;
  const pg = D.pages[anc.slice(0, 4)];
  $('dCh').textContent = pg ? `${pg.ch} · 인쇄 ${pg.print}쪽 · ${anc}` : anc;
  $('dTitle').textContent = extra && extra.title ? extra.title : '원문';
  const body = $('dBody'); body.innerHTML = '';
  if (extra && extra.img) { const im = h('img', {src: extra.img, alt: extra.title || ''}, body); }
  if (extra && extra.note) { const p_ = h('p', {}, body); h('b', {}, p_, `판정: ${extra.verdict} — `); p_.appendChild(document.createTextNode(extra.note)); }
  if (id) { const blk = SRC.blocks[id]; const p_ = h('p', {}, body, blk[1]); if (!extra || !extra.img) h('div', {class: 'sub'}, body, SRC.chapters[blk[0]]?.label || ''); }
  else h('p', {class: 'muted'}, body, '원문 블록을 찾지 못했습니다.');
}
function stepSrc(d) { if (!curAnc) return; const i = SRC.order.indexOf(curAnc) + d; if (i >= 0 && i < SRC.order.length) openSrc(SRC.order[i]); }
$('dClose').onclick = () => { $('drawer').hidden = true; };
$('dPrev').onclick = () => stepSrc(-1); $('dNext').onclick = () => stepSrc(1);
addEventListener('keydown', e => { if (e.key === 'Escape') $('drawer').hidden = true; });
function wireAnchors(root) {
  root.querySelectorAll('.anc').forEach(a => {
    const k = a.dataset.anc, pg = D.pages[k.slice(0, 4)];
    if (pg) hover(a, () => [[`인쇄 ${pg.print}쪽`, k], [null, pg.ch], [null, '누르면 원문이 열립니다']]);
    a.addEventListener('click', e => { e.stopPropagation(); hideTip(); openSrc(k); });
  });
}

// 내 입장 (브라우저에 저장, 내보내기 → my_stance.json)
const SKEY = `bookc-stance:${BK.slug || D.title}`;
let STANCE = {};
try { STANCE = JSON.parse(localStorage.getItem(SKEY) || '{}'); } catch (e) { STANCE = {}; }
const saveStance = () => { try { localStorage.setItem(SKEY, JSON.stringify(STANCE)); } catch (e) {} updateStanceBars(); };
function stanceUI(parent, item) {
  const w = h('div', {class: 'stance'}, parent);
  const cur = STANCE[item.id] || {};
  [['agree', '동의'], ['hold', '보류'], ['disagree', '반대']].forEach(([k, lab]) => {
    const b_ = h('button', {'aria-pressed': String(cur.s === k)}, w, lab);
    b_.onclick = () => { const s = STANCE[item.id] || {}; s.s = s.s === k ? undefined : k; s.t = item.title; STANCE[item.id] = s; saveStance();
      w.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', 'false')); if (s.s) b_.setAttribute('aria-pressed', 'true'); };
  });
  const inp = h('input', {placeholder: '한 줄 메모', value: cur.n || ''}, w);
  inp.onchange = () => { const s = STANCE[item.id] || {}; s.n = inp.value; s.t = item.title; STANCE[item.id] = s; saveStance(); };
}
function updateStanceBars() {
  const n = Object.values(STANCE).filter(x => x.s || x.n).length;
  document.querySelectorAll('.stancebar').forEach(bar => {
    bar.innerHTML = '';
    const b_ = h('button', {}, bar, `내 입장 내보내기 (${n}개)`);
    hover(b_, () => [[null, '내려받은 my_stance.json을 책 폴더에 넣으면'], [null, '7단계 리뷰가 내 입장을 반영합니다']]);
    b_.onclick = () => {
      const items = Object.entries(STANCE).filter(([, v]) => v.s || v.n).map(([id, v]) => ({id, title: v.t || '', stance: v.s || '', note: v.n || ''}));
      const blob = new Blob([JSON.stringify({book: D.title, exported: new Date().toISOString(), items}, null, 1)], {type: 'application/json'});
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'my_stance.json'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    };
  });
}

// 공통 카드
function card(box, it, extra, withStance) {
  const d = h('div', {class: 'icard', id: 'card-' + it.id}, box);
  const hh = h('h3', {}, d); h('span', {class: 'id'}, hh, it.id); hh.appendChild(document.createTextNode(it.title));
  if (extra) extra(d);
  const b = h('div', {}, d); setHTML(b, it.html); wireAnchors(b);
  if (withStance) stanceUI(d, it);
  return d;
}
function goCard(tab, id) { showTab(tab); setTimeout(() => { const c = document.getElementById('card-' + id); if (!c) return; c.scrollIntoView({behavior: 'smooth', block: 'center'}); c.classList.add('flash'); setTimeout(() => c.classList.remove('flash'), 1400); }, 60); }
const byClaim = {}; INS.claims.forEach(c => byClaim[c.id] = []); INS.rebuttals.forEach(r => r.target.forEach(t => { if (byClaim[t]) byClaim[t].push(r); }));

// 머리 카드: 책 정보
function renderBookcard() {
  const I = BK.info || {}; const box = $('bookcard'); box.innerHTML = '';
  const t = h('div', {}, box); h('span', {class: 'bt'}, t, `『${I.title || D.title}』`); if (I.subtitle) h('span', {class: 'bs'}, t, `  ${I.subtitle}`);
  const dl = h('dl', {}, box);
  const row = (k, v) => { if (!v) return; const d = h('div', {}, dl); h('dt', {}, d, k); h('dd', {}, d, v); };
  row('지은이 · 옮긴이', [I.author, I.translator && `${I.translator} 옮김`].filter(Boolean).join(' · '));
  row('출판사', [I.publisher, I.imprint && `(${I.imprint})`].filter(Boolean).join(' '));
  row('한국어판 출간', I.pub_date || I.year);
  row('원서', [I.original_title].filter(Boolean).join(''));
  row('원서 출판사 · 출간', [I.original_publisher, I.original_pub_date].filter(Boolean).join(' · '));
  row('쪽수', [I.pages_printed && `${I.pages_printed}쪽`, I.pdf_pages && `(PDF ${I.pdf_pages}쪽)`].filter(Boolean).join(' '));
  row('ISBN', I.isbn);
  row('이전 번역판', Array.isArray(I.prior_editions) ? I.prior_editions.join(' / ') : I.prior_editions);
  row('분야', I.genre);
  if (I.info_sources) h('div', {class: 'sub', style: 'font-size:11px'}, box, `책 정보 출처: ${I.info_sources}`);
}

// 한눈에 보기
let revKey = null;
function renderGlance() {
  setHTML($('oneline'), INS.oneline || (INS.bottom || '').split('</p>')[0] || '<span class="muted">6단계(인사이트)가 끝나면 한 줄 요약이 나옵니다.</span>'); wireAnchors($('oneline'));
  // 리뷰
  const R = BK.reviews; const seg = $('revSeg'); seg.innerHTML = '';
  if (!R) { $('revMeta').innerHTML = ''; $('revChecks').innerHTML = ''; setHTML($('revBody'), '<p class="muted">아직 리뷰가 없습니다. /bookc-7-review 로 서점 리뷰·비평형 서평·독서 기록을 만들 수 있습니다.</p>'); }
  else {
    if (!revKey || !R.variants.some(v => v.key === revKey)) revKey = R.variants[0].key;
    R.variants.forEach(v => { const b_ = h('button', {'aria-pressed': String(v.key === revKey)}, seg, v.name); b_.onclick = () => { revKey = v.key; renderGlance(); }; });
    const v = R.variants.find(x => x.key === revKey), m = v.meta || {};
    const meta = $('revMeta'); meta.innerHTML = '';
    if (m.stars) h('b', {}, meta, '★'.repeat(Math.round(m.stars)) + '☆'.repeat(5 - Math.round(m.stars)) + ` ${m.stars}`);
    h('span', {class: 'sub'}, meta, `${v.title ? v.title + ' · ' : ''}${v.chars.toLocaleString()}자`);
    if (m.stance_used != null) h('span', {class: 'sub'}, meta, m.stance_used ? '· 내 입장 반영' : '· 내 입장 없이 작성(개인 경험 부분은 빈자리)');
    const ch = $('revChecks'); ch.innerHTML = '';
    if (m.checks) { const g = h('div', {class: 'checks'}, ch); Object.entries(m.checks).forEach(([k, x]) => { const d = h('div', {}, g); h('span', {class: x.pass ? 'ok' : 'no'}, d, x.pass ? '✓ ' : '✕ '); d.appendChild(document.createTextNode(k + (x.note ? ` — ${x.note}` : ''))); }); }
    setHTML($('revBody'), v.html); wireAnchors($('revBody'));
  }
  // 장별 흐름
  const fl = $('flow'); fl.innerHTML = '';
  (BK.flow || []).forEach(f => { const li = h('li', {}, fl); h('b', {}, li, `${f.label}  `); const sp = h('span', {}, li); sp.innerHTML = f.text.replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'})[c]).replace(/\b(p\d{3}(?:-b\d+)?)\b/g, '<span class="anc" data-anc="$1">$1</span>'); wireAnchors(sp); });
  // 핵심 주장
  const cl = $('claims'); cl.innerHTML = ''; $('nClaims').textContent = `${INS.claims.length}개`;
  INS.claims.forEach(c => card(cl, c, d => { const n = byClaim[c.id] || []; if (n.length) { const m = h('div', {class: 'meta'}, d); const ch_ = h('span', {class: 'chip'}, m, `반박 ${n.length}개 보기 →`); ch_.onclick = () => goCard('crit', n[0].id); } }, true));
  // 장 지도
  renderHeat();
  // 질문
  const qs = $('qs'); qs.innerHTML = ''; const Q = BK.questions || {discuss: [], open: []};
  Q.discuss.forEach(q => { const li = h('li', {}, qs); const sp = h('span', {}, li); sp.innerHTML = q.replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'})[c]).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/\b(p\d{3}(?:-b\d+)?)\b/g, '<span class="anc" data-anc="$1">$1</span>'); wireAnchors(sp);
    const b_ = h('button', {}, li, '대화로 복사'); b_.onclick = () => { const txt = `/book-companion:bookc-open ${BK.slug || D.title} — ${q.replace(/\*\*/g, '')}`; (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject()).then(() => { b_.textContent = '복사됨 ✓'; setTimeout(() => b_.textContent = '대화로 복사', 1500); }).catch(() => { b_.textContent = '복사 실패'; }); }; });
  if (!Q.discuss.length) h('li', {class: 'muted'}, qs, '5단계(종합)의 질문이 여기에 나옵니다.');
  const qo = $('qopen'); qo.innerHTML = ''; $('nOpen').textContent = `(${Q.open.length})`; Q.open.forEach(q => h('li', {}, qo, q.replace(/\*\*/g, '')));
}
function renderHeat() {
  const tb = $('heat'); tb.innerHTML = ''; const M = BK.map || []; if (!M.length) return;
  const cols = [['minutes', '읽기(분)'], ['claims', '핵심 주장'], ['rebut', '반박 강도'], ['figbad', '도표 부분·어긋남'], ['ext', '외부 근거 반박']];
  const max = Object.fromEntries(cols.map(([k]) => [k, Math.max(1, ...M.map(r => r[k]))]));
  const score = r => r.claims * 2 + r.rebut + r.figbad * 0.5; const ranked = [...M].sort((a, b) => score(b) - score(a));
  const must = new Set(ranked.slice(0, 3).map(r => r.id)), skim = new Set(ranked.slice(-2).map(r => r.id));
  const hr = h('tr', {}, h('thead', {}, tb)); h('th', {}, hr, '장'); cols.forEach(([, l]) => h('th', {}, hr, l)); h('th', {}, hr, '읽기 안내');
  const body = h('tbody', {}, tb);
  M.forEach(r => { const tr = h('tr', {}, body); h('td', {}, tr, r.label);
    cols.forEach(([k, l]) => { const v = r[k], f = v / max[k]; const td = h('td', {class: 'h', style: `background:color-mix(in srgb,var(--seq) ${Math.round(f * 70)}%,var(--surface-1));color:${f > .8 ? '#fff' : 'var(--text-primary)'};font-weight:${f > .8 ? 600 : 400}`}, tr, k === 'figbad' ? `${v}/${r.figs}` : String(v));
      hover(td, () => [[k === 'figbad' ? `${v}/${r.figs}` : String(v), l], [null, r.label]]); });
    h('td', {}, tr, must.has(r.id) ? '★ 꼭 읽기' : skim.has(r.id) ? '훑어도 됨' : ''); });
}

// 인사이트
function renderIns() { const box = $('insights'); box.innerHTML = ''; $('nIns').textContent = `${INS.insights.length}개`;
  if (!INS.insights.length) { h('div', {class: 'muted'}, box, '6단계(인사이트)가 끝나면 여기에 나옵니다.'); return; }
  INS.insights.forEach(i => card(box, i)); }

// 반박·비평
let figFilter = '전체';
function renderCrit() {
  // 차트
  const box = $('rebChart'); box.innerHTML = '';
  const rows = INS.claims.map(c => ({c, n: {강: 0, 중: 0, 약: 0}, list: byClaim[c.id] || []})); rows.forEach(r => r.list.forEach(x => { if (r.n[x.strength] != null) r.n[x.strength]++; }));
  if (rows.length) {
    const max = Math.max(1, ...rows.map(r => r.n.강 + r.n.중 + r.n.약)), W = Math.max(420, box.clientWidth || 800), lab = Math.min(360, W * 0.42), rh = 28, bw = W - lab - 60;
    const svg = el('svg', {width: W, height: rows.length * rh + 6, role: 'img', 'aria-label': '주장별 반박 강도'}, box);
    rows.forEach((r, i) => { const y = i * rh + 4; const title = `${r.c.id} ${r.c.title}`; el('text', {x: 0, y: y + 15, fill: css('--text-primary'), 'font-size': 12}, svg, title.length > 34 ? title.slice(0, 33) + '…' : title);
      let x = lab; ['강', '중', '약'].forEach(k => { const w = r.n[k] / max * bw; if (w > 0) { el('rect', {x, y: y + 5, width: Math.max(2, w - 2), height: 14, rx: 3, fill: css(STR[k][1])}, svg); x += w; } });
      const tot = r.n.강 + r.n.중 + r.n.약; el('text', {x: x + 6, y: y + 16, fill: css('--text-secondary'), 'font-size': 12}, svg, tot ? `${tot}` : '반박 없음');
      const hit = el('rect', {x: 0, y, width: W, height: rh, fill: 'transparent'}, svg); hit.style.cursor = 'pointer'; hit.addEventListener('click', () => { if (r.list[0]) goCard('crit', r.list[0].id); });
      hover(hit, () => [[`${tot}개`, `${r.c.id} ${r.c.title}`], ...r.list.map(x => [null, `${x.id} [${x.strength}] ${x.title}`])]); });
    $('rebNote').textContent = `반박 ${INS.rebuttals.length}개 중 강 ${INS.rebuttals.filter(r => r.strength === '강').length}개 · 막대를 누르면 해당 반박 카드로 이동`;
  } else h('div', {class: 'muted'}, box, '6단계(인사이트)가 끝나면 여기에 나옵니다.');
  // 반박 카드
  const rb = $('rebuttals'); rb.innerHTML = ''; $('nReb').textContent = `${INS.rebuttals.length}개`;
  INS.rebuttals.forEach(r => card(rb, r, d => { const m = h('div', {class: 'meta'}, d); const st = STR[r.strength];
    if (st) { const s_ = h('span', {class: 'str'}, m); h('i', {style: `width:${{강: 36, 중: 24, 약: 12}[r.strength]}px;background:var(${st[1]})`}, s_); s_.appendChild(document.createTextNode(`강도 ${st[0]}`)); }
    if (r.type) m.appendChild(document.createTextNode(`  ·  ${r.type}  ·  `)); r.target.forEach(t => { const ch = h('span', {class: 'chip'}, m, `${t} 주장 보기`); ch.onclick = () => goCard('glance', t); }); }, true));
  // 외부 비평
  const cr = $('critiques'); cr.innerHTML = ''; cr.className = 'crit';
  (BK.critiques || []).forEach((c, i) => { const d = h('details', i === 0 ? {open: ''} : {}, cr); h('summary', {}, d, c.title); const b = h('div', {class: 'prose'}, d); setHTML(b, c.html);
    b.querySelectorAll('p,li').forEach(n => { n.innerHTML = n.innerHTML.replace(/\[(\d+)\]/g, (m0, k) => BK.sources && BK.sources[k] ? `<span class="chip src" data-k="${k}">[${k}]</span>` : m0); });
    b.querySelectorAll('.src').forEach(s_ => { const k = s_.dataset.k, S = BK.sources[k]; hover(s_, () => [[`[${k}]`, S.t]]); s_.onclick = () => { if (S.u) window.open(S.u, '_blank', 'noopener'); }; });
    wireAnchors(b); });
  if (!(BK.critiques || []).length) h('div', {class: 'muted'}, cr, '3단계(조사)의 critiques.md가 여기에 나옵니다.');
  // 도표 신뢰도
  const F = BK.figures || []; const cnt = {전체: F.length}; F.forEach(f => cnt[f.verdict] = (cnt[f.verdict] || 0) + 1);
  $('nFigs').textContent = `${F.length}개 · 맞음 ${cnt['맞음'] || 0} · 부분적 ${cnt['부분적'] || 0} · 어긋남 ${cnt['어긋남'] || 0}`;
  const seg = $('figSeg'); seg.innerHTML = ''; ['전체', '부분적', '어긋남', '맞음', '판정 없음'].forEach(k => { if (k !== '전체' && !cnt[k]) return; const b_ = h('button', {'aria-pressed': String(figFilter === k)}, seg, `${k} ${cnt[k] || 0}`); b_.onclick = () => { figFilter = k; renderCrit(); }; });
  const g = $('figs'); g.innerHTML = '';
  F.filter(f => figFilter === '전체' || f.verdict === figFilter).forEach(f => { const d = h('div', {class: 'fig', tabindex: '0'}, g); h('img', {src: f.img, alt: f.title, loading: 'lazy'}, d); h('div', {class: 't'}, d, f.title);
    const icon = {맞음: '✓ ', 부분적: '◐ ', 어긋남: '✕ '}[f.verdict] || '– '; h('span', {class: 'vb v-' + f.verdict.replace(/\s/g, '')}, d, icon + f.verdict);
    const pr = printOf(f.id); if (pr) h('span', {class: 'sub', style: 'margin-left:6px;font-size:11px'}, d, `${pr}쪽`);
    const open = () => openSrc(f.id, f); d.onclick = open; d.onkeydown = e => { if (e.key === 'Enter') open(); }; });
}

// 탭
const TABS = {glance: ['tab-glance', 'pane-glance', '#overview', renderGlance], ins: ['tab-ins', 'pane-ins', '#insights', renderIns], crit: ['tab-crit', 'pane-crit', '#critique', renderCrit], prog: ['tab-prog', 'pane-prog', '#progress', () => renderAll()]};
function showTab(which) { Object.entries(TABS).forEach(([k, [t, p]]) => { $(t).setAttribute('aria-selected', String(k === which)); $(p).hidden = k !== which; });
  if (history.replaceState) history.replaceState(null, '', TABS[which][2]); TABS[which][3](); updateStanceBars(); }
Object.entries(TABS).forEach(([k, [t]]) => { $(t).onclick = () => showTab(k); });
renderBookcard();
