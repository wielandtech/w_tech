document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".navbar a");

    const highlightLink = (id) => {
        navLinks.forEach((link) => {
            link.classList.remove("active");
            const href = link.getAttribute("href");
            if (href === `/#${id}` || href === `${window.location.pathname}`) {
                link.classList.add("active");
            }
        });
    };

    const sections = document.querySelectorAll("div[id]");
    const currentPath = window.location.pathname;

    // If we're on the homepage, observe scroll position
    if (currentPath === "/") {
        const options = {
            root: null,
            rootMargin: "0px 0px -40% 0px", // Helps mobile detect section earlier
            threshold: 0.1,
        };

        let activeId = null;
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    const id = entry.target.getAttribute("id");
                    if (id !== activeId) {
                        activeId = id;
                        highlightLink(id);
                    }
                }
            });
        }, options);

        sections.forEach((section) => observer.observe(section));
    } else {
        // If on another page, match by pathname
        navLinks.forEach((link) => {
            const linkUrl = new URL(link.href, window.location.origin);
            if (
                // Match exact path or photography section paths
                linkUrl.pathname === currentPath ||
                (linkUrl.pathname === '/images/list/' && 
                 (currentPath.startsWith('/images/') || currentPath.startsWith('/account/')))
            ) {
                link.classList.add("active");
            }
        });
    }
});
