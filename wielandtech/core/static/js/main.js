document.addEventListener("DOMContentLoaded", function () {
    const sections = document.querySelectorAll("div[id]");
    const navLinks = document.querySelectorAll(".navbar a[href^='/#']");

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
            rootMargin: "0px",
            threshold: 0.5, // 50% of the section needs to be visible
        }
    );

    sections.forEach((section) => {
        observer.observe(section);
    });
});
