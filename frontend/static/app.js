/** PromptForge frontend – v0.2 */

// ── Theme ──────────────────────────────────────────────────────────────────────
const themeBtn = document.getElementById('theme-toggle');
if (localStorage.getItem('theme') === 'dark') document.body.classList.add('dark');
themeBtn.addEventListener('click', () => {
  document.body.classList.toggle('dark');
  localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
  themeBtn.textContent = document.body.classList.contains('dark') ? '☀️' : '🌙';
});

// ── Toast ──────────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Token counter ──────────────────────────────────────────────────────────────
let tokenDebounce = null;
async function updateTokenCount() {
  clearTimeout(tokenDebounce);
  tokenDebounce = setTimeout(async () => {
    const text = document.getElementById('user-message').value;
    const context = document.getElementById('context').value;
    if (!text) { document.getElementById('token-count').textContent = '~0 tokens'; return; }
    try {
      const r = await fetch('/api/estimate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, context: context || null }),
      });
      const d = await r.json();
      document.getElementById('token-count').textContent = `~${d.estimated_tokens} tokens`;
    } catch (_) {}
  }, 300);
}
document.getElementById('user-message').addEventListener('input', updateTokenCount);
document.getElementById('context').addEventListener('input', updateTokenCount);

// ── History sidebar ────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const r = await fetch('/api/history');
    const items = await r.json();
    const list = document.getElementById('history-list');
    list.innerHTML = '';
    if (!items.length) {
      list.innerHTML = '<li style="color:var(--text-muted);font-size:.85rem">No saved runs yet.</li>';
      return;
    }
    items.forEach(item => {
      const li = document.createElement('li');
      const label = item.name || item.id.slice(0, 8) + '…';
      const v = item.version > 1 ? ` v${item.version}` : '';
      li.innerHTML = `<span>${label}${v}</span><span class="score-badge">${item.score ?? '?'}</span>`;
      list.appendChild(li);
    });
  } catch (e) {
    toast('Failed to load history', 'error');
  }
}
document.getElementById('history-toggle').addEventListener('click', async () => {
  const sidebar = document.getElementById('history-sidebar');
  sidebar.classList.toggle('hidden');
  if (!sidebar.classList.contains('hidden')) await loadHistory();
});
document.getElementById('history-close').addEventListener('click', () => {
  document.getElementById('history-sidebar').classList.add('hidden');
});

// ── File upload ─────────────────────────────────────────────────────────────────
document.getElementById('file-upload').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const resp = await fetch('/api/upload', { method: 'POST', body: formData });
    if (!resp.ok) throw new Error(await resp.text());
    const data = await resp.json();
    if (data.context_text) {
      document.getElementById('context').value = data.context_text;
      updateTokenCount();
      toast('Document context loaded ✓', 'success');
    }
  } catch (err) { toast('Upload failed: ' + err.message, 'error'); }
});

// ── Run prompt ──────────────────────────────────────────────────────────────────
let lastRunResult = null;

document.getElementById('run-btn').addEventListener('click', async () => {
  const userMessage = document.getElementById('user-message').value.trim();
  if (!userMessage) { toast('Please enter a prompt.', 'error'); return; }

  const runBtn = document.getElementById('run-btn');
  runBtn.disabled = true;
  runBtn.textContent = 'Running…';

  const payload = {
    role: document.getElementById('role').value,
    tone: document.getElementById('tone').value,
    output_format: document.getElementById('output-format').value,
    context: document.getElementById('context').value || null,
    user_message: userMessage,
    guardrail_config: {
      pii_scan: true, injection_detect: true, token_limit: 4000,
      hallucination_guard: true, pii_output_scan: true, bypass_detect: true, no_code: false,
    },
    provider_config: {
      provider_type: document.getElementById('provider').value,
      model: document.getElementById('model').value,
    },
  };

  try {
    const resp = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw new Error(await resp.text());
    lastRunResult = await resp.json();
    displayResults(lastRunResult);
    document.getElementById('save-btn').disabled = false;
    toast(`Done — score ${lastRunResult.score}/100`, 'success');
  } catch (err) {
    toast('Run failed: ' + err.message, 'error');
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = '▶ Run Prompt';
  }
});

// ── Save ────────────────────────────────────────────────────────────────────────
document.getElementById('save-btn').addEventListener('click', async () => {
  if (!lastRunResult) return;
  const name = document.getElementById('save-name').value.trim() || null;
  try {
    const resp = await fetch('/api/save/local', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ run_result: lastRunResult, name, format: 'json' }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    toast('Saved ✓', 'success');
  } catch (err) { toast('Save failed: ' + err.message, 'error'); }
});

// ── Comment ─────────────────────────────────────────────────────────────────────
document.getElementById('comment-btn').addEventListener('click', async () => {
  if (!lastRunResult) return;
  const text = document.getElementById('comment-text').value.trim();
  if (!text) { toast('Comment cannot be empty', 'error'); return; }
  const author = document.getElementById('comment-author').value.trim() || null;
  try {
    const resp = await fetch(`/api/history/${lastRunResult.id}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, author }),
    });
    if (!resp.ok) throw new Error(await resp.text());
    document.getElementById('comment-text').value = '';
    await loadComments(lastRunResult.id);
    toast('Comment added ✓', 'success');
  } catch (err) { toast('Comment failed: ' + err.message, 'error'); }
});

async function loadComments(runId) {
  try {
    const r = await fetch(`/api/history/${runId}/comments`);
    const comments = await r.json();
    const list = document.getElementById('comment-list');
    list.innerHTML = comments.length
      ? comments.map(c => `<div class="comment-item"><div class="comment-author">${c.author || 'Anonymous'}</div><div>${c.text}</div></div>`).join('')
      : '<div style="font-size:.85rem;color:var(--text-muted);padding:.5rem">No comments yet.</div>';
  } catch (_) {}
}

// ── Display results ─────────────────────────────────────────────────────────────
function displayResults(result) {
  document.getElementById('results').classList.remove('hidden');
  document.getElementById('score-pill').textContent = `${result.score}/100`;

  // Breakdown
  const bd = document.getElementById('score-breakdown');
  bd.innerHTML = (result.score_breakdown || []).map(s =>
    `<div class="breakdown-row ${s.passed ? 'pass' : 'fail'}">
      <span>${s.check.replace(/_/g, ' ')}</span>
      <span>${s.points} pts</span>
    </div>`
  ).join('');

  // Meta
  document.getElementById('meta').textContent =
    `${result.provider} / ${result.model}  ·  ${result.latency_ms}ms  ·  ${result.input_tokens ?? '?'} in / ${result.output_tokens ?? '?'} out tokens`;

  // Violations
  const violations = [...(result.input_violations || []), ...(result.output_violations || [])];
  document.getElementById('violations').innerHTML = violations.length
    ? violations.map(v => `<div class="violation ${v.severity}">[${v.severity.toUpperCase()}] ${v.message}</div>`).join('')
    : '<div class="no-violations">✓ No violations detected</div>';

  // Response
  document.getElementById('response').textContent = result.response;

  // Load comments
  loadComments(result.id);

  // Scroll to results
  document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}
