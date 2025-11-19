document.addEventListener('DOMContentLoaded', () => {
    loadCredentials();

    document.getElementById('test-conn-btn').addEventListener('click', testConnection);
    document.getElementById('scan-btn').addEventListener('click', scanResources);
    document.getElementById('stats-btn').addEventListener('click', fetchStatistics);
});

// State
let currentInventory = {
    topics: [],
    queues: [],
    links: [],
    stats: {} // arn -> stats object
};

// UI Helpers
function setStatus(msg, type = 'normal') {
    const el = document.getElementById('status-bar');
    el.textContent = msg;
    el.style.color = type === 'error' ? 'var(--error)' : (type === 'success' ? 'var(--success)' : 'var(--text-secondary)');
}

function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

    // Find button by onclick attribute content is a bit hacky but works for simple app
    const btns = Array.from(document.querySelectorAll('.tab-btn'));
    const btn = btns.find(b => b.getAttribute('onclick').includes(tabName));
    if (btn) btn.classList.add('active');

    document.getElementById(`tab-${tabName}`).classList.add('active');
}

// API Calls
async function loadCredentials() {
    try {
        const res = await fetch('/api/credentials');
        const data = await res.json();

        if (data.access_key) document.getElementById('access_key').value = data.access_key;
        if (data.secret_key) document.getElementById('secret_key').value = data.secret_key;
        if (data.session_token) document.getElementById('session_token').value = data.session_token;
        if (data.profile) document.getElementById('profile').value = data.profile;
        if (data.regions) document.getElementById('regions').value = data.regions;
        document.getElementById('remember').checked = data.remember;
    } catch (e) {
        console.error("Failed to load credentials", e);
    }
}

async function saveCredentials() {
    const data = {
        access_key: document.getElementById('access_key').value,
        secret_key: document.getElementById('secret_key').value,
        session_token: document.getElementById('session_token').value,
        profile: document.getElementById('profile').value,
        regions: document.getElementById('regions').value,
        remember: document.getElementById('remember').checked
    };

    await fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
}

async function testConnection() {
    setStatus('Testing connection...');
    await saveCredentials();

    const data = {
        access_key: document.getElementById('access_key').value,
        secret_key: document.getElementById('secret_key').value,
        session_token: document.getElementById('session_token').value,
        profile: document.getElementById('profile').value
    };

    try {
        const res = await fetch('/api/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();

        if (result.success) {
            setStatus(`Connected: ${result.account} (${result.arn})`, 'success');
        } else {
            setStatus(`Connection failed: ${result.error}`, 'error');
        }
    } catch (e) {
        setStatus(`Network error: ${e}`, 'error');
    }
}

async function scanResources() {
    setStatus('Scanning resources...');
    await saveCredentials();

    const data = {
        access_key: document.getElementById('access_key').value,
        secret_key: document.getElementById('secret_key').value,
        session_token: document.getElementById('session_token').value,
        profile: document.getElementById('profile').value,
        regions: document.getElementById('regions').value
    };

    try {
        const res = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const inventory = await res.json();

        if (inventory.error) {
            setStatus(`Scan failed: ${inventory.error}`, 'error');
            return;
        }

        processInventory(inventory);
        setStatus(`Scan complete. Found ${currentInventory.topics.length} topics, ${currentInventory.queues.length} queues.`, 'success');
    } catch (e) {
        setStatus(`Scan error: ${e}`, 'error');
    }
}

function processInventory(inventoryList) {
    currentInventory = { topics: [], queues: [], links: [], stats: {} };

    inventoryList.forEach(regionData => {
        const r = regionData.region;

        regionData.topics.forEach(t => {
            currentInventory.topics.push({ ...t, region: r });
        });

        regionData.queues.forEach(q => {
            currentInventory.queues.push({ ...q, region: r });
        });

        regionData.links.forEach(l => {
            // Resolve names
            const topic = regionData.topics.find(t => t.arn === l.from_arn);
            const queue = regionData.queues.find(q => q.arn === l.to_arn);

            currentInventory.links.push({
                ...l,
                region: r,
                topic_name: topic ? topic.name : l.from_arn,
                queue_name: queue ? queue.name : l.to_arn
            });
        });
    });

    updateTables();
    updateDiagram(inventoryList);

    // Save for export
    window.rawInventory = inventoryList;
}

function updateTables() {
    // Update Counts
    document.getElementById('count-topics').textContent = currentInventory.topics.length;
    document.getElementById('count-queues').textContent = currentInventory.queues.length;
    document.getElementById('count-links').textContent = currentInventory.links.length;

    // Update Topics
    const topicsBody = document.getElementById('list-topics');
    topicsBody.innerHTML = currentInventory.topics.map(t => {
        const s = currentInventory.stats[t.arn] || {};
        const published = s.published_28d !== undefined ? s.published_28d : '-';
        return `
        <tr>
            <td>${t.region}</td>
            <td>${t.name}</td>
            <td class="mono">${t.arn}</td>
            <td>${published}</td>
        </tr>
    `}).join('');

    // Update Queues
    const queuesBody = document.getElementById('list-queues');
    queuesBody.innerHTML = currentInventory.queues.map(q => {
        const s = currentInventory.stats[q.arn] || {};
        const sent = s.numberofmessagessent_28d !== undefined ? s.numberofmessagessent_28d : '-';
        const recv = s.numberofmessagesreceived_28d !== undefined ? s.numberofmessagesreceived_28d : '-';
        return `
        <tr>
            <td>${q.region}</td>
            <td>${q.name}</td>
            <td class="mono">${q.url}</td>
            <td>${sent}</td>
            <td>${recv}</td>
        </tr>
    `}).join('');

    // Update Links
    const linksBody = document.getElementById('list-links');
    linksBody.innerHTML = currentInventory.links.map(l => `
        <tr>
            <td>${l.region}</td>
            <td>${l.topic_name}</td>
            <td>${l.queue_name}</td>
        </tr>
    `).join('');
}

async function updateDiagram(inventoryList) {
    try {
        const res = await fetch('/api/export/mermaid', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inventoryList)
        });
        const data = await res.json();

        const mermaidDiv = document.getElementById('mermaid-graph');
        mermaidDiv.innerHTML = data.content;
        mermaidDiv.removeAttribute('data-processed');

        mermaid.init(undefined, mermaidDiv);
    } catch (e) {
        console.error("Mermaid generation failed", e);
    }
}

async function exportData(format) {
    if (currentInventory.topics.length === 0 && currentInventory.queues.length === 0) {
        alert("No data to export. Please scan first.");
        return;
    }

    if (format === 'json') {
        downloadFile('inventory.json', JSON.stringify(currentInventory, null, 2));
    } else if (format === 'mermaid') {
        alert("Please use the 'Export JSON' to get the data, or copy the diagram text.");
    } else if (format === 'sql') {
        if (!window.rawInventory) {
            alert("No data.");
            return;
        }
        const res = await fetch('/api/export/sql', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(window.rawInventory)
        });
        const data = await res.json();
        downloadFile('inventory.sql', data.content);
    } else if (format === 'drawio') {
        if (!window.rawInventory) {
            alert("No data.");
            return;
        }
        const res = await fetch('/api/export/drawio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(window.rawInventory)
        });
        const data = await res.json();
        downloadFile('inventory.drawio', data.content);
    }
}

async function fetchStatistics() {
    if (currentInventory.topics.length === 0 && currentInventory.queues.length === 0) {
        setStatus("Scan resources first.", "error");
        return;
    }

    setStatus('Fetching CloudWatch metrics (last 28 days)...');

    // Prepare items list
    const items = [];
    currentInventory.topics.forEach(t => items.push({ arn: t.arn, name: t.name, region: t.region, type: 'topic' }));
    currentInventory.queues.forEach(q => items.push({ arn: q.arn, name: q.name, region: q.region, type: 'queue' }));

    const data = {
        access_key: document.getElementById('access_key').value,
        secret_key: document.getElementById('secret_key').value,
        session_token: document.getElementById('session_token').value,
        profile: document.getElementById('profile').value,
        items: items
    };

    try {
        const res = await fetch('/api/stats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const stats = await res.json();

        if (stats.error) {
            setStatus(`Stats failed: ${stats.error}`, 'error');
            return;
        }

        currentInventory.stats = stats;
        updateTables();
        setStatus('Statistics updated.', 'success');
    } catch (e) {
        setStatus(`Stats error: ${e}`, 'error');
    }
}

function downloadFile(filename, content) {
    const element = document.createElement('a');
    element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content));
    element.setAttribute('download', filename);
    element.style.display = 'none';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}
