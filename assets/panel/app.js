'use strict';

/* ==========================================================================
   REA Panel 手机端 — 界面逻辑
   通过 fetch 调用电脑上的 HTTP 服务，完整对齐 153 个命令
   ========================================================================== */

const S = {
  base: '',            // 服务器地址，如 http://192.168.1.5:8788
  token: '',
  commands: [],
  filtered: [],
  active: null,
  schema: null,
  lastResult: null,
  view: 'json',
  running: false
};

const $ = (id) => document.getElementById(id);
const E = {
  connDot: $('connDot'), btnCfg: $('btnCfg'), btnBack: $('btnBack'),
  scrConfig: $('scrConfig'), scrList: $('scrList'), scrDetail: $('scrDetail'), scrResult: $('scrResult'),
  inpUrl: $('inpUrl'), inpToken: $('inpToken'), btnConnect: $('btnConnect'), cfgStatus: $('cfgStatus'),
  cmdSearch: $('cmdSearch'), cmdList: $('cmdList'), listCount: $('listCount'), btnReload: $('btnReload'),
  detName: $('detName'), detSummary: $('detSummary'), detCmdline: $('detCmdline'),
  argForm: $('argForm'), btnRun: $('btnRun'), btnStop: $('btnStop'),
  resBadge: $('resBadge'), resBody: $('resBody'), btnCopy: $('btnCopy'), btnAgain: $('btnAgain'),
  tabbar: $('tabbar'), toast: $('toast')
};

const GROUPS = [
  ['总览 / 能力', (n) => ['analyze', 'capabilities', 'doctor', 'compare'].includes(n)],
  ['JS / Electron', (n) => /javascript|electron|web-bundle|web-capture|web-screenshot|wasm/.test(n)],
  ['Android / ADB', (n) => /adb|android|apk/.test(n)],
  ['原生 / 二进制', (n) => /native|binary|file-offset|annotate|managed|process|cutter|gdb|objdump|macho|plist|signature|demangle|architecture|dispatch/.test(n)],
  ['浏览器', (n) => /browser|playwright|page|origin|screenshot/.test(n)],
  ['比对 / 差分', (n) => /^compare/.test(n)],
  ['其他', () => true]
];
const groupOf = (n) => (GROUPS.find((g) => g[1](n)) || GROUPS[GROUPS.length - 1])[0];

// ---- 工具 -----------------------------------------------------------------

function toast(msg, ms = 1800) {
  E.toast.textContent = msg;
  E.toast.classList.remove('hidden');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => E.toast.classList.add('hidden'), ms);
}

function show(screenId) {
  ['scrConfig', 'scrList', 'scrDetail', 'scrResult'].forEach((s) => {
    E[s].classList.toggle('active', s === screenId);
  });
  document.querySelectorAll('.tab').forEach((t) => {
    t.classList.toggle('active', t.dataset.tab === screenId);
  });
  E.btnBack.classList.toggle('hidden', screenId === 'scrConfig' || screenId === 'scrList');
}

function setDot(state) {
  E.connDot.className = 'dot ' + state;
}

async function api(path, opts = {}, timeoutMs = 60000) {
  if (!S.base) throw new Error('未配置服务器地址');
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    if (S.token) headers['X-REA-TOKEN'] = S.token;
    const res = await fetch(S.base + path, Object.assign({}, opts, { headers, signal: ctrl.signal }));
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch (_) { throw new Error('返回非 JSON: ' + text.slice(0, 120)); }
    return data;
  } finally {
    clearTimeout(timer);
  }
}

// ---- 连接管理 -------------------------------------------------------------

async function connect(silent) {
  const url = E.inpUrl.value.trim().replace(/\/+$/, '');
  if (!url) { if (!silent) toast('请填写服务器地址'); return false; }
  if (!/^https?:\/\//i.test(url)) { if (!silent) toast('地址需以 http:// 开头'); return false; }

  S.base = url;
  S.token = E.inpToken.value.trim();
  setDot('wait');
  E.cfgStatus.className = 'cfg-status wait';
  E.cfgStatus.textContent = '连接中…';

  try {
    const ping = await api('/api/ping', {}, 8000);
    if (!ping.ok) throw new Error('服务未就绪');
    setDot('on');
    E.cfgStatus.className = 'cfg-status ok';
    E.cfgStatus.textContent = '✓ 连接成功';

    try {
      const env = await api('/api/env', {}, 8000);
      E.cfgStatus.textContent = `✓ 已连接 · rea 环境: ${env.kind}`;
    } catch (_) { /* 忽略 */ }

    saveConfig();
    toast('已连接');
    loadCommands();
    setTimeout(() => show('scrList'), 300);
    return true;
  } catch (e) {
    setDot('off');
    const msg = (e && e.name === 'AbortError') ? '连接超时，检查地址与防火墙' : (e.message || String(e));
    E.cfgStatus.className = 'cfg-status err';
    E.cfgStatus.textContent = '✗ ' + msg;
    if (!silent) toast('连接失败');
    return false;
  }
}

function saveConfig() {
  try {
    localStorage.setItem('rea_url', S.base);
    localStorage.setItem('rea_token', S.token);
  } catch (_) { /* WebView 可能禁用 storage */ }
}

function loadConfig() {
  // 优先用原生注入的 ?saved=
  const q = new URLSearchParams(location.search);
  const injected = q.get('saved') || '';
  let url = injected, token = '';
  try {
    url = url || localStorage.getItem('rea_url') || '';
    token = localStorage.getItem('rea_token') || '';
  } catch (_) { /* ignore */ }
  E.inpUrl.value = url || '';
  E.inpToken.value = token || '';
}

// ---- 命令索引 -------------------------------------------------------------

async function loadCommands() {
  if (!S.base) return;
  E.listCount.textContent = '加载中…';
  try {
    const d = await api('/api/commands', {}, 30000);
    S.commands = d.commands || [];
    S.filtered = S.commands.slice();
    E.listCount.textContent = `${S.commands.length} 个命令`;
    renderList();
    setDot('on');
  } catch (e) {
    E.listCount.textContent = '加载失败';
    setDot('off');
    toast('命令加载失败: ' + (e.message || e), 2500);
  }
}

function renderList() {
  const kw = E.cmdSearch.value.trim().toLowerCase();
  const items = kw
    ? S.filtered.filter((c) => c.name.toLowerCase().includes(kw) || c.summary.toLowerCase().includes(kw))
    : S.filtered;

  if (!items.length) {
    E.cmdList.innerHTML = '<div class="empty">无匹配命令</div>';
    return;
  }

  const buckets = new Map();
  for (const c of items) {
    const g = groupOf(c.name);
    if (!buckets.has(g)) buckets.set(g, []);
    buckets.get(g).push(c);
  }

  const html = [];
  for (const [label, fn] of GROUPS) {
    const arr = buckets.get(label);
    if (!arr) continue;
    html.push(`<div class="grp-head">${label} (${arr.length})</div>`);
    for (const c of arr) {
      html.push(
        `<div class="cmd-row" data-cmd="${c.name}">
           <span class="cname">${c.name}</span>
           <span class="csum">${c.summary}</span>
         </div>`
      );
    }
  }
  E.cmdList.innerHTML = html.join('');
  E.cmdList.querySelectorAll('.cmd-row').forEach((row) => {
    row.addEventListener('click', () => openCommand(row.dataset.cmd));
  });
}

// ---- 命令详情 / Schema 表单 -----------------------------------------------

async function openCommand(name) {
  S.active = name;
  S.schema = null;
  S.lastResult = null;
  const meta = S.commands.find((c) => c.name === name);
  E.detName.textContent = name;
  E.detSummary.textContent = meta ? meta.summary : '';
  E.detCmdline.textContent = '加载参数…';
  E.argForm.innerHTML = '<div class="empty">加载中…</div>';
  E.btnRun.disabled = true;
  show('scrDetail');

  try {
    const d = await api('/api/schema?cmd=' + encodeURIComponent(name), {}, 20000);
    S.schema = d.schema || {};
    buildForm();
    E.btnRun.disabled = false;
    updateCmdline();
  } catch (e) {
    E.argForm.innerHTML = `<div class="empty">参数加载失败：${esc(e.message || e)}<br>仍可直接运行</div>`;
    E.btnRun.disabled = false;
    updateCmdline();
  }
}

function buildForm() {
  const sch = S.schema || {};
  if (sch.error) {
    E.argForm.innerHTML = `<div class="empty">该命令无参数定义，可直接运行</div>`;
    return;
  }
  const args = sch.args || {};
  const opts = sch.options || {};
  const aProps = args.properties || {};
  const oProps = opts.properties || {};
  const required = args.required || [];

  const html = [];

  const aKeys = Object.keys(aProps);
  if (aKeys.length) {
    html.push('<div class="sec"><div class="sec-title">位置参数</div>');
    for (const k of aKeys) html.push(fieldHtml(k, aProps[k], required.includes(k), 'arg'));
    html.push('</div>');
  }

  const oKeys = Object.keys(oProps);
  if (oKeys.length) {
    html.push(`<div class="sec"><div class="sec-title">选项参数（${oKeys.length}）</div>`);
    for (const k of oKeys) html.push(fieldHtml(k, oProps[k], false, 'opt'));
    html.push('</div>');
  }

  if (!aKeys.length && !oKeys.length) {
    html.push('<div class="empty">该命令无参数，可直接运行</div>');
  }

  E.argForm.innerHTML = html.join('');
  E.argForm.querySelectorAll('[data-fk]').forEach((el) => {
    el.addEventListener('input', updateCmdline);
    el.addEventListener('change', updateCmdline);
  });
}

function fieldHtml(key, spec, isReq, kind) {
  const type = spec.type || 'string';
  const desc = spec.description ? `<div class="fdesc">${esc(spec.description)}</div>` : '';
  const t = spec.enum ? 'enum' : type;

  // 布尔 → 复选
  if (type === 'boolean') {
    return `<div class="field"><div class="chk-row">
      <input type="checkbox" data-fk="${key}" data-kind="${kind}" data-ftype="boolean" id="c_${key}">
      <label for="c_${key}">${key}<span class="ftype">flag</span></label>
    </div>${desc}</div>`;
  }

  const label = `${isReq ? '<span class="req">*</span>' : ''}${key}<span class="ftype">${t}</span>`;

  let ctrl;
  if (spec.enum) {
    const opts = ['<option value="">— 未设置 —</option>']
      .concat(spec.enum.map((v) => `<option value="${esc(String(v))}">${esc(String(v))}</option>`));
    ctrl = `<select data-fk="${key}" data-kind="${kind}" data-ftype="enum">${opts.join('')}</select>`;
  } else if (type === 'array' || /json/i.test(key)) {
    ctrl = `<textarea data-fk="${key}" data-kind="${kind}" data-ftype="array"
              placeholder='JSON 数组，如 ["a","b"]'></textarea>`;
  } else if (type === 'integer' || type === 'number') {
    ctrl = `<input type="number" class="inp" data-fk="${key}" data-kind="${kind}" data-ftype="${type}">`;
  } else {
    const ph = /path|file|dir|snapshot|jar|exe|apk|db/i.test(key) ? '绝对路径' : key;
    ctrl = `<input type="text" class="inp" data-fk="${key}" data-kind="${kind}" data-ftype="string"
             placeholder="${esc(ph)}" autocomplete="off" autocorrect="off" spellcheck="false">`;
  }

  return `<div class="field"><label>${label}</label>${ctrl}${desc}</div>`;
}

// ---- 参数收集 -------------------------------------------------------------

function collectArgs(strict) {
  const out = [];
  const opts = [];
  let missing = null;

  E.argForm.querySelectorAll('[data-fk]').forEach((el) => {
    const key = el.dataset.fk;
    const kind = el.dataset.kind;
    const ftype = el.dataset.ftype;

    if (ftype === 'boolean') {
      if (el.checked) opts.push([key, null]);
      return;
    }

    const val = (el.value || '').trim();
    if (!val) {
      if (strict && kind === 'arg' && !missing) missing = key;
      return;
    }

    if (ftype === 'array') {
      try {
        const arr = JSON.parse(val);
        if (Array.isArray(arr)) { arr.forEach((v) => opts.push([key, String(v)])); return; }
      } catch (_) { /* 退化为单值 */ }
      opts.push([key, val]);
      return;
    }

    if (kind === 'arg') out.push(val);
    else opts.push([key, val]);
  });

  if (missing) throw new Error('必填参数未填写：' + missing);

  for (const [k, v] of opts) {
    out.push('--' + k);
    if (v !== null) out.push(v);
  }
  return out;
}

function updateCmdline() {
  if (!S.active) return;
  try {
    const a = collectArgs(false);
    E.detCmdline.textContent = 'rea ' + [S.active].concat(a).join(' ');
  } catch (_) {
    E.detCmdline.textContent = 'rea ' + S.active;
  }
}

// ---- 执行 -----------------------------------------------------------------

async function runCommand() {
  if (!S.active || S.running) return;
  let args;
  try {
    args = [S.active].concat(collectArgs(true));
  } catch (e) {
    toast(e.message);
    return;
  }

  S.running = true;
  E.btnRun.classList.add('hidden');
  E.btnStop.classList.remove('hidden');
  show('scrResult');
  E.resBadge.className = 'badge';
  E.resBadge.textContent = '运行中…';
  E.resBody.textContent = '▌执行中，请稍候…';

  try {
    const r = await api('/api/run', {
      method: 'POST',
      body: JSON.stringify({ args })
    }, 180000);

    S.lastResult = r;
    const code = r.code;

    if (r.error) {
      E.resBadge.className = 'badge err';
      E.resBadge.textContent = '错误';
    } else if (code === 0) {
      E.resBadge.className = 'badge ok';
      E.resBadge.textContent = `退出码 0 · ${r.ms || 0}ms`;
    } else {
      E.resBadge.className = 'badge err';
      E.resBadge.textContent = `退出码 ${code} · ${r.ms || 0}ms`;
    }
    renderResult();
    toast(code === 0 ? '执行完成' : `退出码 ${code}`);
  } catch (e) {
    E.resBadge.className = 'badge err';
    E.resBadge.textContent = '失败';
    E.resBody.textContent = '请求失败：' + (e.message || e);
    setDot('off');
    toast('执行失败');
  } finally {
    S.running = false;
    E.btnRun.classList.remove('hidden');
    E.btnStop.classList.add('hidden');
  }
}

function renderResult() {
  if (!S.lastResult) return;
  const r = S.lastResult;
  const raw = (r.stdout || '') + (r.stderr ? '\n--- stderr ---\n' + r.stderr : '');

  if (S.view === 'raw') {
    E.resBody.textContent = raw;
    return;
  }

  const parsed = tryJson(r.stdout);
  if (parsed !== null) {
    E.resBody.innerHTML = renderJson(parsed, 0);
    bindFolds();
  } else {
    E.resBody.textContent = raw;
  }
}

function tryJson(s) {
  if (!s) return null;
  const t = s.trim();
  if (!t || (t[0] !== '{' && t[0] !== '[')) return null;
  try { return JSON.parse(t); } catch (_) { return null; }
}

function renderJson(v, depth) {
  if (v === null) return '<span class="jnull">null</span>';
  const t = typeof v;
  if (t === 'string') return `<span class="jstr">${esc(JSON.stringify(v))}</span>`;
  if (t === 'number') return `<span class="jnum">${v}</span>`;
  if (t === 'boolean') return `<span class="jbool">${v}</span>`;

  if (Array.isArray(v)) {
    if (!v.length) return '<span class="jnull">[]</span>';
    const open = depth < 2;
    const id = 'f' + Math.random().toString(36).slice(2, 8);
    const rows = v.map((x, i) =>
      `<div class="jrow"><span class="jkey">${i}: </span>${renderJson(x, depth + 1)}</div>`
    ).join('');
    return `<div><span class="jfold" data-fold="${id}">${open ? '▾' : '▸'} Array(${v.length})</span>
      <div class="jbody" id="${id}" ${open ? '' : 'style="display:none"'}>${rows}</div></div>`;
  }

  const keys = Object.keys(v);
  if (!keys.length) return '<span class="jnull">{}</span>';
  const open = depth < 2;
  const id = 'f' + Math.random().toString(36).slice(2, 8);
  const rows = keys.map((k) =>
    `<div class="jrow"><span class="jkey">${esc(k)}: </span>${renderJson(v[k], depth + 1)}</div>`
  ).join('');
  return `<div><span class="jfold" data-fold="${id}">${open ? '▾' : '▸'} {${keys.length}}</span>
    <div class="jbody" id="${id}" ${open ? '' : 'style="display:none"'}>${rows}</div></div>`;
}

function bindFolds() {
  E.resBody.querySelectorAll('[data-fold]').forEach((el) => {
    el.addEventListener('click', () => {
      const body = document.getElementById(el.dataset.fold);
      if (!body) return;
      const open = body.style.display !== 'none';
      body.style.display = open ? 'none' : 'block';
      el.textContent = el.textContent.replace(open ? '▾' : '▸', open ? '▸' : '▾');
    });
  });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

// ---- 事件绑定 -------------------------------------------------------------

function bind() {
  E.btnConnect.addEventListener('click', () => connect(false));
  E.inpUrl.addEventListener('keydown', (e) => { if (e.key === 'Enter') connect(false); });
  E.btnCfg.addEventListener('click', () => show('scrConfig'));
  E.btnBack.addEventListener('click', () => show('scrList'));
  E.btnReload.addEventListener('click', loadCommands);
  E.cmdSearch.addEventListener('input', renderList);
  E.btnRun.addEventListener('click', runCommand);
  E.btnStop.addEventListener('click', () => {
    toast('手机端暂不支持中断，可在电脑端停止');
  });
  E.btnAgain.addEventListener('click', runCommand);
  E.btnCopy.addEventListener('click', async () => {
    if (!S.lastResult) return;
    const txt = (S.lastResult.stdout || '') +
      (S.lastResult.stderr ? '\n--- stderr ---\n' + S.lastResult.stderr : '');
    try {
      await navigator.clipboard.writeText(txt);
      toast('已复制');
    } catch (_) {
      // WebView 剪贴板兜底
      const ta = document.createElement('textarea');
      ta.value = txt;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      toast('已复制');
    }
  });

  E.tabbar.querySelectorAll('.tab').forEach((t) => {
    t.addEventListener('click', () => {
      const id = t.dataset.tab;
      if (id === 'scrDetail' && !S.active) { toast('先选一个命令'); return; }
      if (id === 'scrResult' && !S.lastResult) { toast('还没有结果'); return; }
      show(id);
    });
  });

  document.querySelectorAll('.vs-btn').forEach((b) => {
    b.addEventListener('click', () => {
      document.querySelectorAll('.vs-btn').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      S.view = b.dataset.v;
      renderResult();
    });
  });
}

// ---- 启动 -----------------------------------------------------------------

function boot() {
  loadConfig();
  bind();

  if (E.inpUrl.value) {
    connect(true);  // 静默自动重连
  } else {
    setDot('off');
    show('scrConfig');
  }
}

document.addEventListener('DOMContentLoaded', boot);
