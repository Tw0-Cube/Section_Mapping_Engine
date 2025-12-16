lucide.createIcons();

let debounceTimer;
let selectedIndex = -1;
let suggestions = [];
let searchHistory = JSON.parse(localStorage.getItem('searchHistory') || '[]');
let currentResultData = null;
let currentSearchMode = 'ipc';

let settings = {
    autocomplete: true,
    voiceSearch: true
};

function setLucideIcon(element, name) {
    const newIcon = lucide.createElement(name);
    element.replaceWith(newIcon);
    newIcon.id = element.id;
}

function loadSettings() {
    const saved = localStorage.getItem('userSettings');
    if (saved) {
        settings = Object.assign({}, settings, JSON.parse(saved));
    }
    applySettings();
}

function saveSettings() {
    localStorage.setItem('userSettings', JSON.stringify(settings));
}

function applySettings() {
    const voiceBtn = document.getElementById('voiceSearchBtn');
    if (voiceBtn) {
        voiceBtn.style.display = settings.voiceSearch ? 'block' : 'none';
    }
    
    Object.keys(settings).forEach(function(key) {
        const toggle = document.getElementById(key + '-toggle');
        if (toggle) {
            if (settings[key]) {
                toggle.classList.add('active');
            } else {
                toggle.classList.remove('active');
            }
        }
    });
}

function toggleSetting(settingName) {
    settings[settingName] = !settings[settingName];
    saveSettings();
    applySettings();
    showToast(settingName + ' ' + (settings[settingName] ? 'Enabled' : 'Disabled'));
}

function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    const overlay = document.getElementById('overlay');
    panel.classList.toggle('show');
    overlay.classList.toggle('show');
}

marked.setOptions({
    breaks: true,
    gfm: true
});

loadSettings();

function switchSearchMode(mode) {
    currentSearchMode = mode;
    document.getElementById('searchMode').value = mode;
    
    document.querySelectorAll('.mode-btn').forEach(btn => {
        if (btn.getAttribute('data-mode') === mode) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    const searchInput = document.getElementById('searchInput');
    if (mode === 'ipc') {
        searchInput.placeholder = 'Start typing legal term or IPC section ...';
    } else {
        searchInput.placeholder = 'Start typing legal term or BNS section ...';
    }
    
    const query = searchInput.value.trim();
    if (query.length >= 2) {
        fetchSuggestions(query);
    }
}

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    const icon = document.getElementById('themeIcon');

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);

    icon.setAttribute('data-lucide', newTheme === 'dark' ? 'moon' : 'sun');

    lucide.createIcons();
}

const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
document.getElementById('themeIcon').setAttribute('data-lucide', savedTheme === 'dark' ? 'moon' : 'sun');

function toggleShortcuts() {
    const shortcuts = document.getElementById('keyboardShortcuts');
    const overlay = document.getElementById('overlay');
    shortcuts.classList.toggle('show');
    overlay.classList.toggle('show');
}

function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

function copyToClipboard(text, label) {
    navigator.clipboard.writeText(text).then(() => {
        showToast(`${label} copied to clipboard!`);
    }).catch(() => {
        showToast('Failed to copy');
    });
}

function fillSearch(text) {
    document.getElementById('searchInput').value = text;
    document.getElementById('searchInput').focus();
    if (settings.autocomplete) {
        fetchSuggestions(text);
    }
}

function addToHistory(query) {
    searchHistory = searchHistory.filter(item => item !== query);
    searchHistory.unshift(query);
    searchHistory = searchHistory.slice(0, 5);
    localStorage.setItem('searchHistory', JSON.stringify(searchHistory));
}

function toggleHistory() {
    const dropdown = document.getElementById('historyDropdown');
    if (dropdown.classList.contains('show')) {
        dropdown.classList.remove('show');
        return;
    }
    
    if (searchHistory.length === 0) {
        dropdown.innerHTML = '<div class="history-item" style="color: var(--text-secondary); text-align: center;">No search history</div>';
    } else {
        let html = '';
        searchHistory.forEach(item => {
            html += `<div class="history-item" onclick="fillSearch('${item.replace(/'/g, "\\'")}')">${item}</div>`;
        });
        html += '<div class="history-clear" onclick="clearHistory()">Clear History</div>';
        dropdown.innerHTML = html;
    }
    dropdown.classList.add('show');
}

function clearHistory() {
    searchHistory = [];
    localStorage.removeItem('searchHistory');
    document.getElementById('historyDropdown').classList.remove('show');
    showToast('Search history cleared');
}

function toggleAccordion(element) {
    const item = element.closest('.accordion-item');
    const content = item.querySelector('.accordion-content');
    const isActive = item.classList.contains('active');
    
    if (!isActive) {
        item.classList.add('active');
        content.style.maxHeight = content.scrollHeight + 'px';
    } else {
        item.classList.remove('active');
        content.style.maxHeight = '0';
    }
}

function expandAll() {
    document.querySelectorAll('.accordion-item').forEach(item => {
        item.classList.add('active');
        item.querySelector('.accordion-content').style.maxHeight = 
            item.querySelector('.accordion-content').scrollHeight + 'px';
    });
}

function collapseAll() {
    document.querySelectorAll('.accordion-item').forEach(item => {
        item.classList.remove('active');
        item.querySelector('.accordion-content').style.maxHeight = '0';
    });
}

function shareResult() {
    if (!currentResultData) return;
    const url = new URL(window.location.href);
    url.searchParams.set('section', currentResultData.ipc_sections.split(',')[0].trim());
    
    navigator.clipboard.writeText(url.toString()).then(() => {
        showToast('Share link copied!');
    });
}

function printResult() {
    window.print();
}

function bookmarkResult() {
    if (!currentResultData) return;
    let bookmarks = JSON.parse(localStorage.getItem('bookmarks') || '[]');
    const bookmark = {
        title: currentResultData.title,
        ipc: currentResultData.ipc_sections,
        bns: currentResultData.bns_sections
    };
    
    if (bookmarks.some(b => b.ipc === bookmark.ipc)) {
        showToast('Already bookmarked!');
        return;
    }
    
    bookmarks.push(bookmark);
    localStorage.setItem('bookmarks', JSON.stringify(bookmarks));
    showToast('Bookmarked successfully!');
}

const searchInput = document.getElementById('searchInput');
const autocompleteDropdown = document.getElementById('autocompleteDropdown');
const selectedTitleInput = document.getElementById('selectedTitle');

searchInput.addEventListener('input', function() {
    const query = this.value.trim();
    
    clearTimeout(debounceTimer);
    
    if (query.length < 2) {
        hideDropdown();
        return;
    }
    
    debounceTimer = setTimeout(() => {
        if (settings.autocomplete) {
            fetchSuggestions(query);
        }
    }, 300);
});

searchInput.addEventListener('keydown', function(e) {
    const items = document.querySelectorAll('.autocomplete-item');
    
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
        updateSelection(items);
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        updateSelection(items);
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        items[selectedIndex].click();
    } else if (e.key === 'Escape') {
        hideDropdown();
        if (this.value === '') {
            document.getElementById('resultCard').classList.remove('show');
            document.getElementById('emptyState').style.display = 'block';
        }
    }
});

const voiceBtn = document.getElementById('voiceSearchBtn');
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-IN';
    recognition.continuous = false;
    
    voiceBtn.addEventListener('click', () => {
        recognition.start();
        voiceBtn.classList.add('listening');
    });
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        searchInput.value = transcript;
        voiceBtn.classList.remove('listening');
        if (settings.autocomplete) {
            fetchSuggestions(transcript);
        }
    };
    
    recognition.onerror = () => {
        voiceBtn.classList.remove('listening');
        showToast('Voice search failed');
    };
    
    recognition.onend = () => {
        voiceBtn.classList.remove('listening');
    };
} else {
    voiceBtn.style.display = 'none';
}

document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        searchInput.focus();
    }
    
    if (e.key === '?' && e.target !== searchInput) {
        e.preventDefault();
        toggleShortcuts();
    }
});

document.addEventListener('click', function(e) {
    if (!e.target.closest('.search-box')) {
        hideDropdown();
    }
    if (!e.target.closest('.history-btn') && !e.target.closest('.history-dropdown')) {
        document.getElementById('historyDropdown').classList.remove('show');
    }
    if (e.target === document.getElementById('overlay')) {
        const shortcuts = document.getElementById('keyboardShortcuts');
        const settingsPanel = document.getElementById('settingsPanel');
        if (shortcuts.classList.contains('show')) {
            toggleShortcuts();
        }
        if (settingsPanel.classList.contains('show')) {
            toggleSettings();
        }
    }
});

function fetchSuggestions(query) {
    if (!settings.autocomplete) {
        hideDropdown();
        return;
    }
    
    const formData = new FormData();
    formData.append('query', query);
    formData.append('search_mode', currentSearchMode);
    
    fetch('/autocomplete', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        suggestions = data.suggestions || [];
        displaySuggestions(suggestions, query);
    })
    .catch(error => {
        console.error('Autocomplete error:', error);
    });
}

function displaySuggestions(suggestions, query) {
    selectedIndex = -1;
    
    if (suggestions.length === 0) {
        autocompleteDropdown.innerHTML = '<div class="no-results">No matching laws found. Try a different term?</div>';
        autocompleteDropdown.classList.add('show');
        return;
    }
    
    let html = '';
    suggestions.forEach((suggestion, index) => {
        const highlightedTitle = highlightMatch(suggestion.title, query);
        html += `
            <div class="autocomplete-item" data-index="${index}" onclick="selectSuggestion(${index})">
                <div class="autocomplete-title">${highlightedTitle}</div>
                <div class="autocomplete-meta">IPC: ${suggestion.ipc} | BNS: ${suggestion.bns}</div>
            </div>
        `;
    });
    
    autocompleteDropdown.innerHTML = html;
    autocompleteDropdown.classList.add('show');
}

function highlightMatch(text, query) {
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<strong style="color: var(--accent-primary)">$1</strong>');
}

function selectSuggestion(index) {
    const suggestion = suggestions[index];
    searchInput.value = suggestion.title;
    selectedTitleInput.value = suggestion.title;
    hideDropdown();
    searchInput.focus();
}

function updateSelection(items) {
    items.forEach((item, index) => {
        if (index === selectedIndex) {
            item.classList.add('selected');
            item.scrollIntoView({ block: 'nearest' });
        } else {
            item.classList.remove('selected');
        }
    });
}

function hideDropdown() {
    autocompleteDropdown.classList.remove('show');
    selectedIndex = -1;
}

function displayError(errorMessage) {
    const resultCard = document.getElementById('resultCard');
    const html = `
        <div class="result-header" style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);">
            <div class="result-title">
                <i class="fas fa-exclamation-circle" style="margin-right: 10px;"></i>
                Search Error
            </div>
        </div>
        <div class="result-body">
            <div class="error-message">
                <div class="error-icon">
                    <i class="fas fa-search"></i>
                </div>
                <h3>No Results Found</h3>
                <p>${errorMessage}</p>
                <div class="error-suggestions">
                    <h4>Try these suggestions:</h4>
                    <ul>
                        <li>Check your spelling and try again</li>
                        <li>Use different keywords or section numbers</li>
                        <li>Try searching by legal term instead of section number</li>
                        <li>Switch between IPC and BNS search modes</li>
                    </ul>
                </div>
                <button class="control-btn" onclick="document.getElementById('searchInput').focus()" style="margin-top: 20px;">
                    <i class="fas fa-search"></i> Try Another Search
                </button>
            </div>
        </div>
    `;
    
    document.getElementById('resultContent').innerHTML = html;
    resultCard.classList.add('show');
}

document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const query = searchInput.value.trim();
    const selectedTitle = selectedTitleInput.value;
    const resultCard = document.getElementById('resultCard');
    const loadingDiv = document.getElementById('loading');
    const emptyState = document.getElementById('emptyState');
    
    hideDropdown();
    resultCard.classList.remove('show');
    emptyState.style.display = 'none';
    loadingDiv.classList.add('show');
    
    document.getElementById('step1').classList.add('active');
    document.getElementById('step2').classList.remove('active');
    
    addToHistory(query);
    
    try {
        const formData = new FormData();
        formData.append('query', query);
        formData.append('selected_title', selectedTitle);
        formData.append('search_mode', currentSearchMode);
        
        const response = await fetch('/explain_term', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        document.getElementById('step1').classList.remove('active');
        document.getElementById('step2').classList.add('active');
        
        setTimeout(() => {
            loadingDiv.classList.remove('show');
            
            if (response.ok) {
                currentResultData = data;
                displayResult(data);
                resultCard.classList.add('show');
                selectedTitleInput.value = '';
                
                const url = new URL(window.location.href);
                url.searchParams.set('section', data.ipc_sections.split(',')[0].trim());
                window.history.pushState({}, '', url);
            } else {
                displayError(data.error || 'No matching law found');
            }
        }, 500);
    } catch (error) {
        loadingDiv.classList.remove('show');
        displayError('Network error: Unable to connect to the server. Please check your connection and try again.');
    }
});

function renderMarkdown(text) {
    if (!text || text === 'None') return '';
    return marked.parse(text);
}

function displayResult(data) {
    let accordionItems = '';
    
    // Simple Explanation
    accordionItems += `
        <div class="accordion-item">
            <div class="accordion-header" onclick="toggleAccordion(this)">
                <div class="accordion-title">
                    <i class="fas fa-lightbulb"></i>
                    <span>Simple Explanation</span>
                </div>
                <i class="fas fa-chevron-down accordion-icon"></i>
            </div>
            <div class="accordion-content">
                <div class="accordion-body">
                    <button class="copy-content-btn" onclick="copyToClipboard(\`${data.explanation.replace(/`/g, '\\`')}\`, 'Explanation')">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                    ${renderMarkdown(data.explanation)}
                    <div class="source-tag">${data.source}</div>
                </div>
            </div>
        </div>
    `;
    
    // Legal Meaning (keep the FULL legal text)
    if (data.legal && data.legal !== 'None' && data.legal.trim() !== '') {
        accordionItems += `
            <div class="accordion-item">
                <div class="accordion-header" onclick="toggleAccordion(this)">
                    <div class="accordion-title">
                        <i class="fas fa-gavel"></i>
                        <span>Legal Meaning</span>
                    </div>
                    <i class="fas fa-chevron-down accordion-icon"></i>
                </div>
                <div class="accordion-content">
                    <div class="accordion-body">
                        <button class="copy-content-btn" onclick="copyToClipboard(\`${data.legal.replace(/`/g, '\\`')}\`, 'Legal meaning')">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                        ${renderMarkdown(data.legal)}
                    </div>
                </div>
            </div>
        `;
    }
    
    // IPC to BNS Changes
    if (data.change && data.change !== 'None' && data.change.trim() !== '') {
        accordionItems += `
            <div class="accordion-item">
                <div class="accordion-header" onclick="toggleAccordion(this)">
                    <div class="accordion-title">
                        <i class="fas fa-exchange-alt"></i>
                        <span>IPC to BNS Changes</span>
                    </div>
                    <i class="fas fa-chevron-down accordion-icon"></i>
                </div>
                <div class="accordion-content">
                    <div class="accordion-body">
                        <button class="copy-content-btn" onclick="copyToClipboard(\`${data.change.replace(/`/g, '\\`')}\`, 'Changes')">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                        ${renderMarkdown(data.change)}
                    </div>
                </div>
            </div>
        `;
    }
    
    // Summary with BNSS Classification
    let summaryContent = `
        <p><strong>Old Law (IPC):</strong> ${data.ipc_sections}${data.ipc_subsections ? ' (' + data.ipc_subsections + ')' : ''}</p>
        <p><strong>New Law (BNS):</strong> ${data.bns_sections}</p>
        <p><strong>Title:</strong> ${data.title}</p>
    `;
    
    // Add BNSS Classification if available
    if (data.bnss_classification && Array.isArray(data.bnss_classification) && data.bnss_classification.length > 0) {
        summaryContent += `
            <div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid var(--border-color);">
                <h4 style="color: var(--accent-primary); margin-bottom: 10px;">
                    BNSS Classification
                </h4>
                <ul style="list-style: none; padding-left: 0;">
        `;
        
        data.bnss_classification.forEach(item => {
            summaryContent += `<li style="margin-bottom: 8px; padding-left: 10px; border-left: 3px solid var(--accent-primary);">${renderMarkdown(item)}</li>`;
        });
        
        summaryContent += `
                </ul>
            </div>
        `;
    }
    
    accordionItems += `
        <div class="accordion-item">
            <div class="accordion-header" onclick="toggleAccordion(this)">
                <div class="accordion-title">
                    <i class="fas fa-info-circle"></i>
                    <span>Summary</span>
                </div>
                <i class="fas fa-chevron-down accordion-icon"></i>
            </div>
            <div class="accordion-content">
                <div class="accordion-body">
                    <button class="copy-content-btn" onclick="copyToClipboard(\`Old Law (IPC): ${data.ipc_sections}${data.ipc_subsections ? ' (' + data.ipc_subsections + ')' : ''}\nNew Law (BNS): ${data.bns_sections}\nTitle: ${data.title}\`, 'Summary')">
                        <i class="fas fa-copy"></i> Copy
                    </button>
                    ${summaryContent}
                </div>
            </div>
        </div>
    `;
    
    const relatedSections = generateRelatedSections(data.ipc_sections);
    
    const html = `
        <div class="result-header">
            <div class="result-actions">
                <button class="action-btn" onclick="bookmarkResult()" title="Bookmark">
                    <i data-lucide="bookmark"></i>
                </button>
                <button class="action-btn" onclick="shareResult()" title="Share">
                    <i data-lucide="share-2"></i>
                </button>
                <button class="action-btn" onclick="printResult()" title="Print">
                    <i data-lucide="printer"></i>
                </button>
            </div>
            <div class="result-title">${data.title}</div>
            <div class="result-meta">
                <div class="meta-item">
                    <i data-lucide="gavel"></i>
                    <span>IPC: ${data.ipc_sections}</span>
                    <i data-lucide="clipboard-copy" onclick="copyToClipboard('${data.ipc_sections}', 'IPC section')" title="Copy IPC" style="cursor: pointer;"></i>
                </div>
                <div class="meta-item">
                    <i data-lucide="book-open-text"></i>
                    <span>BNS: ${data.bns_sections}</span>
                    <i data-lucide="clipboard-copy" onclick="copyToClipboard('${data.bns_sections}', 'BNS section')" title="Copy BNS" style="cursor: pointer;"></i>
                </div>
            </div>
        </div>
        
        <div class="result-body">
            <div class="accordion-controls">
                <button class="control-btn" onclick="expandAll()">
                    <i class="fas fa-expand-alt"></i> Expand All
                </button>
                <button class="control-btn" onclick="collapseAll()">
                    <i class="fas fa-compress-alt"></i> Collapse All
                </button>
            </div>
            
            <div class="accordion">
                ${accordionItems}
            </div>
            
            ${relatedSections}
        </div>
    `;
    
    document.getElementById('resultContent').innerHTML = html;
    lucide.createIcons();
}

function generateRelatedSections(ipcSection) {
    const section = parseInt(ipcSection.split(',')[0].trim());
    if (isNaN(section)) return '';
    
    const related = [
        section - 1,
        section + 1,
        section - 10,
        section + 10
    ].filter(s => s > 0 && s <= 511);
    
    if (related.length === 0) return '';
    
    return `
        <div class="related-sections">
            <h4><i class="fas fa-link"></i> Related Sections</h4>
            <div class="related-tags">
                ${related.map(s => `<span class="related-tag" onclick="fillSearch('${s}'); document.getElementById('searchForm').requestSubmit();">IPC ${s}</span>`).join('')}
            </div>
        </div>
    `;
}

window.addEventListener('load', () => {
    const params = new URLSearchParams(window.location.search);
    const section = params.get('section');
    if (section) {
        fillSearch(section);
        setTimeout(() => {
            document.getElementById('searchForm').requestSubmit();
        }, 500);
    }
});

lucide.createIcons();