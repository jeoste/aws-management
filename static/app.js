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
    el.innerHTML = ''; // Clear previous content

    // Create status indicator
    const indicator = document.createElement('div');
    indicator.className = `h-2 w-2 rounded-full mr-2 ${type === 'error' ? 'bg-destructive' : (type === 'success' ? 'bg-green-500' : 'bg-muted-foreground')}`;

    const text = document.createTextNode(msg);

    el.appendChild(indicator);
    el.appendChild(text);

    // Update text color
    el.className = `px-6 py-2 text-xs border-b bg-muted/20 flex items-center ${type === 'error' ? 'text-destructive' : 'text-muted-foreground'}`;
}

async function loadCredentials() {
    try {
        const res = await fetch('/api/credentials');
        const data = await res.json();

        if (data.access_key) document.getElementById('access_key').value = data.access_key;
        if (data.secret_key) document.getElementById('secret_key').value = data.secret_key;
        if (data.session_token) document.getElementById('session_token').value = data.session_token;
        if (data.profile) document.getElementById('profile').value = data.profile;
        if (data.regions) document.getElementById('regions').value = data.regions;
        if (data.remember) document.getElementById('remember').checked = true;
    } catch (e) {
        console.error("Failed to load credentials", e);
    }
}

async function testConnection() {
    const btn = document.getElementById('test-conn-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2" class="mr-2 h-4 w-4 animate-spin"></i> Testing...';
    lucide.createIcons();

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
            setStatus(`Connected: ${result.arn}`, 'success');
        } else {
            setStatus(`Connection failed: ${result.error}`, 'error');
        }
    } catch (e) {
        setStatus(`Connection error: ${e}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
        lucide.createIcons();
    }
}

async function scanResources() {
    const btn = document.getElementById('scan-btn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i data-lucide="loader-2" class="mr-2 h-4 w-4 animate-spin"></i> Scanning...';
    lucide.createIcons();

    const data = {
        access_key: document.getElementById('access_key').value,
        secret_key: document.getElementById('secret_key').value,
        session_token: document.getElementById('session_token').value,
        profile: document.getElementById('profile').value,
        regions: document.getElementById('regions').value,
        remember: document.getElementById('remember').checked
    };

    // Save credentials if remember is checked
    await fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });

    try {
        const res = await fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const inventory = await res.json();

        if (inventory.error) {
            setStatus(`Scan failed: ${inventory.error}`, 'error');
        } else {
            // Flatten inventory
            currentInventory.topics = [];
            currentInventory.queues = [];
            currentInventory.links = [];
            window.rawInventory = inventory; // Store raw for export

            inventory.forEach(regionItem => {
                const r = regionItem.region;
                regionItem.topics.forEach(t => currentInventory.topics.push({ ...t, region: r }));
                regionItem.queues.forEach(q => currentInventory.queues.push({ ...q, region: r }));
                regionItem.links.forEach(l => currentInventory.links.push({ ...l, region: r }));
            });

            updateTables();
            updateDiagram(inventory);
            setStatus(`Scan complete. Found ${currentInventory.topics.length} topics and ${currentInventory.queues.length} queues.`, 'success');
        }
    } catch (e) {
        setStatus(`Scan error: ${e}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
        lucide.createIcons();
    }
}

function updateTables() {
    // Update Counts
    document.getElementById('count-topics').textContent = currentInventory.topics.length;
    document.getElementById('count-queues').textContent = currentInventory.queues.length;
    document.getElementById('count-links').textContent = currentInventory.links.length;

    const rowClass = "border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted";
    const cellClass = "p-4 align-middle [&:has([role=checkbox])]:pr-0";

    // Update Topics
    const topicsBody = document.getElementById('list-topics');
    topicsBody.innerHTML = currentInventory.topics.map(t => {
        const s = currentInventory.stats[t.arn] || {};
        const published = s.published_28d !== undefined ? s.published_28d : '-';
        return `
        <tr class="${rowClass}">
            <td class="${cellClass}">${t.region}</td>
            <td class="${cellClass} font-medium">${t.name}</td>
            <td class="${cellClass} font-mono text-xs text-muted-foreground">${t.arn}</td>
            <td class="${cellClass}">${published}</td>
        </tr>
    `}).join('');

    // Update Queues
    const queuesBody = document.getElementById('list-queues');
    queuesBody.innerHTML = currentInventory.queues.map(q => {
        const s = currentInventory.stats[q.arn] || {};
        const sent = s.numberofmessagessent_28d !== undefined ? s.numberofmessagessent_28d : '-';
        const recv = s.numberofmessagesreceived_28d !== undefined ? s.numberofmessagesreceived_28d : '-';
        return `
        <tr class="${rowClass}">
            <td class="${cellClass}">${q.region}</td>
            <td class="${cellClass} font-medium">${q.name}</td>
            <td class="${cellClass} font-mono text-xs text-muted-foreground truncate max-w-[200px]" title="${q.url}">${q.url}</td>
            <td class="${cellClass}">${sent}</td>
            <td class="${cellClass}">${recv}</td>
        </tr>
    `}).join('');

    // Update Links (Grouped by Topic)
    const linksBody = document.getElementById('list-links');

    // Group links by Topic ARN (or Name + Region)
    const groupedLinks = {};
    currentInventory.links.forEach(l => {
        // Extract topic name from from_arn (format: arn:aws:sns:region:account:TopicName)
        const topicName = l.from_arn ? l.from_arn.split(':').pop() : 'Unknown';
        // Extract queue name from to_arn (format: arn:aws:sqs:region:account:QueueName)
        const queueName = l.to_arn ? l.to_arn.split(':').pop() : 'Unknown';

        const key = `${l.region}|${topicName}`;
        if (!groupedLinks[key]) {
            groupedLinks[key] = {
                region: l.region,
                topic_name: topicName,
                queues: []
            };
        }
        groupedLinks[key].queues.push(queueName);
    });

    linksBody.innerHTML = Object.values(groupedLinks).map(group => `
        <tr class="${rowClass}">
            <td class="${cellClass}">${group.region}</td>
            <td class="${cellClass} font-medium">${group.topic_name}</td>
            <td class="${cellClass}">
                <div class="flex flex-wrap gap-1">
                    ${group.queues.map(q => `
                        <span class="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">
                            ${q}
                        </span>
                    `).join('')}
                </div>
            </td>
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

// Real-time monitoring
let realtimeInterval = null;
let isMonitoring = false;

function toggleRealtime() {
    const button = document.getElementById('realtime-toggle');
    const statusText = document.getElementById('realtime-status');
    const icon = button.querySelector('i');

    if (isMonitoring) {
        // Stop monitoring
        clearInterval(realtimeInterval);
        realtimeInterval = null;
        isMonitoring = false;
        statusText.textContent = 'Start Monitoring';
        icon.setAttribute('data-lucide', 'play');
        lucide.createIcons();
    } else {
        // Start monitoring
        isMonitoring = true;
        statusText.textContent = 'Stop Monitoring';
        icon.setAttribute('data-lucide', 'pause');
        lucide.createIcons();

        // Poll for messages every 2 seconds
        fetchRealtimeMessages();
        realtimeInterval = setInterval(fetchRealtimeMessages, 2000);
    }
}

async function fetchRealtimeMessages() {
    // This is a placeholder - you'll need to implement the backend endpoint
    // For now, we'll simulate some messages
    const log = document.getElementById('realtime-log');

    // Simulate message activity
    const timestamp = new Date().toLocaleTimeString();
    const topics = currentInventory.topics.map(t => t.name);
    const queues = currentInventory.queues.map(q => q.name);

    if (topics.length > 0 && queues.length > 0) {
        const randomTopic = topics[Math.floor(Math.random() * topics.length)];
        const randomQueue = queues[Math.floor(Math.random() * queues.length)];

        const messageHtml = `
            <div class="flex items-start gap-2 p-2 rounded bg-muted/50 border border-border/50">
                <div class="text-muted-foreground">${timestamp}</div>
                <div class="flex-1">
                    <span class="text-primary font-medium">${randomTopic}</span>
                    <i data-lucide="arrow-right" class="inline h-3 w-3 mx-1"></i>
                    <span class="text-secondary font-medium">${randomQueue}</span>
                </div>
            </div>
        `;

        // Remove placeholder if it exists
        const placeholder = log.querySelector('.text-center');
        if (placeholder) {
            log.innerHTML = '';
        }

        // Add new message at the top
        log.insertAdjacentHTML('afterbegin', messageHtml);
        lucide.createIcons();

        // Keep only last 50 messages
        while (log.children.length > 50) {
            log.removeChild(log.lastChild);
        }
    }
}

function clearRealtimeLog() {
    const log = document.getElementById('realtime-log');
    log.innerHTML = `
        <div class="text-muted-foreground text-center py-8">
            Click "Start Monitoring" to begin tracking real-time message exchanges
        </div>
    `;
}
