/**
 * VeriVision - Dashboard JavaScript
 * Charts and analytics visualization
 */

// Data passed from Django template (defined in dashboard.html)
// dashboardData is already defined in the template

document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    initializeAnimations();
});

function initializeCharts() {
    // Chart.js global configuration
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = '#334155';

    // Results Distribution Pie Chart
    const resultsCtx = document.getElementById('resultsChart');
    if (resultsCtx) {
        new Chart(resultsCtx, {
            type: 'doughnut',
            data: {
                labels: ['Real', 'Fake', 'Manipulated', 'Suspicious'],
                datasets: [{
                    data: [
                        dashboardData.resultCounts.real || 0,
                        dashboardData.resultCounts.fake || 0,
                        dashboardData.resultCounts.manipulated || 0,
                        dashboardData.resultCounts.suspicious || 0
                    ],
                    backgroundColor: [
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(239, 68, 68, 0.8)',
                        'rgba(249, 115, 22, 0.8)',
                        'rgba(245, 158, 11, 0.8)'
                    ],
                    borderColor: [
                        'rgba(16, 185, 129, 1)',
                        'rgba(239, 68, 68, 1)',
                        'rgba(249, 115, 22, 1)',
                        'rgba(245, 158, 11, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }

    // Content Type Bar Chart
    const typeCtx = document.getElementById('typeChart');
    if (typeCtx) {
        new Chart(typeCtx, {
            type: 'bar',
            data: {
                labels: ['Image', 'Video', 'Audio', 'URL'],
                datasets: [{
                    label: 'Number of Scans',
                    data: [
                        dashboardData.typeCounts.image || 0,
                        dashboardData.typeCounts.video || 0,
                        dashboardData.typeCounts.audio || 0,
                        dashboardData.typeCounts.url || 0
                    ],
                    backgroundColor: [
                        'rgba(6, 182, 212, 0.8)',
                        'rgba(139, 92, 246, 0.8)',
                        'rgba(236, 72, 153, 0.8)',
                        'rgba(34, 197, 94, 0.8)'
                    ],
                    borderColor: [
                        'rgba(6, 182, 212, 1)',
                        'rgba(139, 92, 246, 1)',
                        'rgba(236, 72, 153, 1)',
                        'rgba(34, 197, 94, 1)'
                    ],
                    borderWidth: 2,
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Scans: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        },
                        grid: {
                            color: 'rgba(51, 65, 85, 0.5)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    // Time Series Line Chart
    const trendsCtx = document.getElementById('trendsChart');
    if (trendsCtx) {
        const labels = dashboardData.timeSeries.map(item => item.date);
        const data = dashboardData.timeSeries.map(item => item.count);

        new Chart(trendsCtx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Scans per Day',
                    data: data,
                    borderColor: 'rgba(6, 182, 212, 1)',
                    backgroundColor: 'rgba(6, 182, 212, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: 'rgba(6, 182, 212, 1)',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                return `Scans: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        },
                        grid: {
                            color: 'rgba(51, 65, 85, 0.5)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxTicksLimit: 10
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }
}

function initializeAnimations() {
    // Animate metric values on scroll
    const observerOptions = {
        threshold: 0.5
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                animateValue(entry.target);
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.metric-value').forEach(el => {
        observer.observe(el);
    });
}

function animateValue(element) {
    const value = parseFloat(element.textContent);
    const isPercentage = element.textContent.includes('%');
    const duration = 1500;
    const start = 0;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease out quart
        const easeOut = 1 - Math.pow(1 - progress, 4);

        const current = start + (value - start) * easeOut;

        if (isPercentage) {
            element.textContent = current.toFixed(1) + '%';
        } else {
            element.textContent = Math.round(current);
        }

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            if (isPercentage) {
                element.textContent = value.toFixed(1) + '%';
            } else {
                element.textContent = value;
            }
        }
    }

    requestAnimationFrame(update);
}

// Auto-refresh dashboard data every 5 minutes
setInterval(() => {
    fetch('/api/stats/')
        .then(response => response.json())
        .then(data => {
            // Update stats without full page reload
            updateDashboardStats(data);
        })
        .catch(error => console.error('Error fetching stats:', error));
}, 300000); // 5 minutes

function updateDashboardStats(data) {
    // Update total scans
    const totalScansEl = document.querySelector('.stat-card:first-child .stat-content h3');
    if (totalScansEl) {
        totalScansEl.textContent = data.total_scans;
    }

    // You can add more dynamic updates here
}
