document.addEventListener('DOMContentLoaded', () => {
    loadCredentials();

    document.getElementById('test-conn-btn').addEventListener('click', testConnection);
    document.getElementById('scan-btn').addEventListener('click', scanResources);
    document.getElementById('stats-btn').addEventListener('click', fetchStatistics);

    // Observe when pipeline section becomes visible to update diagram lists
    const pipelineSection = document.getElementById('pipeline');
    if (pipelineSection) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Update diagram lists when section becomes visible
                    // Add a small delay to ensure React is ready
                    setTimeout(() => {
                        updateDiagramLists();
                    }, 200);
                }
            });
        }, { threshold: 0.1 });
        observer.observe(pipelineSection);
    }

    // Also update diagram lists when clicking on pipeline link in nav
    const pipelineNavLink = document.querySelector('a[href="#pipeline"]');
    if (pipelineNavLink) {
        pipelineNavLink.addEventListener('click', (e) => {
            e.preventDefault();
            document.getElementById('pipeline')?.scrollIntoView({ behavior: 'smooth' });
            // Update after scroll animation
            setTimeout(() => {
                updateDiagramLists();
            }, 500);
        });
    }
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
    const statusText = document.getElementById('status-text');
    if (!el || !statusText) return;

    // Update status indicator
    const indicator = el.querySelector('.h-2') || el.querySelector('div');
    if (indicator) {
        indicator.className = `h-2 w-2 rounded-full ${type === 'error' ? 'bg-red-500' : (type === 'success' ? 'bg-green-500' : 'bg-gray-500')}`;
    }

    // Update text
    statusText.textContent = msg;
    statusText.className = type === 'error' ? 'text-red-400' : (type === 'success' ? 'text-green-400' : 'text-gray-400');
}

// Notification system
function showNotification(message, type = 'info', duration = 5000) {
    // Create notification container if it doesn't exist
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'fixed top-24 right-6 z-[100] space-y-2';
        document.body.appendChild(container);
    }

    // Create notification element
    const notification = document.createElement('div');
    const bgColor = type === 'success' ? 'bg-green-500/20 border-green-500/50' : 
                     type === 'error' ? 'bg-red-500/20 border-red-500/50' : 
                     'bg-blue-500/20 border-blue-500/50';
    const textColor = type === 'success' ? 'text-green-400' : 
                      type === 'error' ? 'text-red-400' : 
                      'text-blue-400';
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'alert-circle' : 
                 'info';

    notification.className = `${bgColor} ${textColor} border rounded-lg px-4 py-3 shadow-lg backdrop-blur-sm flex items-center gap-3 min-w-[300px] max-w-[400px] animate-slide-in`;
    notification.innerHTML = `
        <i data-lucide="${icon}" class="w-5 h-5 flex-shrink-0"></i>
        <span class="text-sm font-medium flex-1">${message}</span>
        <button onclick="this.parentElement.remove()" class="text-current opacity-70 hover:opacity-100 transition-opacity">
            <i data-lucide="x" class="w-4 h-4"></i>
        </button>
    `;
    
    container.appendChild(notification);
    lucide.createIcons();

    // Auto-remove after duration
    setTimeout(() => {
        notification.style.animation = 'slide-out 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, duration);

    return notification;
}

// Update region indicator
function updateRegionIndicator(regions) {
    const regionValue = document.getElementById('region-value');
    if (regionValue && regions) {
        const regionList = regions.split(',').map(r => r.trim()).filter(r => r);
        if (regionList.length > 0) {
            regionValue.textContent = regionList.length === 1 ? regionList[0] : `${regionList[0]} (+${regionList.length - 1})`;
        }
    }
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
        if (data.regions) {
            document.getElementById('regions').value = data.regions;
            updateRegionIndicator(data.regions);
        }
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

    // Show initial notification
    const scanningNotification = showNotification('Scan en cours...', 'info', 0);
    
    // Close modal automatically
    const modal = document.getElementById('credentials-modal');
    if (modal) {
        modal.classList.remove('active');
    }

    const data = {
        access_key: document.getElementById('access_key').value,
        secret_key: document.getElementById('secret_key').value,
        session_token: document.getElementById('session_token').value,
        profile: document.getElementById('profile').value,
        regions: document.getElementById('regions').value,
        remember: document.getElementById('remember').checked
    };

    // Save credentials if remember is checked (non-blocking)
    fetch('/api/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    }).catch(e => console.error('Failed to save credentials:', e));

    // Perform scan in background
    fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(inventory => {
        // Remove scanning notification
        if (scanningNotification && scanningNotification.parentElement) {
            scanningNotification.remove();
        }

        if (inventory.error) {
            setStatus(`Scan failed: ${inventory.error}`, 'error');
            showNotification(`Échec du scan: ${inventory.error}`, 'error');
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
            updateRegionIndicator(data.regions);
            const successMsg = `Scan terminé: ${currentInventory.topics.length} topics et ${currentInventory.queues.length} queues trouvés.`;
            setStatus(successMsg, 'success');
            showNotification(successMsg, 'success');
        }
    })
    .catch(e => {
        // Remove scanning notification
        if (scanningNotification && scanningNotification.parentElement) {
            scanningNotification.remove();
        }
        const errorMsg = `Erreur lors du scan: ${e}`;
        setStatus(errorMsg, 'error');
        showNotification(errorMsg, 'error');
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = originalText;
        lucide.createIcons();
    });
}

function updateTables() {
    // Update Counts
    const countTopics = document.getElementById('count-topics');
    const countQueues = document.getElementById('count-queues');
    const countLinks = document.getElementById('count-links');
    
    if (countTopics) countTopics.textContent = currentInventory.topics.length;
    if (countQueues) countQueues.textContent = currentInventory.queues.length;
    if (countLinks) countLinks.textContent = currentInventory.links.length;

    // Update Dashboard Grid with Statistics
    updateDashboardGrid();

    // Update Queues List
    updateQueuesList();

    // Update Topics List
    updateTopicsList();

    updateRealtimeQueueList();
    updateDiagramLists();
}

function updateDashboardGrid() {
    const grid = document.getElementById('dashboard-grid');
    if (!grid) return;

    if (currentInventory.queues.length === 0 && currentInventory.topics.length === 0) {
        grid.innerHTML = `
            <div class="glass-panel spotlight-card rounded-xl p-6 text-center col-span-full">
                <div class="text-gray-400 text-sm mb-2">Scan resources to view statistics</div>
            </div>
        `;
        return;
    }

    // Calculate statistics
    const subscribedQueueArns = new Set(currentInventory.links.map(l => l.to_arn));
    const orphanCount = currentInventory.queues.filter(q => !subscribedQueueArns.has(q.arn)).length;
    
    // Get total stats
    let totalSent = 0, totalReceived = 0, totalPublished = 0;
    currentInventory.queues.forEach(q => {
        const s = currentInventory.stats[q.arn] || {};
        totalSent += s.numberofmessagessent_28d || 0;
        totalReceived += s.numberofmessagesreceived_28d || 0;
    });
    currentInventory.topics.forEach(t => {
        const s = currentInventory.stats[t.arn] || {};
        totalPublished += s.published_28d || 0;
    });

    grid.innerHTML = `
        <div class="glass-panel spotlight-card rounded-xl p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 bg-accent/20 rounded-lg flex items-center justify-center">
                    <i data-lucide="layers" class="w-5 h-5 text-accent"></i>
                </div>
                <div>
                    <div class="text-2xl font-display font-semibold text-white">${currentInventory.queues.length}</div>
                    <div class="text-xs text-gray-400 font-mono">Queues</div>
                </div>
            </div>
            <div class="text-xs text-gray-500">Orphan: ${orphanCount}</div>
        </div>
        <div class="glass-panel spotlight-card rounded-xl p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                    <i data-lucide="radio" class="w-5 h-5 text-blue-400"></i>
                </div>
                <div>
                    <div class="text-2xl font-display font-semibold text-white">${currentInventory.topics.length}</div>
                    <div class="text-xs text-gray-400 font-mono">Topics</div>
                </div>
            </div>
            <div class="text-xs text-gray-500">Published: ${totalPublished.toLocaleString()}</div>
        </div>
        <div class="glass-panel spotlight-card rounded-xl p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center">
                    <i data-lucide="link" class="w-5 h-5 text-green-400"></i>
                </div>
                <div>
                    <div class="text-2xl font-display font-semibold text-white">${currentInventory.links.length}</div>
                    <div class="text-xs text-gray-400 font-mono">Subscriptions</div>
                </div>
            </div>
        </div>
        <div class="glass-panel spotlight-card rounded-xl p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-10 h-10 bg-purple-500/20 rounded-lg flex items-center justify-center">
                    <i data-lucide="activity" class="w-5 h-5 text-purple-400"></i>
                </div>
                <div>
                    <div class="text-2xl font-display font-semibold text-white">${totalSent.toLocaleString()}</div>
                    <div class="text-xs text-gray-400 font-mono">Sent (28d)</div>
                </div>
            </div>
            <div class="text-xs text-gray-500">Received: ${totalReceived.toLocaleString()}</div>
        </div>
    `;
    
    lucide.createIcons();
}

function updateQueuesList() {
    const list = document.getElementById('queues-list');
    if (!list) return;

    if (currentInventory.queues.length === 0) {
        list.innerHTML = '<div class="col-span-full text-center text-gray-400 text-sm py-8">No queues found. Scan resources first.</div>';
        return;
    }

    const subscribedQueueArns = new Set(currentInventory.links.map(l => l.to_arn));

    list.innerHTML = currentInventory.queues.map(q => {
        const s = currentInventory.stats[q.arn] || {};
        const sent = s.numberofmessagessent_28d !== undefined ? s.numberofmessagessent_28d.toLocaleString() : '-';
        const recv = s.numberofmessagesreceived_28d !== undefined ? s.numberofmessagesreceived_28d.toLocaleString() : '-';
        const isOrphan = !subscribedQueueArns.has(q.arn);
        
        return `
            <div class="glass-panel spotlight-card rounded-xl p-6">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 bg-accent/20 rounded-lg flex items-center justify-center">
                            <i data-lucide="layers" class="w-4 h-4 text-accent"></i>
                        </div>
                        <div>
                            <div class="font-display font-semibold text-white">${q.name}</div>
                            <div class="text-xs text-gray-400 font-mono">${q.region}</div>
                        </div>
                    </div>
                    ${isOrphan ? '<span class="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400 border border-red-500/30">Orphan</span>' : ''}
                </div>
                <div class="space-y-2 text-xs font-mono">
                    <div class="flex justify-between text-gray-400">
                        <span>Sent (28d):</span>
                        <span class="text-white">${sent}</span>
                    </div>
                    <div class="flex justify-between text-gray-400">
                        <span>Received (28d):</span>
                        <span class="text-white">${recv}</span>
                    </div>
                    <div class="pt-2 border-t border-white/10">
                        <div class="text-gray-500 truncate" title="${q.url}">${q.url}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    lucide.createIcons();
}

function updateTopicsList() {
    const list = document.getElementById('topics-list');
    if (!list) return;

    if (currentInventory.topics.length === 0) {
        list.innerHTML = '<div class="col-span-full text-center text-gray-400 text-sm py-8">No topics found. Scan resources first.</div>';
        return;
    }

    // Group links by topic
    const topicToQueues = {};
    currentInventory.links.forEach(l => {
        if (!topicToQueues[l.from_arn]) {
            topicToQueues[l.from_arn] = [];
        }
        const queueName = l.to_arn ? l.to_arn.split(':').pop() : 'Unknown';
        topicToQueues[l.from_arn].push(queueName);
    });

    list.innerHTML = currentInventory.topics.map(t => {
        const s = currentInventory.stats[t.arn] || {};
        const published = s.published_28d !== undefined ? s.published_28d.toLocaleString() : '-';
        const queues = topicToQueues[t.arn] || [];
        
        return `
            <div class="glass-panel spotlight-card rounded-xl p-6">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex items-center gap-3">
                        <div class="w-8 h-8 bg-blue-500/20 rounded-lg flex items-center justify-center">
                            <i data-lucide="radio" class="w-4 h-4 text-blue-400"></i>
                        </div>
                        <div>
                            <div class="font-display font-semibold text-white">${t.name}</div>
                            <div class="text-xs text-gray-400 font-mono">${t.region}</div>
                        </div>
                    </div>
                </div>
                <div class="space-y-2 text-xs font-mono">
                    <div class="flex justify-between text-gray-400">
                        <span>Published (28d):</span>
                        <span class="text-white">${published}</span>
                    </div>
                    ${queues.length > 0 ? `
                        <div class="pt-2 border-t border-white/10">
                            <div class="text-gray-400 mb-1">Subscribed Queues:</div>
                            <div class="flex flex-wrap gap-1">
                                ${queues.slice(0, 3).map(q => `
                                    <span class="px-2 py-0.5 rounded bg-white/5 text-gray-300 border border-white/10 text-[10px]">${q}</span>
                                `).join('')}
                                ${queues.length > 3 ? `<span class="px-2 py-0.5 rounded bg-white/5 text-gray-300 border border-white/10 text-[10px]">+${queues.length - 3}</span>` : ''}
                            </div>
                        </div>
                    ` : '<div class="pt-2 border-t border-white/10 text-gray-500 text-[10px]">No subscriptions</div>'}
                </div>
            </div>
        `;
    }).join('');
    
    lucide.createIcons();
}

function updateDiagramLists() {
    console.log('updateDiagramLists called', {
        topicsCount: currentInventory.topics.length,
        queuesCount: currentInventory.queues.length,
        reactLoaded: typeof window.mountDiagramCheckboxes !== 'undefined'
    });

    // Wait for React to be loaded
    if (typeof window.mountDiagramCheckboxes === 'undefined') {
        console.warn('React components not loaded yet, retrying...');
        setTimeout(updateDiagramLists, 100);
        return;
    }

    // Update diagram topic list with React
    const diagramTopicContainer = document.getElementById('diagram-topic-list');
    if (diagramTopicContainer) {
        // Always clear and remount to ensure fresh state
        diagramTopicContainer.innerHTML = '';
        if (currentInventory.topics.length === 0) {
            diagramTopicContainer.innerHTML = '<div class="text-xs text-gray-500">Scan resources first</div>';
        } else {
            const topics = currentInventory.topics.map(t => ({ arn: t.arn, name: t.name }));
            console.log('Mounting topics:', topics.length);
            try {
                window.mountDiagramCheckboxes('diagram-topic-list', 'topics', topics, updateDiagramFromSelection);
            } catch (e) {
                console.error('Failed to mount topic checkboxes:', e);
                diagramTopicContainer.innerHTML = '<div class="text-xs text-red-500">Erreur lors du chargement des topics</div>';
            }
        }
    }
    
    // Update diagram queue list with React
    const diagramQueueContainer = document.getElementById('diagram-queue-list');
    if (diagramQueueContainer) {
        // Always clear and remount to ensure fresh state
        diagramQueueContainer.innerHTML = '';
        if (currentInventory.queues.length === 0) {
            diagramQueueContainer.innerHTML = '<div class="text-xs text-gray-500">Scan resources first</div>';
        } else {
            const queues = currentInventory.queues.map(q => ({ arn: q.arn, name: q.name }));
            console.log('Mounting queues:', queues.length);
            try {
                window.mountDiagramCheckboxes('diagram-queue-list', 'queues', queues, updateDiagramFromSelection);
            } catch (e) {
                console.error('Failed to mount queue checkboxes:', e);
                diagramQueueContainer.innerHTML = '<div class="text-xs text-red-500">Erreur lors du chargement des queues</div>';
            }
        }
    }
}

function selectAllDiagramTopics() {
    if (window.diagramCheckboxRefs && window.diagramCheckboxRefs.topics && window.diagramCheckboxRefs.topics.current) {
        window.diagramCheckboxRefs.topics.current.selectAll();
    }
}

function deselectAllDiagramTopics() {
    if (window.diagramCheckboxRefs && window.diagramCheckboxRefs.topics && window.diagramCheckboxRefs.topics.current) {
        window.diagramCheckboxRefs.topics.current.deselectAll();
    }
}

function selectAllDiagramQueues() {
    if (window.diagramCheckboxRefs && window.diagramCheckboxRefs.queues && window.diagramCheckboxRefs.queues.current) {
        window.diagramCheckboxRefs.queues.current.selectAll();
    }
}

function deselectAllDiagramQueues() {
    if (window.diagramCheckboxRefs && window.diagramCheckboxRefs.queues && window.diagramCheckboxRefs.queues.current) {
        window.diagramCheckboxRefs.queues.current.deselectAll();
    }
}

function getSelectedDiagramTopics() {
    if (window.diagramCheckboxRefs && window.diagramCheckboxRefs.topics && window.diagramCheckboxRefs.topics.current) {
        return window.diagramCheckboxRefs.topics.current.getSelectedArns();
    }
    return [];
}

function getSelectedDiagramQueues() {
    if (window.diagramCheckboxRefs && window.diagramCheckboxRefs.queues && window.diagramCheckboxRefs.queues.current) {
        return window.diagramCheckboxRefs.queues.current.getSelectedArns();
    }
    return [];
}

function getFilteredInventoryFromDiagramSelection() {
    const selectedTopicArns = getSelectedDiagramTopics();
    const selectedQueueArns = getSelectedDiagramQueues();
    
    // If nothing selected, return null to use full inventory
    if (selectedTopicArns.length === 0 && selectedQueueArns.length === 0) {
        return null;
    }
    
    // Build sets of selected resources
    const selectedTopics = new Set(selectedTopicArns);
    const selectedQueues = new Set(selectedQueueArns);
    
    // Find related resources (topics linked to selected queues, queues linked to selected topics)
    const relatedTopics = new Set(selectedTopics);
    const relatedQueues = new Set(selectedQueues);
    
    // Add queues that are subscribed to selected topics
    currentInventory.links.forEach(link => {
        if (selectedTopics.has(link.from_arn)) {
            relatedQueues.add(link.to_arn);
        }
    });
    
    // Add topics that have subscriptions to selected queues
    currentInventory.links.forEach(link => {
        if (selectedQueues.has(link.to_arn)) {
            relatedTopics.add(link.from_arn);
        }
    });
    
    // Build filtered inventory for diagram
    const filteredInventory = [];
    const topicMap = {};
    const queueMap = {};
    
    // Group by region
    const byRegion = {};
    currentInventory.topics.forEach(t => {
        if (!byRegion[t.region]) byRegion[t.region] = { topics: [], queues: [], links: [] };
        if (relatedTopics.has(t.arn)) {
            byRegion[t.region].topics.push(t);
            topicMap[t.arn] = t;
        }
    });
    
    currentInventory.queues.forEach(q => {
        if (!byRegion[q.region]) byRegion[q.region] = { topics: [], queues: [], links: [] };
        if (relatedQueues.has(q.arn)) {
            byRegion[q.region].queues.push(q);
            queueMap[q.arn] = q;
        }
    });
    
    // Add links only between selected/related resources
    currentInventory.links.forEach(link => {
        if (relatedTopics.has(link.from_arn) && relatedQueues.has(link.to_arn)) {
            const region = topicMap[link.from_arn]?.region || queueMap[link.to_arn]?.region;
            if (region && byRegion[region]) {
                byRegion[region].links.push(link);
            }
        }
    });
    
    // Convert to inventory format
    Object.keys(byRegion).forEach(region => {
        const regionData = byRegion[region];
        if (regionData.topics.length > 0 || regionData.queues.length > 0) {
            filteredInventory.push({
                region: region,
                accountId: null,
                topics: regionData.topics.map(t => ({ arn: t.arn, name: t.name })),
                queues: regionData.queues.map(q => ({ arn: q.arn, name: q.name, url: q.url })),
                links: regionData.links.map(l => ({ from_arn: l.from_arn, to_arn: l.to_arn, protocol: l.protocol, attributes: l.attributes }))
            });
        }
    });
    
    return filteredInventory.length > 0 ? filteredInventory : null;
}

function updateDiagramFromSelection() {
    const filteredInventory = getFilteredInventoryFromDiagramSelection();
    
    // If nothing selected, show empty diagram
    if (!filteredInventory) {
        const mermaidDiv = document.getElementById('mermaid-graph');
        mermaidDiv.innerHTML = 'graph TD;\n    A[Select resources to view diagram] --> B[Diagram will appear here];';
        mermaidDiv.removeAttribute('data-processed');
        try {
            // Use the same Linear theme configuration
            mermaid.initialize({
                startOnLoad: false,
                theme: 'base',
                themeVariables: {
                    primaryColor: '#FF7A1A',
                    primaryTextColor: '#ffffff',
                    lineColor: '#9B9B9B',
                    secondaryColor: '#9B9B9B',
                    background: '#ffffff',
                    textColor: '#0A0A0A'
                }
            });
            mermaid.init(undefined, mermaidDiv);
        } catch (e) {
            console.error("Mermaid init failed", e);
        }
        return;
    }
    
    // Use the existing updateDiagram function
    updateDiagram(filteredInventory);
}

function updateRealtimeQueueList() {
    const container = document.getElementById('realtime-queue-list');
    if (!container) return;

    if (currentInventory.queues.length === 0) {
        container.innerHTML = '<div class="text-xs text-gray-500">Scan resources first to see available queues</div>';
        return;
    }

    container.innerHTML = '';
    currentInventory.queues.forEach(queue => {
        const label = document.createElement('label');
        label.className = 'flex items-center gap-2 px-2 py-1.5 rounded hover:bg-white/5 cursor-pointer transition-colors text-sm text-gray-300';
        label.title = queue.url || queue.name;

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = queue.arn;
        checkbox.dataset.name = queue.name;
        checkbox.className = 'h-4 w-4 rounded border-white/20 bg-white/5 text-accent focus:ring-accent focus:ring-offset-0';
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

        // Store the Mermaid code for export
        window.lastMermaidCode = data.content;

        const mermaidDiv = document.getElementById('mermaid-graph');
        mermaidDiv.innerHTML = data.content;
        mermaidDiv.removeAttribute('data-processed');

        // Configure Mermaid with Linear-inspired theme
        mermaid.initialize({
            startOnLoad: false,
            theme: 'base',
            themeVariables: {
                // Linear-inspired colors
                primaryColor: '#FF7A1A',        // Orange for topics
                primaryTextColor: '#ffffff',     // White text on primary
                primaryBorderColor: '#FF7A1A',   // Orange border
                lineColor: '#9B9B9B',           // Neutral gray for edges
                secondaryColor: '#9B9B9B',       // Neutral gray for queues
                secondaryTextColor: '#ffffff',   // White text on secondary
                tertiaryColor: '#ffffff',       // White background
                background: '#ffffff',           // White background
                mainBkg: '#ffffff',             // Main background
                secondBkg: '#9B9B9B',          // Secondary background (queues)
                tertiaryBkg: '#ffffff',         // Tertiary background
                textColor: '#0A0A0A',           // Near-black text
                border1: '#E5E5E5',             // Subtle gray border
                border2: '#9B9B9B',            // Neutral gray border
                noteBkgColor: '#FAFAFA',        // Very light gray for notes
                noteTextColor: '#0A0A0A',       // Dark text for notes
                noteBorderColor: '#E5E5E5',     // Subtle border for notes
                actorBorder: '#FF7A1A',          // Orange border for actors
                actorBkg: '#FF7A1A',            // Orange background for actors
                actorTextColor: '#ffffff',       // White text
                actorLineColor: '#9B9B9B',      // Gray line
                labelBoxBkgColor: '#ffffff',     // White label box
                labelBoxBorderColor: '#E5E5E5',  // Subtle border
                labelTextColor: '#0A0A0A',      // Dark text
                loopTextColor: '#0A0A0A',       // Dark text
                activationBorderColor: '#FF7A1A', // Orange activation border
                activationBkgColor: '#FF7A1A',   // Orange activation background
                sequenceNumberColor: '#ffffff',  // White sequence numbers
                sectionBkgColor: '#FAFAFA',     // Light gray sections
                altSectionBkgColor: '#F5F5F5',   // Slightly darker alt sections
                sectionBorderColor: '#E5E5E5',   // Subtle section border
                gridColor: '#E5E5E5',            // Subtle grid
                doneTaskBkgColor: '#FF7A1A',     // Orange for done tasks
                doneTaskBorderColor: '#FF7A1A',  // Orange border
                activeTaskBkgColor: '#9B9B9B',   // Gray for active tasks
                activeTaskBorderColor: '#9B9B9B', // Gray border
                taskBkgColor: '#FAFAFA',         // Light gray for tasks
                taskTextColor: '#0A0A0A',        // Dark text
                taskTextLightColor: '#ffffff',    // White text on colored backgrounds
                taskTextOutsideColor: '#0A0A0A', // Dark text outside
                taskTextClickableColor: '#FF7A1A', // Orange clickable text
                critBorderColor: '#FF7A1A',      // Orange critical border
                critBkgColor: '#FF7A1A',         // Orange critical background
                todayLineColor: '#FF7A1A',       // Orange today line
                cScale0: '#FF7A1A',              // Orange scale 0
                cScale1: '#9B9B9B',              // Gray scale 1
                cScale2: '#E5E5E5'               // Light gray scale 2
            }
        });

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

    // Get filtered inventory from diagram selection, or use full inventory if nothing selected
    const filteredInventory = getFilteredInventoryFromDiagramSelection();
    const inventoryToExport = filteredInventory || window.rawInventory;

    if (!inventoryToExport) {
        alert("No data to export.");
        return;
    }

    if (format === 'json') {
        // For JSON export, use currentInventory structure
        if (filteredInventory) {
            // Convert filtered inventory to currentInventory format
            const exportData = {
                topics: [],
                queues: [],
                links: []
            };
            filteredInventory.forEach(regionItem => {
                regionItem.topics.forEach(t => exportData.topics.push({ ...t, region: regionItem.region }));
                regionItem.queues.forEach(q => exportData.queues.push({ ...q, region: regionItem.region }));
                regionItem.links.forEach(l => exportData.links.push({ ...l, region: regionItem.region }));
            });
            downloadFile('inventory.json', JSON.stringify(exportData, null, 2));
        } else {
            downloadFile('inventory.json', JSON.stringify(currentInventory, null, 2));
        }
    } else if (format === 'mermaid') {
        if (!window.lastMermaidCode) {
            alert("No diagram available. Please select resources in the Diagram tab first.");
            return;
        }
        downloadFile('diagram.mmd', window.lastMermaidCode);
    } else if (format === 'sql') {
        const res = await fetch('/api/export/sql', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inventoryToExport)
        });
        const data = await res.json();
        downloadFile('inventory.sql', data.content);
    } else if (format === 'drawio') {
        const res = await fetch('/api/export/drawio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inventoryToExport)
        });
        const data = await res.json();
        downloadFile('inventory.drawio', data.content);
    } else if (format === 'canvas') {
        const res = await fetch('/api/export/canvas', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(inventoryToExport)
        });
        const data = await res.json();
        if (data.error) {
            alert(`Export failed: ${data.error}`);
            return;
        }
        // JSON Canvas format - download as .canvas file
        downloadFile('inventory.canvas', JSON.stringify(data, null, 2));
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
        // Switch button color back to primary (orange)
        button.className = 'flex-1 bg-accent text-black px-4 py-2 text-xs font-semibold uppercase tracking-wider hover:bg-white transition-all';
        lucide.createIcons();
    } else {
        // Start monitoring
        isMonitoring = true;
    statusText.textContent = 'Stop Monitoring';
    setToggleIcon(button, 'pause');
        // Switch button color to destructive (red)
        button.className = 'flex-1 bg-red-500 text-white px-4 py-2 text-xs font-semibold uppercase tracking-wider hover:bg-red-600 transition-all';
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
    if (!log) {
        console.error('realtime-log element not found');
        return;
    }
    
    try {
        console.debug('fetchRealtimeMessages called');
    } catch (e) {}

    try {

    // Check if we have scanned resources
    if (currentInventory.topics.length === 0 && currentInventory.queues.length === 0) {
        log.innerHTML = `
            <div class="text-center py-8 text-gray-400">
                Please scan resources first before monitoring
            </div>
        `;
        return;
    }

    // Prepare items list for monitoring
    const selectedQueueArns = getSelectedQueues();

    if (selectedQueueArns.length === 0) {
        log.innerHTML = `
            <div class="text-center py-8 text-gray-400">
                <div class="text-2xl mb-2">🔍</div>
                <div class="font-semibold mb-2 text-white">Aucune ressource sélectionnée</div>
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
                const msgId = msg.message_id ? `<span class="text-xs ml-2 text-gray-400">ID: ${msg.message_id.substring(0, 8)}...</span>` : '';
                const bodyHtml = msg.body ? `<div class="mt-2 text-xs font-mono p-2 rounded bg-black/30 text-gray-300 border border-white/10">${escapeHtml(msg.body)}</div>` : '';
                
                // Color code based on type
                let typeColorClass = '';
                let typeIcon = '📨';
                if (msg.type === 'message') {
                    typeColorClass = 'bg-green-500/20 text-green-400 border-green-500/30';
                    typeIcon = '✉️';
                } else if (msg.type === 'error') {
                    typeColorClass = 'bg-red-500/20 text-red-400 border-red-500/30';
                    typeIcon = '⚠️';
                } else if (msg.type === 'sent') {
                    typeColorClass = 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
                    typeIcon = '📤';
                } else if (msg.type === 'received') {
                    typeColorClass = 'bg-purple-500/20 text-purple-400 border-purple-500/30';
                    typeIcon = '📥';
                } else {
                    typeColorClass = 'bg-blue-500/20 text-blue-400 border-blue-500/30';
                }
                
                const messageHtml = `
                    <div class="flex flex-col gap-1 p-3 rounded border mb-2 bg-white/5 border-white/10">
                        <div class="flex items-start gap-2">
                            <span class="text-lg">${typeIcon}</span>
                            <div class="flex-1 min-w-0">
                                <div class="flex items-center gap-2 flex-wrap">
                                    <span class="font-medium text-white">${msg.resource}</span>
                                    <span class="text-xs px-2 py-0.5 rounded font-semibold border ${typeColorClass}">${msg.type.toUpperCase()}</span>
                                    <span class="text-xs text-gray-400">${msg.region}</span>
                                    ${msgId}
                                </div>
                                <div class="text-xs mt-0.5 text-gray-400">${timestamp}</div>
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
                    <div class="text-center py-8 text-gray-400">
                        <div class="text-2xl mb-2">👀</div>
                        <div class="text-white">Surveillance active - en attente de messages...</div>
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
                        <div class="poll-status-indicator text-xs text-center py-2 mt-2 text-gray-400 border-t border-white/10">
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
            log.insertAdjacentHTML('afterbegin', `<div class="text-sm p-2 text-red-400 bg-red-500/10 border border-red-500/30 rounded">Realtime error: ${escapeHtml(String(e))}</div>`);
        } catch (ee) {}
    }
    } catch (syncErr) {
        console.error('Synchronous error in fetchRealtimeMessages:', syncErr);
        try {
            log.insertAdjacentHTML('afterbegin', `<div class="text-sm p-2 text-red-400 bg-red-500/10 border border-red-500/30 rounded">Realtime sync error: ${escapeHtml(String(syncErr))}</div>`);
        } catch (ee) {}
    }
}

function clearRealtimeLog() {
    const log = document.getElementById('realtime-log');
    if (!log) return;
    log.innerHTML = `
        <div class="text-center py-8 text-gray-400">
            Click "Start Monitoring" to begin tracking real-time message exchanges
        </div>
    `;
}
