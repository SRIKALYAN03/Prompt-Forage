/** PromptForge frontend logic */

let lastRunResult = null;

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
        }
    } catch (err) {
        alert('Upload failed: ' + err.message);
    }
});

document.getElementById('run-btn').addEventListener('click', async () => {
    const role = document.getElementById('role').value;
    const tone = document.getElementById('tone').value;
    const outputFormat = document.getElementById('output-format').value;
    const provider = document.getElementById('provider').value;
    const model = document.getElementById('model').value;
    const context = document.getElementById('context').value || null;
    const userMessage = document.getElementById('user-message').value;

    if (!userMessage.trim()) {
        alert('Please enter a message.');
        return;
    }

    const payload = {
        role,
        tone,
        output_format: outputFormat,
        context,
        user_message: userMessage,
        guardrail_config: {
            pii_scan: true,
            injection_detect: true,
            token_limit: 4000,
            hallucination_guard: true,
            pii_output_scan: true,
            bypass_detect: true,
            no_code: false,
        },
        provider_config: {
            provider_type: provider,
            model,
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
    } catch (err) {
        alert('Run failed: ' + err.message);
    }
});

document.getElementById('save-btn').addEventListener('click', async () => {
    if (!lastRunResult) return;

    try {
        const resp = await fetch('/api/save/local', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ run_result: lastRunResult, format: 'json' }),
        });
        if (!resp.ok) throw new Error(await resp.text());
        const data = await resp.json();
        alert('Saved to: ' + data.path);
    } catch (err) {
        alert('Save failed: ' + err.message);
    }
});

function displayResults(result) {
    document.getElementById('results').classList.remove('hidden');
    document.getElementById('score').textContent = 'Score: ' + result.score + '/100';
    document.getElementById('response').textContent = result.response;

    const violations = [
        ...(result.input_violations || []),
        ...(result.output_violations || []),
    ];
    const violEl = document.getElementById('violations');
    if (violations.length) {
        violEl.innerHTML = '<h3>Violations</h3>' + violations.map(v =>
            `<p>[${v.severity}] ${v.message}</p>`
        ).join('');
    } else {
        violEl.innerHTML = '';
    }
}
