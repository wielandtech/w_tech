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
            
            // Temporarily disable smooth scrolling and transitions during theme change
            document.documentElement.style.scrollBehavior = 'auto';
            document.body.style.transition = 'none';
            
            const theme = e.target.checked ? 'dark' : 'light';
            setTheme(theme);
            
            // Force a reflow to ensure layout is stable
            document.body.offsetHeight;
            
            // Restore scroll position to prevent jumping
            window.scrollTo(0, currentScrollY);
            
            // Re-enable smooth scrolling and transitions after a short delay
            setTimeout(() => {
                document.documentElement.style.scrollBehavior = 'smooth';
                document.body.style.transition = '';
            }, 100);
        });
    }

    // Listen for system theme changes
    prefersDarkScheme.addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
});