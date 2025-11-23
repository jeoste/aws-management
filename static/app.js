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

function switchTab(tabName) {
    // Hide all contents
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.add('hidden');
    });
    // Show target
    const target = document.getElementById(`tab-${tabName}`);
    if (target) target.classList.remove('hidden');

    // Update buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        // Reset to inactive state
        btn.classList.remove('bg-background', 'text-foreground', 'shadow-sm');
        btn.classList.add('hover:text-foreground');

        if (btn.dataset.tab === tabName) {
            // Set active state
            btn.classList.add('bg-background', 'text-foreground', 'shadow-sm');
            btn.classList.remove('hover:text-foreground');
        }
    });
}

// ... existing code ...

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
        const key = `${l.region}|${l.topic_name}`;
        if (!groupedLinks[key]) {
            groupedLinks[key] = {
                region: l.region,
                topic_name: l.topic_name,
                queues: []
            };
        }
        groupedLinks[key].queues.push(l.queue_name);
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
