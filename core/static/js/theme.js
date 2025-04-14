// Check for saved theme preference, otherwise use system preference
const prefersDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
const currentTheme = localStorage.getItem('theme');

if (currentTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    document.getElementById('checkbox').checked = true;
} else if (currentTheme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    document.getElementById('checkbox').checked = false;
} else {
    // Use system preference
    if (prefersDarkScheme.matches) {
        document.documentElement.setAttribute('data-theme', 'dark');
        document.getElementById('checkbox').checked = true;
    }
}

// Listen for toggle switch change
const toggleSwitch = document.querySelector('#checkbox');
toggleSwitch.addEventListener('change', switchTheme);

function switchTheme(e) {
    if (e.target.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
    }
}

// Listen for system theme changes
prefersDarkScheme.addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
        if (e.matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
            document.getElementById('checkbox').checked = true;
        } else {
            document.documentElement.setAttribute('data-theme', 'light');
            document.getElementById('checkbox').checked = false;
        }
    }
});