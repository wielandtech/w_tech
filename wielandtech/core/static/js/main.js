document.addEventListener("DOMContentLoaded", function () {
    const navLinks = document.querySelectorAll(".navbar a");

    // Handle scroll-based active highlighting for anchors (/#about, etc.)
    const sections = document.querySelectorAll("div[id]");
    if (sections.length > 0 && window.location.pathname === "/") {
        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    const id = entry.target.getAttribute("id");
                    const navLink = document.querySelector(`.navbar a[href='/#${id}']`);
                    if (entry.isIntersecting) {
                        navLinks.forEach((link) => link.classList.remove("active"));
                        if (navLink) navLink.classList.add("active");
                    }
                });
            },
            {
                root: null,
                threshold: 0.5,
            }
        );

        sections.forEach((section) => observer.observe(section));
    }

    // Handle pathname-based highlighting (for routes like /blog)
    const currentPath = window.location.pathname;
    navLinks.forEach((link) => {
        const linkPath = new URL(link.href).pathname;
        if (linkPath === currentPath && !link.href.includes("#")) {
            navLinks.forEach((l) => l.classList.remove("active"));
            link.classList.add("active");
        }
    });
});
