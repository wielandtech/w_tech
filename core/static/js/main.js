document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".navbar a");
    const currentPath = window.location.pathname;

    // Define section paths
    const sections = {
        photography: {
            paths: ['/images', '/account'],
            navPath: '/images'
        },
        blog: {
            paths: ['/blog'],
            navPath: '/blog'
        }
    };

    // Check if current path matches any of a section's paths
    const isSection = (sectionPaths) => {
        return sectionPaths.some(path => currentPath.startsWith(path));
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

        // Handle section highlighting
        navLinks.forEach(link => {
            const linkUrl = new URL(link.href, window.location.origin);
            
            // Check if link matches any section
            for (const [section, config] of Object.entries(sections)) {
                if (linkUrl.pathname.startsWith(config.navPath) && isSection(config.paths)) {
                    link.classList.add("active");
                    return;
                }
            }

            // More permissive matching for other pages, exclude root path
            if (currentPath.startsWith(linkUrl.pathname) && linkUrl.pathname !== '/') {
                link.classList.add("active");
            }
        });
    }
});
