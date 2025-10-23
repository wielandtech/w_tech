document.addEventListener('DOMContentLoaded', () => {
    const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
    const toggleSwitch = document.querySelector('#theme-toggle');
    const currentTheme = localStorage.getItem('theme');

    // Function to update theme
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        if (toggleSwitch) {
            toggleSwitch.checked = theme === 'dark';
        }
        localStorage.setItem('theme', theme);
    }

    // Initialize theme
    if (currentTheme) {
        setTheme(currentTheme);
    } else if (prefersDarkScheme.matches) {
        setTheme('dark');
    } else {
        setTheme('light');
    }

    // Listen for toggle switch change
    if (toggleSwitch) {
        toggleSwitch.addEventListener('change', (e) => {
            // Store current scroll position
            const currentScrollY = window.scrollY;
            
            const theme = e.target.checked ? 'dark' : 'light';
            setTheme(theme);
            
            // Restore scroll position to prevent jumping
            window.scrollTo(0, currentScrollY);
        });
    }

    // Listen for system theme changes
    prefersDarkScheme.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
});