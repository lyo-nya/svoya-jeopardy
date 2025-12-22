// Telegram WebApp integration
(function() {
    "use strict";
    
    const tg = window.Telegram && window.Telegram.WebApp;
    
    if (!tg) {
        console.error("Telegram WebApp SDK not available");
        return;
    }
    
    // Initialize and expand
    tg.ready();
    tg.expand();
    
    // Get init data for backend validation
    // Try from SDK first, fall back to sessionStorage
    let initData = tg.initData;
    
    if (initData) {
        // Store in sessionStorage for backup
        try {
            sessionStorage.setItem("telegram_init_data", initData);
        } catch (e) {
            console.warn("Could not store init_data in sessionStorage:", e);
        }
    } else {
        // Try to recover from sessionStorage
        try {
            initData = sessionStorage.getItem("telegram_init_data") || "";
        } catch (e) {
            console.warn("Could not retrieve init_data from sessionStorage:", e);
        }
    }
    
    console.log("Telegram WebApp: initData present =", !!initData);
    
    // Function to add init_data to a URL
    function addInitDataToUrl(url) {
        if (!initData || !url) return url;
        
        // Only modify relative URLs
        if (!url.startsWith("/")) return url;
        
        // Don't add if already present
        if (url.includes("init_data=")) return url;
        
        const separator = url.includes("?") ? "&" : "?";
        return url + separator + "init_data=" + encodeURIComponent(initData);
    }
    
    // Function to add init_data hidden field to a form
    function addInitDataToForm(form) {
        if (!initData) return;
        
        // Check if already added
        if (form.querySelector('input[name="init_data"]')) return;
        
        const input = document.createElement("input");
        input.type = "hidden";
        input.name = "init_data";
        input.value = initData;
        form.appendChild(input);
    }
    
    // Process all existing forms and links
    function processElements() {
        // Add init_data to all forms
        document.querySelectorAll("form").forEach(addInitDataToForm);
        
        // Add init_data to all links with relative URLs
        document.querySelectorAll("a[href]").forEach(function(link) {
            const href = link.getAttribute("href");
            if (href && href.startsWith("/")) {
                link.setAttribute("href", addInitDataToUrl(href));
            }
        });
    }
    
    // Process elements on DOM load
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", processElements);
    } else {
        processElements();
    }
    
    // Also observe for dynamically added elements
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType !== Node.ELEMENT_NODE) return;
                
                // Process the node itself
                if (node.tagName === "FORM") {
                    addInitDataToForm(node);
                } else if (node.tagName === "A" && node.getAttribute("href")) {
                    const href = node.getAttribute("href");
                    if (href.startsWith("/")) {
                        node.setAttribute("href", addInitDataToUrl(href));
                    }
                }
                
                // Process children
                node.querySelectorAll && node.querySelectorAll("form").forEach(addInitDataToForm);
                node.querySelectorAll && node.querySelectorAll("a[href]").forEach(function(link) {
                    const href = link.getAttribute("href");
                    if (href && href.startsWith("/")) {
                        link.setAttribute("href", addInitDataToUrl(href));
                    }
                });
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
    
    // Expose utility for manual use if needed
    window.TelegramApp = {
        initData: initData,
        addInitDataToUrl: addInitDataToUrl
    };
})();
