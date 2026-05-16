/**
 * Dashboard Polish & Interactions
 * Phase 4: Loading states, tooltips, smooth scroll, keyboard shortcuts
 */

// ============================================
// Loading States for Charts
// ============================================

function showChartLoader(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const container = canvas.parentElement;
    const loader = document.createElement('div');
    loader.className = 'chart-loader';
    loader.innerHTML = `
        <div class="chart-loader-spinner">
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
        </div>
        <span class="chart-loader-text">Loading chart...</span>
    `;
    
    container.style.position = 'relative';
    container.appendChild(loader);
    
    // Hide canvas temporarily
    canvas.style.opacity = '0.3';
    
    return loader;
}

function hideChartLoader(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const container = canvas.parentElement;
    const loader = container.querySelector('.chart-loader');
    
    if (loader) {
        loader.style.opacity = '0';
        setTimeout(() => loader.remove(), 300);
    }
    
    // Fade canvas back in
    canvas.style.transition = 'opacity 0.5s ease';
    canvas.style.opacity = '1';
}

// ============================================
// Enhanced Tooltips
// ============================================

function initEnhancedTooltips() {
    // Find all elements with data-tooltip
    const tooltipElements = document.querySelectorAll('[data-tooltip]');
    
    tooltipElements.forEach(el => {
        el.addEventListener('mouseenter', showTooltip);
        el.addEventListener('mouseleave', hideTooltip);
        el.addEventListener('focus', showTooltip);
        el.addEventListener('blur', hideTooltip);
    });
}

function showTooltip(e) {
    const text = this.dataset.tooltip;
    const position = this.dataset.tooltipPosition || 'top';
    
    const tooltip = document.createElement('div');
    tooltip.className = `enhanced-tooltip ${position}`;
    tooltip.textContent = text;
    tooltip.id = 'active-tooltip';
    
    document.body.appendChild(tooltip);
    
    const rect = this.getBoundingClientRect();
    const tooltipRect = tooltip.getBoundingClientRect();
    
    let top, left;
    
    switch(position) {
        case 'top':
            top = rect.top - tooltipRect.height - 8;
            left = rect.left + (rect.width - tooltipRect.width) / 2;
            break;
        case 'bottom':
            top = rect.bottom + 8;
            left = rect.left + (rect.width - tooltipRect.width) / 2;
            break;
        case 'left':
            top = rect.top + (rect.height - tooltipRect.height) / 2;
            left = rect.left - tooltipRect.width - 8;
            break;
        case 'right':
            top = rect.top + (rect.height - tooltipRect.height) / 2;
            left = rect.right + 8;
            break;
    }
    
    // Ensure tooltip stays within viewport
    top = Math.max(8, Math.min(top, window.innerHeight - tooltipRect.height - 8));
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipRect.width - 8));
    
    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
    tooltip.style.opacity = '0';
    tooltip.style.transform = 'translateY(4px)';
    
    // Trigger animation
    requestAnimationFrame(() => {
        tooltip.style.opacity = '1';
        tooltip.style.transform = 'translateY(0)';
    });
}

function hideTooltip() {
    const tooltip = document.getElementById('active-tooltip');
    if (tooltip) {
        tooltip.style.opacity = '0';
        tooltip.style.transform = 'translateY(4px)';
        setTimeout(() => tooltip.remove(), 200);
    }
}

// ============================================
// Smooth Scroll Navigation
// ============================================

function initSmoothScroll() {
    // Handle anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const target = document.getElementById(targetId) || document.querySelector(`[name="${targetId}"]`);
            
            if (target) {
                smoothScrollTo(target);
                // Update URL hash without jump
                history.pushState(null, null, `#${targetId}`);
            }
        });
    });
}

function smoothScrollTo(element, offset = 80) {
    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;
    
    window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
    });
    
    // Highlight element briefly
    element.classList.add('scroll-highlight');
    setTimeout(() => element.classList.remove('scroll-highlight'), 2000);
}

// ============================================
// Keyboard Shortcuts
// ============================================

function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ignore if user is typing in input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        const key = e.key.toLowerCase();
        const ctrl = e.ctrlKey || e.metaKey;
        
        // ?: Toggle shortcuts help
        if (key === '?') {
            e.preventDefault();
            toggleShortcutsHelp();
        }
        
        // Ctrl/Cmd + E: Export dashboard
        if (ctrl && key === 'e') {
            e.preventDefault();
            exportDashboard();
        }
        
        // Ctrl/Cmd + P: Print-friendly view
        if (ctrl && key === 'p') {
            e.preventDefault();
            togglePrintView();
        }
        
        // Ctrl/Cmd + F: Focus search
        if (ctrl && key === 'f') {
            e.preventDefault();
            const searchInput = document.getElementById('id_url');
            if (searchInput) searchInput.focus();
        }
        
        // Number keys 1-6: Navigate to sections
        if (!ctrl && /^[1-6]$/.test(key)) {
            e.preventDefault();
            navigateToSection(parseInt(key));
        }
        
        // Escape: Close any open modals/overlays
        if (key === 'escape') {
            closeAllOverlays();
        }
        
        // R: Re-analyze (with confirmation)
        if (!ctrl && key === 'r') {
            e.preventDefault();
            if (confirm('Re-analyze this URL?')) {
                window.location.reload();
            }
        }
    });
}

function navigateToSection(index) {
    const sections = [
        '.dashboard-header-wrapper',
        '.dashboard-kpi',
        '.dashboard-radar',
        '.dashboard-content',
        '.dashboard-tech',
        '.dashboard-issues'
    ];
    
    const section = document.querySelector(sections[index - 1]);
    if (section) {
        smoothScrollTo(section);
    }
}

function closeAllOverlays() {
    // Close sidebar on mobile
    const sidebar = document.getElementById('sidebarMenu');
    if (sidebar && sidebar.classList.contains('show')) {
        sidebar.classList.remove('show');
    }
    
    // Close expanded issue cards
    document.querySelectorAll('.issue-card.expanded').forEach(card => {
        card.classList.remove('expanded');
        const detail = card.querySelector('.issue-detail');
        if (detail) detail.style.display = 'none';
    });
}

// ============================================
// Export Dashboard Functionality
// ============================================

function exportDashboard() {
    const exportMenu = document.createElement('div');
    exportMenu.className = 'export-menu-overlay';
    exportMenu.innerHTML = `
        <div class="export-menu">
            <h4><i class="fas fa-download"></i> Export Dashboard</h4>
            <button class="export-option" onclick="exportAsPDF()">
                <i class="fas fa-file-pdf"></i>
                <span>Export as PDF</span>
                <small>Full dashboard report</small>
            </button>
            <button class="export-option" onclick="exportAsImage()">
                <i class="fas fa-image"></i>
                <span>Save as Image</span>
                <small>Dashboard screenshot</small>
            </button>
            <button class="export-option" onclick="exportDataJSON()">
                <i class="fas fa-file-code"></i>
                <span>Export Data (JSON)</span>
                <small>Raw audit data</small>
            </button>
            <button class="export-option" onclick="exportDataCSV()">
                <i class="fas fa-file-csv"></i>
                <span>Export Metrics (CSV)</span>
                <small>Spreadsheet format</small>
            </button>
            <button class="export-cancel" onclick="closeExportMenu()">Cancel</button>
        </div>
    `;
    
    document.body.appendChild(exportMenu);
    
    // Animate in
    requestAnimationFrame(() => {
        exportMenu.style.opacity = '1';
        exportMenu.querySelector('.export-menu').style.transform = 'translateY(0)';
    });
    
    // Close on backdrop click
    exportMenu.addEventListener('click', function(e) {
        if (e.target === exportMenu) closeExportMenu();
    });
}

function closeExportMenu() {
    const exportMenu = document.querySelector('.export-menu-overlay');
    if (exportMenu) {
        exportMenu.style.opacity = '0';
        exportMenu.querySelector('.export-menu').style.transform = 'translateY(20px)';
        setTimeout(() => exportMenu.remove(), 300);
    }
}

function exportAsPDF() {
    closeExportMenu();
    
    // Show loading
    const loader = document.createElement('div');
    loader.className = 'export-loading';
    loader.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating PDF...';
    document.body.appendChild(loader);
    
    // Trigger print dialog (optimized for print stylesheet)
    setTimeout(() => {
        window.print();
        loader.remove();
    }, 500);
}

function exportAsImage() {
    closeExportMenu();
    alert('Image export requires html2canvas library. Add it to enable this feature.');
}

function exportDataJSON() {
    closeExportMenu();
    
    // Collect all data from the page
    const data = {
        url: document.querySelector('.header-domain-info h1')?.textContent,
        timestamp: new Date().toISOString(),
        score: document.querySelector('.score-ring-value .value')?.textContent,
        metrics: {}
    };
    
    // Add KPI values
    document.querySelectorAll('.kpi-card').forEach(card => {
        const label = card.querySelector('.kpi-label') ? card.querySelector('.kpi-label').textContent : null;
        const value = card.querySelector('.kpi-value') ? card.querySelector('.kpi-value').textContent : null;
        if (label && value) {
            data.metrics[label] = value;
        }
    });
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seo-dashboard-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function exportDataCSV() {
    closeExportMenu();
    
    let csv = 'Metric,Value,Status\n';
    
    document.querySelectorAll('.kpi-card').forEach(card => {
        const label = card.querySelector('.kpi-label')?.textContent?.replace(/,/g, '');
        const value = card.querySelector('.kpi-value')?.textContent;
        const status = card.classList.contains('success') ? 'Good' : 
                      card.classList.contains('warning') ? 'Warning' : 'Critical';
        if (label && value) {
            csv += `"${label}","${value}","${status}"\n`;
        }
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seo-metrics-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
}

function togglePrintView() {
    document.body.classList.toggle('print-view');
    
    if (document.body.classList.contains('print-view')) {
        // Add temporary message
        const msg = document.createElement('div');
        msg.className = 'print-view-notice';
        msg.innerHTML = '<i class="fas fa-print"></i> Print view enabled. Press Ctrl+P to print.';
        document.body.appendChild(msg);
        
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 3000);
    }
}

// ============================================
// Intersection Observer for Animations
// ============================================

function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in-view');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);
    
    // Observe dashboard cards
    document.querySelectorAll('.dashboard-card').forEach(card => {
        observer.observe(card);
    });
}

// ============================================
// Touch Gestures for Mobile
// ============================================

function initTouchGestures() {
    let touchStartX = 0;
    let touchEndX = 0;
    
    document.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });
    
    document.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const swipeThreshold = 100;
        const diff = touchStartX - touchEndX;
        
        // Swipe right to open sidebar (on mobile)
        if (diff < -swipeThreshold && window.innerWidth <= 900) {
            const sidebar = document.getElementById('sidebarMenu');
            if (sidebar && !sidebar.classList.contains('show')) {
                sidebar.classList.add('show');
            }
        }
        
        // Swipe left to close sidebar
        if (diff > swipeThreshold && window.innerWidth <= 900) {
            const sidebar = document.getElementById('sidebarMenu');
            if (sidebar && sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
            }
        }
    }
}

// ============================================
// Initialize Everything
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all polish features
    initEnhancedTooltips();
    initSmoothScroll();
    initKeyboardShortcuts();
    initScrollAnimations();
    initTouchGestures();
    
    // Add data-tooltip attributes to elements that need tooltips
    document.querySelectorAll('.kpi-card').forEach(card => {
        card.setAttribute('data-tooltip', 'Click to see details');
    });
    
    document.querySelectorAll('.tech-item').forEach(item => {
        const status = item.querySelector('.tech-status')?.textContent;
        if (status) {
            item.setAttribute('data-tooltip', `Status: ${status}`);
        }
    });
    
    console.log('Dashboard Polish & Interactions initialized');
});

// Toggle shortcuts help modal
function toggleShortcutsHelp() {
    const help = document.getElementById('shortcutsHelp');
    if (help) {
        if (help.style.display === 'none') {
            help.style.display = 'flex';
        } else {
            help.style.display = 'none';
        }
    }
}


// Export functions for global access
window.DashboardPolish = {
    showChartLoader,
    hideChartLoader,
    exportDashboard,
    smoothScrollTo,
    navigateToSection,
    toggleShortcutsHelp,
    togglePrintView
};

// Also make these globally accessible for inline onclick handlers
window.exportDashboard = exportDashboard;
window.toggleShortcutsHelp = toggleShortcutsHelp;
window.togglePrintView = togglePrintView;
