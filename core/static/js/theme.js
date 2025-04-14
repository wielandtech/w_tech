// Check for saved theme preference, otherwise use system preference
const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
const currentTheme = localStorage.getItem('theme');
const toggleSwitch = document.querySelector('#theme-toggle');

// Function to update theme
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    if (toggleSwitch) {
        toggleSwitch.checked = theme === 'dark';
    }
}

// Initialize theme
if (currentTheme) {
    // Use saved preference if it exists
    setTheme(currentTheme);
} else {
    // Use system preference if no saved preference
    setTheme(prefersDarkScheme.matches ? 'dark' : 'light');
}

// Listen for toggle switch change
if (toggleSwitch) {
    toggleSwitch.addEventListener('change', (e) => {
        const theme = e.target.checked ? 'dark' : 'light';
        setTheme(theme);
    });
}

// Listen for system theme changes
prefersDarkScheme.addEventListener('change', (e) => {
    // Only update theme if user hasn't set a preference
    if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light');
    }
});