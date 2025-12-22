// Telegram WebApp integration
(function() {
    // Check if Telegram WebApp is available
    if (!window.Telegram || !window.Telegram.WebApp) {
        console.error('Telegram WebApp SDK not available');
        return;
    }
    
    const tg = window.Telegram.WebApp;
    
    // Initialize and expand
    tg.ready();
    tg.expand();
    
    // Get init data for backend validation
    // First check URL params (in case we already have it), then fall back to tg.initData
    const urlParams = new URLSearchParams(window.location.search);
    const initData = urlParams.get('init_data') || tg.initData;
    
    if (!initData) {
        console.warn('No init_data available from Telegram');
        return;
    }
    
    // Store initData for use in the page
    window.telegramInitData = initData;
    
    // Add init_data to all forms on page load
    document.addEventListener("DOMContentLoaded", function() {
        document.querySelectorAll("form").forEach(function(form) {
            // Check if form already has init_data
            if (form.querySelector('input[name="init_data"]')) {
                return;
            }
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "init_data";
            input.value = initData;
            form.appendChild(input);
        });
    });
    
    // Add init_data to all links as query parameter
    document.addEventListener("DOMContentLoaded", function() {
        document.querySelectorAll("a").forEach(function(link) {
            const href = link.getAttribute("href");
            if (href && href.startsWith("/")) {
                // Check if init_data is already in the URL
                if (href.includes('init_data=')) {
                    return;
                }
                const separator = href.includes("?") ? "&" : "?";
                link.setAttribute("href", href + separator + "init_data=" + encodeURIComponent(initData));
            }
        });
    });
    
    // Also handle dynamically added elements
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType !== 1) return; // Not an element
                
                // Handle forms
                if (node.tagName === 'FORM') {
                    if (!node.querySelector('input[name="init_data"]')) {
                        const input = document.createElement("input");
                        input.type = "hidden";
                        input.name = "init_data";
                        input.value = initData;
                        node.appendChild(input);
                    }
                }
                
                // Handle links
                if (node.tagName === 'A') {
                    const href = node.getAttribute("href");
                    if (href && href.startsWith("/") && !href.includes('init_data=')) {
                        const separator = href.includes("?") ? "&" : "?";
                        node.setAttribute("href", href + separator + "init_data=" + encodeURIComponent(initData));
                    }
                }
                
                // Handle nested elements
                node.querySelectorAll && node.querySelectorAll('form').forEach(function(form) {
                    if (!form.querySelector('input[name="init_data"]')) {
                        const input = document.createElement("input");
                        input.type = "hidden";
                        input.name = "init_data";
                        input.value = initData;
                        form.appendChild(input);
                    }
                });
                
                node.querySelectorAll && node.querySelectorAll('a').forEach(function(link) {
                    const href = link.getAttribute("href");
                    if (href && href.startsWith("/") && !href.includes('init_data=')) {
                        const separator = href.includes("?") ? "&" : "?";
                        link.setAttribute("href", href + separator + "init_data=" + encodeURIComponent(initData));
                    }
                });
            });
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
})();
