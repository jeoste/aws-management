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

// Helper to set the icon inside the realtime toggle button safely.
function setToggleIcon(button, name) {
    if (!button) return;
    // Try to find an element that lucide recognizes or an existing svg
    let iconEl = button.querySelector('[data-lucide]') || button.querySelector('svg');
    if (iconEl) {
        try {
            // update data-lucide attribute if possible
            iconEl.setAttribute('data-lucide', name);
        } catch (e) {
            // ignore
        }
    } else {
        // Insert an <i> with data-lucide before the status span
        const statusSpan = button.querySelector('#realtime-status') || button.querySelector('span');
        const i = document.createElement('i');
        i.setAttribute('data-lucide', name);
        i.className = 'mr-2 h-4 w-4';
        if (statusSpan && statusSpan.parentNode === button) {
            button.insertBefore(i, statusSpan);
        } else {
            button.prepend(i);
        }
    }
    try { lucide.createIcons(); } catch (e) {}
}

// Utility to escape HTML in message bodies
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe.replace(/[&<"'`=\/]/g, function (s) {
        return ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
            '`': '&#96;',
            '=': '&#61;',
            '/': '&#47;'
        })[s];
    });
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

    updateRealtimeQueueList();
}

function updateRealtimeQueueList() {
    const container = document.getElementById('realtime-queue-list');
    if (!container) return;

    if (currentInventory.queues.length === 0) {
        container.innerHTML = '<div class="text-xs text-muted-foreground">Scan resources first to see available queues</div>';
        return;
    }

    container.innerHTML = '';
    currentInventory.queues.forEach(queue => {
        const label = document.createElement('label');
        label.className = 'flex items-center gap-2 px-2 py-1 rounded hover:bg-accent cursor-pointer transition-colors';
        label.title = queue.url || queue.name;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = queue.arn;
        checkbox.dataset.name = queue.name;
        checkbox.className = 'h-4 w-4 rounded border-primary';
        checkbox.checked = false; // not selected by default

        const span = document.createElement('span');
        span.className = 'text-sm';
        span.textContent = queue.name;

        label.appendChild(checkbox);
        label.appendChild(span);
        container.appendChild(label);
    });
}

function selectAllTopics() {
    document.querySelectorAll('#realtime-topic-list input[type="checkbox"]').forEach(cb => cb.checked = true);
}

function deselectAllTopics() {
    document.querySelectorAll('#realtime-topic-list input[type="checkbox"]').forEach(cb => cb.checked = false);
}

function selectAllQueues() {
    document.querySelectorAll('#realtime-queue-list input[type="checkbox"]').forEach(cb => cb.checked = true);
}

function deselectAllQueues() {
    document.querySelectorAll('#realtime-queue-list input[type="checkbox"]').forEach(cb => cb.checked = false);
}

function filterQueues() {
    const q = document.getElementById('realtime-queue-filter');
    const term = (q.value || '').toLowerCase().trim();
    const container = document.getElementById('realtime-queue-list');
    if (!container) return;
    Array.from(container.children).forEach(label => {
        const text = (label.textContent || '').toLowerCase();
        if (!term || text.includes(term)) {
            label.style.display = '';
        } else {
            label.style.display = 'none';
        }
    });
}

function getSelectedQueues() {
    const checkboxes = document.querySelectorAll('#realtime-queue-list input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function getSelectedTopics() {
    const checkboxes = document.querySelectorAll('#realtime-topic-list input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
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
        items: items,
        // Request the server to attempt peeking SQS messages (non-destructive when possible)
        fetch_messages: true
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
let lastPollTime = null;
let pollCount = 0;

function toggleRealtime() {
    const button = document.getElementById('realtime-toggle');
    const statusText = document.getElementById('realtime-status');

    if (isMonitoring) {
        // Stop monitoring
        clearInterval(realtimeInterval);
        realtimeInterval = null;
        isMonitoring = false;
        pollCount = 0;
        lastPollTime = null;
    statusText.textContent = 'Start Monitoring';
    setToggleIcon(button, 'play');
        // Switch button color back to primary (blue)
        try {
            button.classList.remove('bg-destructive', 'text-destructive-foreground');
            button.classList.add('bg-primary', 'text-primary-foreground');
        } catch (e) {
            // ignore
        }
        // also set explicit inline color to ensure visual change
        button.style.backgroundColor = 'rgb(2 132 199)'; // blue
        button.style.color = '#ffffff';
        lucide.createIcons();
    } else {
        // Start monitoring
        isMonitoring = true;
    statusText.textContent = 'Stop Monitoring';
    setToggleIcon(button, 'pause');
        // Switch button color to destructive (red)
        try {
            button.classList.remove('bg-primary', 'text-primary-foreground');
            button.classList.add('bg-destructive', 'text-destructive-foreground');
        } catch (e) {
            // ignore
        }
        // explicit inline color to ensure visible change
        button.style.backgroundColor = 'rgb(239 68 68)'; // red
        button.style.color = '#ffffff';
        lucide.createIcons();

        // Reset counters
        lastPollTime = new Date();
        pollCount = 0;
        
        // Poll for messages every 3 seconds (adjusted to match backend 5s long-polling)
        fetchRealtimeMessages();
        realtimeInterval = setInterval(fetchRealtimeMessages, 3000);
    }
}

async function fetchRealtimeMessages() {
    const log = document.getElementById('realtime-log');
    try {
        console.debug('fetchRealtimeMessages called');
    } catch (e) {}

    try {

    // Check if we have scanned resources
    if (currentInventory.topics.length === 0 && currentInventory.queues.length === 0) {
        log.innerHTML = `
            <div class="text-muted-foreground text-center py-8">
                Please scan resources first before monitoring
            </div>
        `;
        return;
    }

    // Prepare items list for monitoring
    const selectedQueueArns = getSelectedQueues();

    if (selectedQueueArns.length === 0) {
        log.innerHTML = `
            <div class="text-muted-foreground text-center py-8">
                <div class="text-2xl mb-2">🔍</div>
                <div class="font-semibold mb-2">Aucune ressource sélectionnée</div>
                <div class="text-xs">Sélectionnez au moins une queue pour commencer la surveillance</div>
            </div>
        `;
        return;
    }

    const items = [];

    // Only monitor queues explicitly selected
    currentInventory.queues.forEach(q => {
        if (selectedQueueArns.includes(q.arn)) {
            items.push({ arn: q.arn, name: q.name, region: q.region, type: 'queue' });
        }
    });

    const data = {
        access_key: document.getElementById('access_key').value,
        secret_key: document.getElementById('secret_key').value,
        session_token: document.getElementById('session_token').value,
        profile: document.getElementById('profile').value,
        items: items,
        fetch_messages: true
    };

    try {
        const res = await fetch('/api/monitor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const messages = await res.json();

        if (messages.error) {
            console.error('Monitoring error:', messages.error);
            return;
        }

        // Remove placeholder if it exists
        const placeholder = log.querySelector('.text-center');
        if (placeholder) {
            log.innerHTML = '';
        }

        // Display new messages
        if (messages.length > 0) {
            messages.forEach(msg => {
                const timestamp = new Date(msg.timestamp).toLocaleTimeString();
                const msgId = msg.message_id ? `<span class="text-xs text-muted-foreground ml-2">ID: ${msg.message_id.substring(0, 8)}...</span>` : '';
                const bodyHtml = msg.body ? `<div class="mt-1 text-sm text-muted-foreground font-mono bg-muted/30 p-2 rounded">${escapeHtml(msg.body)}</div>` : '';
                
                // Color code based on type
                let typeColor = 'bg-blue-500/10 text-blue-500';
                let typeIcon = '📨';
                if (msg.type === 'message') {
                    typeColor = 'bg-green-500/10 text-green-500';
                    typeIcon = '✉️';
                } else if (msg.type === 'error') {
                    typeColor = 'bg-red-500/10 text-red-500';
                    typeIcon = '⚠️';
                } else if (msg.type === 'sent') {
                    typeColor = 'bg-yellow-500/10 text-yellow-500';
                    typeIcon = '📤';
                } else if (msg.type === 'received') {
                    typeColor = 'bg-purple-500/10 text-purple-500';
                    typeIcon = '📥';
                }
                
                const messageHtml = `
                    <div class="flex flex-col gap-1 p-3 rounded bg-muted/50 border border-border/50 mb-2">
                        <div class="flex items-start gap-2">
                            <span class="text-lg">${typeIcon}</span>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 flex-wrap">
                                    <span class="text-primary font-medium">${msg.resource}</span>
                                    <span class="text-xs ${typeColor} px-2 py-0.5 rounded font-semibold">${msg.type.toUpperCase()}</span>
                                    <span class="text-xs text-muted-foreground">${msg.region}</span>
                                    ${msgId}
                                </div>
                                <div class="text-xs text-muted-foreground mt-0.5">${timestamp}</div>
                            </div>
                        </div>
                        ${bodyHtml}
                    </div>
                `;

                // Add new message at the top
                log.insertAdjacentHTML('afterbegin', messageHtml);
            });

            lucide.createIcons();

            // Keep only last 100 messages
            while (log.children.length > 100) {
                log.removeChild(log.lastChild);
            }
        } else {
            // No new messages, but monitoring is active
            pollCount++;
            lastPollTime = new Date();
            
            // Add status message to indicate monitoring is working
            if (log.children.length === 0) {
                // First poll with no messages
                log.innerHTML = `
                    <div class="text-muted-foreground text-center py-8">
                        <div class="text-2xl mb-2">👀</div>
                        <div>Surveillance active - en attente de messages...</div>
                        <div class="text-xs mt-2">Polling #${pollCount} - ${lastPollTime.toLocaleTimeString()}</div>
                        <div class="text-xs mt-1">Les messages apparaîtront ici dès leur réception</div>
                    </div>
                `;
            } else {
                // Update status at the bottom if messages exist
                const existingStatus = log.querySelector('.poll-status-indicator');
                if (existingStatus) {
                    existingStatus.remove();
                }
                
                // Only show status every 5 polls to avoid spam
                if (pollCount % 5 === 0) {
                    const statusHtml = `
                        <div class="poll-status-indicator text-xs text-muted-foreground text-center py-2 border-t border-border/50 mt-2">
                            ⏱️ Monitoring actif - Dernier poll: ${lastPollTime.toLocaleTimeString()} (${pollCount} polls)
                        </div>
                    `;
                    log.insertAdjacentHTML('beforeend', statusHtml);
                }
            }
        }
    } catch (e) {
        console.error('Failed to fetch realtime messages:', e);
        // Show error in UI for easier debugging
        try {
            log.insertAdjacentHTML('afterbegin', `<div class="text-destructive text-sm p-2">Realtime error: ${escapeHtml(String(e))}</div>`);
        } catch (ee) {}
    }
    } catch (syncErr) {
        console.error('Synchronous error in fetchRealtimeMessages:', syncErr);
        try {
            log.insertAdjacentHTML('afterbegin', `<div class="text-destructive text-sm p-2">Realtime sync error: ${escapeHtml(String(syncErr))}</div>`);
        } catch (ee) {}
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
