// ---- 책 탭 (한눈에 보기 · 인사이트 · 반박·비평) + 원문 보기 + 내 입장 ----
const BK = D.book || {};
const INS = D.insights || {claims: [], insights: [], rebuttals: []};
const STR = {강: ['강', '--st-hi'], 중: ['중', '--st-mid'], 약: ['약', '--st-lo']};
const setHTML = (node, trusted) => { node.innerHTML = trusted || ''; };  // 서버에서 이스케이프한 HTML만 넣는다
const SRC = (BK.src || {blocks: {}, order: [], chapters: []});
const printOf = a => { const pg = D.pages[a.slice(0, 4)]; return pg ? pg.print : null; };

// 원문 서랍 + 목차 리모콘
let curAnc = null;
const FIGIMG = Object.fromEntries((BK.figures || []).map(f => [f.id, f]));
const chFirst = ci => SRC.order.find(b => SRC.blocks[b][0] === ci);
function openSrc(anc, extra) {
  let id = anc;
  if (!SRC.blocks[id]) { id = SRC.order.find(b => b.startsWith(anc.slice(0, 4))) || null; }
  const dr = $('drawer'); dr.hidden = false; document.body.classList.add('reading'); curAnc = id;
  const key = (id || anc), pg = D.pages[key.slice(0, 4)];
  $('dCh').textContent = pg ? `${pg.ch} · 인쇄 ${pg.print}쪽 · ${key}` : key;
  const blk = id ? SRC.blocks[id] : null;
  const fig = extra && extra.img ? extra : (id && FIGIMG[id]) || null;
  $('dTitle').textContent = fig ? fig.title : blk && blk[2] && blk[2].startsWith('h') ? blk[1] : '원문';
  const body = $('dBody'); body.innerHTML = '';
  if (fig && fig.img) h('img', {src: fig.img, alt: fig.title || ''}, body);
  if (fig && fig.note) { const p_ = h('p', {class: 'verdict'}, body); h('b', {}, p_, `판정: ${fig.verdict} — `); p_.appendChild(document.createTextNode(fig.note)); }
  if (blk) {  // 현재 문단을 강조하고, 같은 장에서 이어지는 문단 몇 개를 함께 보여 준다
    const i0 = SRC.order.indexOf(id); let shown = 0;
    for (let i = i0; i < SRC.order.length && shown < 4; i++) {
      const bid = SRC.order[i], b2 = SRC.blocks[bid]; if (b2[0] !== blk[0]) break;
      if (i > i0 && b2[2] === 'h2') break;
      const cur = i === i0 ? ' cur' : '';
      const el_ = (b2[2] || '').startsWith('h') ? h('h4', {class: 'srch' + cur}, body, b2[1]) : h('p', {class: 'srcp' + cur}, body, b2[2] === 'fig' ? '▦ ' + b2[1] : b2[1]);
      if (i > i0) el_.onclick = () => openSrc(bid);
      if (!(b2[2] || '').startsWith('h')) shown++;
    }
  }
  else h('p', {class: 'muted'}, body, '원문 블록을 찾지 못했습니다.');
  body.scrollTop = 0; $('drawer').querySelector('.dmain').scrollTop = 0;
  if (id) { const i = SRC.order.indexOf(id); $('dPos').textContent = `${i + 1} / ${SRC.order.length}`; }
  try { localStorage.setItem(`bookc-last:${BK.slug}`, id || ''); } catch (e) {}
  renderRemote();
}
function stepSrc(d) { if (!curAnc) return; const i = SRC.order.indexOf(curAnc) + d; if (i >= 0 && i < SRC.order.length) openSrc(SRC.order[i]); }
function stepKind(d, test) { if (!curAnc) return; let i = SRC.order.indexOf(curAnc) + d; while (i >= 0 && i < SRC.order.length) { if (test(SRC.blocks[SRC.order[i]], SRC.order[i])) { openSrc(SRC.order[i]); return; } i += d; } }
function stepChapter(d) { if (!curAnc) return; const ci = SRC.blocks[curAnc][0] + d; if (ci < 0 || ci >= SRC.chapters.length) return; const f = chFirst(ci); if (f) openSrc(f); }
function renderRemote() {
  const nav = $('remote'); nav.innerHTML = ''; const cur = curAnc ? SRC.blocks[curAnc][0] : -1;
  h('div', {class: 'rt'}, nav, '목차');
  SRC.chapters.forEach((c, ci) => {
    const f = chFirst(ci); if (!f) return;
    const b_ = h('button', {class: 'rc' + (ci === cur ? ' on' : '')}, nav, c.label.replace(/^제(\d+)장\s*/, '$1장 '));
    b_.onclick = () => openSrc(f);
    if (ci === cur) {
      const secs = SRC.order.filter(b => SRC.blocks[b][0] === ci && SRC.blocks[b][2] === 'h2');
      const curSecIdx = (() => { let last = -1; const pos = SRC.order.indexOf(curAnc); secs.forEach((s_, k) => { if (SRC.order.indexOf(s_) <= pos) last = k; }); return last; })();
      secs.forEach((sid, k) => { const sb = h('button', {class: 'rs' + (k === curSecIdx ? ' on' : '')}, nav, SRC.blocks[sid][1]); sb.onclick = () => openSrc(sid); });
    }
  });
  const on = nav.querySelector('.rs.on') || nav.querySelector('.rc.on'); if (on) on.scrollIntoView({block: 'nearest'});
}
const closeSrc = () => { $('drawer').hidden = true; document.body.classList.remove('reading'); };
$('dClose').onclick = closeSrc;
$('dPrev').onclick = () => stepSrc(-1); $('dNext').onclick = () => stepSrc(1);
$('readerBtn').onclick = () => { let last = ''; try { last = localStorage.getItem(`bookc-last:${BK.slug}`) || ''; } catch (e) {} openSrc(SRC.blocks[last] ? last : SRC.order[0]); };
addEventListener('keydown', e => {
  if ($('drawer').hidden) return;
  if (/^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName || '')) return;
  const isH = b => (b[2] || '').startsWith('h');
  const map = {Escape: () => closeSrc(), ArrowRight: () => stepSrc(1), ArrowLeft: () => stepSrc(-1),
    ArrowDown: () => stepKind(1, isH), ArrowUp: () => stepKind(-1, isH), PageDown: () => stepChapter(1), PageUp: () => stepChapter(-1)};
  if (map[e.key]) { e.preventDefault(); map[e.key](); }
});
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
function card(box, it, extra, footer) {
  const d = h('div', {class: 'icard', id: 'card-' + it.id}, box);
  const hh = h('h3', {}, d); h('span', {class: 'id'}, hh, it.id); hh.appendChild(document.createTextNode(it.title));
  if (extra) extra(d);
  const b = h('div', {}, d); setHTML(b, it.html); wireAnchors(b);
  if (typeof footer === 'function') footer(d);
  return d;
}
// 카드 아래 연결 목록 (주장 ↔ 반박)
function linkList(d, label, rows) {
  if (!rows.length) return;
  const f = h('div', {class: 'lnk'}, d); h('div', {class: 'lnkHead'}, f, label);
  rows.forEach(([tab, id, title, strength]) => {
    const a = h('button', {class: 'lnkRow', type: 'button'}, f);
    if (strength && STR[strength]) h('span', {class: 'lnkStr', style: `background:var(${STR[strength][1]})`}, a, strength);
    h('span', {class: 'lnkId'}, a, id); h('span', {class: 'lnkT'}, a, title || ''); h('span', {class: 'lnkGo'}, a, '→');
    a.onclick = () => goCard(tab, id);
  });
}
function goCard(tab, id) { showTab(tab); setTimeout(() => { const c = document.getElementById('card-' + id); if (!c) return; c.scrollIntoView({behavior: 'smooth', block: 'center'}); c.classList.add('flash'); setTimeout(() => c.classList.remove('flash'), 1400); }, 60); }
const byClaim = {}; INS.claims.forEach(c => byClaim[c.id] = []); INS.rebuttals.forEach(r => r.target.forEach(t => { if (byClaim[t]) byClaim[t].push(r); }));

// 머리 카드: 책 정보 (접기 상태 기억)
function renderBookcard() {
  const I = BK.info || {};
  const cv = $('cover'); if (cv && I.cover) { cv.src = I.cover; cv.hidden = false; cv.onclick = () => cv.classList.toggle('big'); } const det = $('bookcard'); const sum = $('bookSum'); const box = $('bookBody'); sum.innerHTML = ''; box.innerHTML = '';
  h('span', {class: 'bt'}, sum, `『${I.title || D.title}』`); if (I.subtitle) h('span', {class: 'bs'}, sum, I.subtitle);
  h('span', {class: 'bm'}, sum, [I.author, I.translator && (/편역|옮김|번역/.test(I.translator) ? I.translator : `${I.translator} 옮김`), I.pub_date ? I.pub_date.split('(')[0].trim() : I.year].filter(Boolean).join(' · '));
  const dl = h('dl', {}, box);
  const row = (k, v) => { if (!v) return; const d = h('div', {}, dl); h('dt', {}, d, k); h('dd', {}, d, v); };
  row(I.translator ? '지은이 · 옮긴이' : '지은이', [I.author, I.translator && (/편역|옮김|번역/.test(I.translator) ? I.translator : `${I.translator} 옮김`)].filter(Boolean).join(' · '));
  row('출판사', [I.publisher, I.imprint && `(${I.imprint})`].filter(Boolean).join(' '));
  const orig = I.lang && I.lang !== 'ko';   // 원서 자체를 처리한 책
  row(orig ? '출간' : '한국어판 출간', I.pub_date || I.year);
  if (!orig || (I.original_title && I.original_title !== I.title)) {
    row('원서', I.original_title);
    row('원서 출판사 · 출간', [I.original_publisher, I.original_pub_date].filter(Boolean).join(' · '));
  }
  row('쪽수', [I.pages_printed && `${I.pages_printed}쪽`, I.pdf_pages && `PDF ${I.pdf_pages}쪽`].filter(Boolean).join(' · '));
  row('ISBN', I.isbn);
  row(orig ? '한국어 번역서' : '다른 번역서', Array.isArray(I.prior_editions) ? I.prior_editions.join('\n') : I.prior_editions);
  row('분야', I.genre);
  row('비고', I.note);
  if (I.info_sources) h('div', {class: 'sub src-note'}, box, `책 정보 출처: ${I.info_sources}`);
  let open = true; try { open = localStorage.getItem('bookc-bookcard') !== 'closed'; } catch (e) {}
  det.open = open; det.addEventListener('toggle', () => { try { localStorage.setItem('bookc-bookcard', det.open ? 'open' : 'closed'); } catch (e) {} });
}


// 리뷰 본문을 '총평 + 섹션 카드'로 나눈다 (## 기준)
function sectionize(root) {
  const nodes = [...root.childNodes].filter(n => !(n.nodeType === 3 && !n.textContent.trim()));
  const HX = nodes.some(n => n.nodeName === 'H2') ? 'H2' : 'H4'; if (!nodes.some(n => n.nodeName === HX)) return;
  root.innerHTML = '';
  const lead = h('div', {class: 'rvLead'}, root), grid = h('div', {class: 'rvGrid'}, root);
  let cur = null;
  nodes.forEach(n => {
    if (n.nodeName === 'H1') return;
    if (n.nodeName === HX) { cur = h('section', {class: 'rvSec'}, grid); n.className = 'rvH'; cur.appendChild(n); return; }
    if (n.nodeName === 'P' && n.firstChild && n.firstChild.nodeName === 'STRONG' && /[.:]\s*$/.test(n.firstChild.textContent)) n.classList.add('rvItem');
    (cur || lead).appendChild(n);
  });
  if (!lead.childNodes.length) lead.remove();
}

// 장별 흐름 ↔ 핵심 주장 연결선 (주장의 쪽 표시가 속한 장)
function linkFlowClaims() {
  const split = $('flow').closest('.split'); if (!split) return;
  const F = BK.flow || [], pageCh = p => (F.find(f => f.pages && p >= f.pages[0] && p <= f.pages[1]) || {}).id;
  const pairs = [];
  INS.claims.forEach(c => { const set = new Set(); (c.html.match(/p(\d{3})(?:-b\d+)?/g) || []).forEach(a => { const ch = pageCh(+a.slice(1, 4)); if (ch) set.add(ch); }); set.forEach(ch => pairs.push([ch, c.id])); });
  split.classList.add('linked');
  let svg = split.querySelector('svg.links'); if (!svg) { svg = el('svg', {class: 'links'}, null); split.appendChild(svg); }
  const lis = {}; split.querySelectorAll('#flow li[data-ch]').forEach(li => lis[li.dataset.ch] = li);
  const cards = {}; INS.claims.forEach(c => { const d = document.getElementById('card-' + c.id); if (d) cards[c.id] = d; });
  const deg = {}; pairs.forEach(([a, b]) => { deg[a] = (deg[a] || 0) + 1; deg[b] = (deg[b] || 0) + 1; });
  Object.entries(lis).forEach(([k, li]) => { let b = li.querySelector('.lkN'); if (!b) b = h('span', {class: 'lkN'}, li.querySelector('.fh')); b.textContent = deg[k] ? `주장 ${deg[k]}` : ''; });
  function draw() {
    svg.innerHTML = '';
    const R = split.getBoundingClientRect(); svg.setAttribute('width', R.width); svg.setAttribute('height', R.height);
    if (getComputedStyle(split).gridTemplateColumns.split(' ').length < 2) return;
    pairs.forEach(([ch, k]) => {
      const a = lis[ch], b = cards[k]; if (!a || !b) return;
      const ra = a.querySelector('.fh').getBoundingClientRect(), rb = b.querySelector('h3').getBoundingClientRect();
      const x1 = a.closest('.panel').getBoundingClientRect().right - R.left, y1 = ra.top + ra.height / 2 - R.top;
      const x2 = b.closest('.panel').getBoundingClientRect().left - R.left, y2 = rb.top + rb.height / 2 - R.top;
      const mx = (x1 + x2) / 2;
      const p = el('path', {d: `M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`, class: 'lk', 'data-ch': ch, 'data-k': k}, svg);
      el('circle', {cx: x1, cy: y1, r: 3, class: 'lkDot', 'data-ch': ch, 'data-k': k}, svg); el('circle', {cx: x2, cy: y2, r: 3, class: 'lkDot', 'data-ch': ch, 'data-k': k}, svg);
    });
  }
  function hl(ch, k) {
    const on = (x) => (ch && x.dataset.ch === ch) || (k && x.dataset.k === k);
    const act = !!(ch || k); split.classList.toggle('lkAct', act);
    svg.querySelectorAll('.lk,.lkDot').forEach(x => x.classList.toggle('on', act && on(x)));
    const rel = new Set(pairs.filter(([a, b]) => (ch && a === ch) || (k && b === k)).flatMap(([a, b]) => [a, b]));
    Object.entries(lis).forEach(([id, li]) => li.classList.toggle('lkOn', act && rel.has(id)));
    Object.entries(cards).forEach(([id, d]) => d.classList.toggle('lkOn', act && rel.has(id)));
  }
  let pop = document.getElementById('lkPop'); if (!pop) { pop = h('div', {id: 'lkPop', role: 'tooltip'}, split.closest('.viz-root') || document.body); }
  const chOf = id => F.find(f => f.id === id) || {}, clOf = id => INS.claims.find(c => c.id === id) || {};
  function showPop(anchor, head, rows) {
    pop.innerHTML = ''; if (!rows.length) { pop.classList.remove('on'); return; }
    h('div', {class: 'lpH'}, pop, head);
    rows.forEach(([id, t, sub]) => { const r = h('div', {class: 'lpR'}, pop); h('span', {class: 'lpId'}, r, id); const b = h('div', {}, r); h('div', {class: 'lpT'}, b, t || ''); if (sub) h('div', {class: 'lpS'}, b, sub); });
    const a = anchor.getBoundingClientRect(), gap = 16, vw = document.documentElement.clientWidth;
    const card = split.closest('.card') || split, pr = card.getBoundingClientRect();
    const room = vw - pr.right - gap - 12; let W = 300, x;
    if (room >= 220) { W = Math.min(320, room); x = pr.right + gap; }
    else { W = 280; x = a.left - W - gap; if (x < 8) x = Math.min(vw - W - 8, a.right + gap); }
    pop.style.left = x + 'px'; pop.style.width = W + 'px';
    pop.classList.add('on');
    const ph = pop.offsetHeight, vh = window.innerHeight; let y = a.top; y = Math.max(8, Math.min(y, vh - ph - 8));
    pop.style.top = y + 'px';
  }
  const hidePop = () => pop.classList.remove('on');
  Object.entries(lis).forEach(([id, li]) => {
    li.onmouseenter = () => { hl(id, null); const ks = pairs.filter(p => p[0] === id).map(p => p[1]); showPop(li, `${chOf(id).label || id}에서 나온 주장 ${ks.length}개`, ks.map(k => [k, clOf(k).title, `반박 ${(byClaim[k] || []).length}개`])); };
    li.onmouseleave = () => { hl(null, null); hidePop(); };
  });
  Object.entries(cards).forEach(([id, d]) => {
    d.onmouseenter = () => { hl(null, id); const cs = pairs.filter(p => p[1] === id).map(p => p[0]); const rb = byClaim[id] || [];
      showPop(d, `${id} 근거가 나온 장 ${cs.length}개`, cs.map(c => { const f = chOf(c); return [String(+c || c), f.label, f.pages ? `PDF ${f.pages[0]}–${f.pages[1]}쪽 · ${Math.max(1, Math.round(f.chars / 500))}분` : '']; }).concat(rb.length ? [['', `반박 ${rb.length}개`, rb.map(r => `${r.strength} ${r.id}`).join(' · ')]] : [])); };
    d.onmouseleave = () => { hl(null, null); hidePop(); };
  });
  window.addEventListener('scroll', hidePop, {passive: true});
  requestAnimationFrame(draw);
  if (!split._ro) { split._ro = new ResizeObserver(() => requestAnimationFrame(draw)); split._ro.observe(split); document.querySelectorAll('.tabs button, [data-tab]').forEach(b => b.addEventListener('click', () => setTimeout(draw, 60))); }
  split._draw = draw;
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
    if (m.stars) { const f = Math.floor(m.stars), half = m.stars - f >= .5; h('b', {class: 'stars'}, meta, '★'.repeat(f) + (half ? '½' : '') + '☆'.repeat(5 - f - (half ? 1 : 0)) + `  ${m.stars}`); }
    h('span', {class: 'sub'}, meta, `${v.title ? v.title + ' · ' : ''}${v.chars.toLocaleString()}자`);
    if (m.stance_used != null) h('span', {class: 'sub'}, meta, m.stance_used ? '· 내 입장 반영' : '· 내 입장 없이 작성(개인 경험 부분은 빈자리)');
    const ch = $('revChecks'); ch.innerHTML = '';
    if (false && m.checks) { const E = Object.entries(m.checks), ok = E.filter(([, x]) => x.pass).length; const hd = h('div', {class: 'ckHead'}, ch); h('b', {}, hd, '자체 점검'); h('span', {class: 'ckScore' + (ok < E.length ? ' bad' : '')}, hd, `${ok}/${E.length} 통과`); const ul = h('ul', {class: 'ckList'}, ch); E.forEach(([k, x]) => { const li = h('li', {}, ul); h('span', {class: 'ckIco' + (x.pass ? '' : ' no')}, li, x.pass ? '✓' : '✕'); const d = h('div', {}, li); h('div', {class: 'ckName'}, d, k); if (x.note) h('div', {class: 'ckNote'}, d, x.note); }); }
    setHTML($('revBody'), v.html); sectionize($('revBody')); wireAnchors($('revBody'));
  }
  // 장별 흐름
  const fl = $('flow'); fl.innerHTML = '';
  (BK.flow || []).forEach(f => { const li = h('li', {'data-ch': f.id}, fl); const hd = h('div', {class: 'fh'}, li); h('b', {}, hd, f.label); h('span', {class: 'mins'}, hd, `${Math.max(1, Math.round(f.chars / 500))}분`); const sp = h('span', {class: 'ft'}, li); sp.innerHTML = f.text.replace(/`/g, '').replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'})[c]).replace(/\b(p\d{3}(?:-b\d+)?)\b/g, '<span class="anc" data-anc="$1">$1</span>'); wireAnchors(sp); });
  // 핵심 주장
  const cl = $('claims'); cl.innerHTML = ''; $('nClaims').textContent = `${INS.claims.length}개`;
  INS.claims.forEach(c => card(cl, c, null, d => { const n = byClaim[c.id] || []; linkList(d, `이 주장에 대한 반박 ${n.length}개`, n.map(r => ['crit', r.id, r.title, r.strength])); }));
  linkFlowClaims();
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
    if (r.type) m.appendChild(document.createTextNode(`  ·  ${r.type}`)); }, d => { const cm = Object.fromEntries(INS.claims.map(c => [c.id, c])); linkList(d, '반박 대상 주장', r.target.map(t => ['glance', t, (cm[t] || {}).title])); }));
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
function showTab(which) { Object.entries(TABS).forEach(([k, [t, p]]) => { $(t).setAttribute('aria-selected', String(k === which)); $(p).hidden = k !== which; }); $('runSelWrap').style.visibility = which === 'prog' ? 'visible' : 'hidden';
  if (history.replaceState) history.replaceState(null, '', TABS[which][2]); TABS[which][3](); updateStanceBars(); }
Object.entries(TABS).forEach(([k, [t]]) => { $(t).onclick = () => showTab(k); });
renderBookcard();
