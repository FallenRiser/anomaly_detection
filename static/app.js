/**
 * Supply Chain Anomaly Assistant — Client-side JavaScript
 */

// ── AI Explanation Request ────────────────────────────────────────────────

async function requestExplanation(anomalyId) {
    const btn = document.getElementById('explainBtn');
    const content = document.getElementById('explanationContent');
    const loading = document.getElementById('explanationLoading');

    // Show loading state
    btn.style.display = 'none';
    content.style.display = 'none';
    loading.style.display = 'block';

    try {
        const response = await fetch('/explain', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ anomaly_id: anomalyId }),
        });

        const data = await response.json();

        loading.style.display = 'none';
        content.style.display = 'block';

        if (data.error) {
            content.innerHTML = `
                <div class="alert alert-error">
                    <span class="alert-icon">❌</span>
                    Error: ${data.error}
                </div>
            `;
            btn.style.display = 'inline-flex';
            return;
        }

        // Render the explanation with markdown-like formatting
        const formattedExplanation = formatExplanation(data.explanation);
        content.innerHTML = `
            <div class="explanation-text">${formattedExplanation}</div>
            <div class="explanation-meta">
                <span>Generated just now by AI Agent</span>
            </div>
        `;

    } catch (error) {
        loading.style.display = 'none';
        content.style.display = 'block';
        content.innerHTML = `
            <div class="alert alert-error">
                <span class="alert-icon">❌</span>
                Network error: ${error.message}. Please try again.
            </div>
        `;
        btn.style.display = 'inline-flex';
    }
}


// ── Format Explanation Text ───────────────────────────────────────────────

function formatExplanation(text) {
    if (!text) return '';

    // Convert markdown-like headers
    text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gm, '<h2>$1</h2>');

    // Bold text
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

    // Italic text
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');

    // Lists
    text = text.replace(/^- (.*$)/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>\n?)+/gs, '<ul>$&</ul>');

    // Numbered lists
    text = text.replace(/^\d+\. (.*$)/gm, '<li>$1</li>');

    // Line breaks
    text = text.replace(/\n\n/g, '</p><p>');
    text = '<p>' + text + '</p>';

    // Clean up empty paragraphs
    text = text.replace(/<p>\s*<\/p>/g, '');
    text = text.replace(/<p>(<h[23]>)/g, '$1');
    text = text.replace(/(<\/h[23]>)<\/p>/g, '$1');
    text = text.replace(/<p>(<ul>)/g, '$1');
    text = text.replace(/(<\/ul>)<\/p>/g, '$1');

    return text;
}


// ── Utility Functions ─────────────────────────────────────────────────────

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ── Initialize ────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Attach explain button handler (uses data-anomaly-id attribute)
    const explainBtn = document.getElementById('explainBtn');
    if (explainBtn) {
        explainBtn.addEventListener('click', function () {
            const anomalyId = this.getAttribute('data-anomaly-id');
            requestExplanation(parseInt(anomalyId, 10));
        });
    }

    // Add animation classes on scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.card, .stat-card, .chart-card, .detail-card').forEach(el => {
        observer.observe(el);
    });
});
