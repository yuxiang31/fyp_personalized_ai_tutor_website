(function () {
    const btn = document.getElementById('profileBtn');
    if (!btn) return;
    btn.addEventListener('click', function () {
        // Go to absolute URL to avoid relative path issues under /chat/
        window.location.href = '/users/profile/';
    });
})();