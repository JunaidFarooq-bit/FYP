/**
 * Dashboard Charts - Chart.js Configurations
 * SEO Score Radar Chart and Keyword Density Bar Chart
 */

// Chart.js Global Configuration
Chart.defaults.font.family = "'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif";
Chart.defaults.color = '#64748b';
Chart.defaults.scale.grid.color = '#e2e8f0';

/**
 * Initialize Score Radar Chart
 * @param {string} canvasId - Canvas element ID
 * @param {Object} scores - Score data object
 */
function initScoreRadarChart(canvasId, scores) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const data = scores || {
        onPage: 75,
        content: 80,
        technical: 70,
        authority: 65,
        accessibility: 72
    };

    const industryAvg = [70, 75, 72, 68, 74];
    const userScores = [data.onPage, data.content, data.technical, data.authority, data.accessibility];

    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['On-Page SEO', 'Content Quality', 'Technical SEO', 'Authority', 'Accessibility'],
            datasets: [
                {
                    label: 'Your Score',
                    data: userScores,
                    backgroundColor: 'rgba(2, 86, 155, 0.2)',
                    borderColor: '#023761',
                    borderWidth: 3,
                    pointBackgroundColor: '#023761',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 6,
                    pointHoverRadius: 8,
                    fill: true
                },
                {
                    label: 'Industry Average',
                    data: industryAvg,
                    backgroundColor: 'rgba(226, 232, 240, 0.3)',
                    borderColor: '#94a3b8',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    fill: true
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#023761',
                    padding: 12,
                    cornerRadius: 8,
                    titleFont: {
                        size: 13,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 12
                    },
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': ' + context.raw + '/100';
                        }
                    }
                }
            },
            scales: {
                r: {
                    min: 0,
                    max: 100,
                    ticks: {
                        stepSize: 20,
                        font: {
                            size: 10
                        },
                        callback: function(value) {
                            return value;
                        }
                    },
                    pointLabels: {
                        font: {
                            size: 12,
                            weight: '600'
                        },
                        color: '#374151'
                    },
                    grid: {
                        color: '#e2e8f0'
                    },
                    angleLines: {
                        color: '#e2e8f0'
                    }
                }
            },
            animation: {
                duration: 1500,
                easing: 'easeOutQuart'
            }
        }
    });
}

/**
 * Initialize Keyword Density Bar Chart
 * @param {string} canvasId - Canvas element ID
 * @param {Array} keywords - Array of keyword objects {word, density, status}
 */
function initKeywordChart(canvasId, keywords) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const data = keywords || [];
    const maxItems = 10;
    const displayData = data.slice(0, maxItems);

    const labels = displayData.map(k => k.word);
    const densities = displayData.map(k => parseFloat(k.density) || 0);
    const colors = displayData.map(k => {
        if (k.status === 'optimal') return '#10b981';
        if (k.status === 'warning') return '#f59e0b';
        if (k.status === 'danger') return '#ef4444';
        return '#3b82f6';
    });

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Keyword Density (%)',
                data: densities,
                backgroundColor: colors,
                borderRadius: 6,
                borderSkipped: false,
                barThickness: 24,
                maxBarThickness: 32
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#023761',
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return 'Density: ' + context.raw + '%';
                        }
                    }
                }
            },
            scales: {
                x: {
                    min: 0,
                    max: 8,
                    ticks: {
                        stepSize: 1,
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: '#e2e8f0'
                    }
                },
                y: {
                    ticks: {
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    },
                    grid: {
                        display: false
                    }
                }
            },
            animation: {
                duration: 1200,
                easing: 'easeOutQuart',
                delay: function(context) {
                    return context.dataIndex * 100;
                }
            }
        }
    });
}

/**
 * Initialize E-E-A-T Breakdown Doughnut Chart
 * @param {string} canvasId - Canvas element ID
 * @param {Object} eeatData - E-E-A-T scores
 */
function initEEATChart(canvasId, eeatData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const data = eeatData || {
        title_eeat: 75,
        desc_eeat: 80,
        heading_eeat: 70
    };

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Title E-E-A-T', 'Description E-E-A-T', 'Heading E-E-A-T'],
            datasets: [{
                data: [data.title_eeat, data.desc_eeat, data.heading_eeat],
                backgroundColor: [
                    '#023761',
                    '#02569b',
                    '#80aacd'
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: '#023761',
                    padding: 12,
                    cornerRadius: 8,
                    callbacks: {
                        label: function(context) {
                            return context.label + ': ' + context.raw + '/100';
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1200
            }
        }
    });
}

/**
 * Initialize Mini Sparkline Chart for KPI
 * @param {string} canvasId - Canvas element ID
 * @param {Array} data - Array of values
 * @param {string} color - Line color
 */
function initSparkline(canvasId, data, color) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: Array(data.length).fill(''),
            datasets: [{
                data: data,
                borderColor: color || '#023761',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            },
            scales: {
                x: { display: false },
                y: { display: false }
            },
            layout: {
                padding: 0
            }
        }
    });
}

/**
 * Initialize Performance Trend Line Chart
 * @param {string} canvasId - Canvas element ID
 * @param {Object} metrics - Performance metrics
 */
function initPerformanceChart(canvasId, metrics) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;

    const data = metrics || {
        ttfb: 0.8,
        loadTime: 2.5,
        renderTime: 1.2
    };

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['TTFB', 'Render Time', 'Load Time'],
            datasets: [{
                label: 'Time (seconds)',
                data: [data.ttfb, data.renderTime, data.loadTime],
                backgroundColor: [
                    data.ttfb <= 0.8 ? '#10b981' : data.ttfb <= 1.5 ? '#f59e0b' : '#ef4444',
                    data.renderTime <= 1.5 ? '#10b981' : '#f59e0b',
                    data.loadTime <= 3 ? '#10b981' : data.loadTime <= 5 ? '#f59e0b' : '#ef4444'
                ],
                borderRadius: 8,
                barThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.raw + 's';
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + 's';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Initialize all dashboard charts
 * @param {Object} data - Complete dashboard data object
 */
function initDashboardCharts(data) {
    const charts = {};

    // Score Radar Chart
    if (document.getElementById('scoreRadarChart')) {
        charts.radar = initScoreRadarChart('scoreRadarChart', data.chart_scores);
    }

    // Keyword Density Chart
    if (document.getElementById('keywordChart')) {
        charts.keywords = initKeywordChart('keywordChart', data.keywords);
    }

    // E-E-A-T Chart
    if (document.getElementById('eeatChart')) {
        charts.eeat = initEEATChart('eeatChart', data.eeat_data);
    }

    // Performance Chart
    if (document.getElementById('performanceChart')) {
        charts.performance = initPerformanceChart('performanceChart', data.performance);
    }

    return charts;
}

// Export functions for use in templates
window.DashboardCharts = {
    initScoreRadarChart,
    initKeywordChart,
    initEEATChart,
    initSparkline,
    initPerformanceChart,
    initDashboardCharts
};
