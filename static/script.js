// This is the new content for static/script.js

document.addEventListener('DOMContentLoaded', () => {

    // --- Theme switcher code ---
    const themeSwitcher = document.querySelector('.theme-switcher');
    const body = document.body;

    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', () => {
            body.classList.toggle('dark-mode');
            if (body.classList.contains('dark-mode')) {
                localStorage.setItem('theme', 'dark');
            } else {
                localStorage.setItem('theme', 'light');
            }
        });
    }

    if (localStorage.getItem('theme') === 'dark') {
        body.classList.add('dark-mode');
    }
    // --- End of theme switcher code ---


    // --- NEW: Delete Confirmation ---
    // We will find all delete buttons and add this
    const deleteButtons = document.querySelectorAll('.action-btn.delete');
    deleteButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
                e.preventDefault(); // Stop the link from being followed
            }
        });
    });

    // --- NEW: Flash Message Auto-Hide ---
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        // Set a timeout to add the 'fade-out' class
        setTimeout(() => {
            message.classList.add('fade-out');
        }, 5000); // Start fading out after 5 seconds

        // After the fade-out animation finishes (1s), remove the element
        setTimeout(() => {
            if (message.parentNode) {
                message.parentNode.removeChild(message);
            }
        }, 6000); // 5s delay + 1s fade
    });
});