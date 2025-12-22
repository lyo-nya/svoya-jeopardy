// Telegram WebApp integration
const tg = window.Telegram.WebApp;

// Initialize and expand
tg.ready();
tg.expand();

// Get init data for backend validation
const initData = tg.initData;

// Add init_data to all forms on page load
document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll("form").forEach(function(form) {
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
            const separator = href.includes("?") ? "&" : "?";
            link.setAttribute("href", href + separator + "init_data=" + encodeURIComponent(initData));
        }
    });
});
