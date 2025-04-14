document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".navbar a");
    const currentPath = window.location.pathname;

    // Photography section paths
    const photographyPaths = [
        '/images',
        '/images/create',
        '/images/upload',
        '/images/detail',
        '/images/like',
        '/account',
        '/account/edit',
        '/account/register',
        '/account/users'
    ];

    const isPhotographySection = () => {
        return photographyPaths.some(path => currentPath.startsWith(path));
    };

    // Handle homepage scroll highlighting
    if (currentPath === "/") {
        const options = {
            root: null,
            rootMargin: "0px 0px -40% 0px",
            threshold: 0.1,
        };

        const sections = document.querySelectorAll("div[id]");
        let activeId = null;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const id = entry.target.getAttribute("id");
                    if (id !== activeId) {
                        activeId = id;
                        navLinks.forEach(link => {
                            const href = link.getAttribute("href");
                            if (href === `/#${id}`) {
                                link.classList.add("active");
                            } else {
                                link.classList.remove("active");
                            }
                        });
                    }
                }
            });
        }, options);

        sections.forEach((section) => observer.observe(section));
    } else {
        // Remove any existing active classes
        navLinks.forEach(link => link.classList.remove("active"));

        // Handle other pages highlighting
        navLinks.forEach(link => {
            const linkUrl = new URL(link.href, window.location.origin);
            
            if (linkUrl.pathname === '/images/' && isPhotographySection()) {
                // Highlight Photography link for all photography and account paths
                link.classList.add("active");
            } else if (linkUrl.pathname === currentPath) {
                // Exact match for other pages
                link.classList.add("active");
            }
        });
    }
});
