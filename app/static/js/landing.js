(function () {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Scroll reveals -- fade/rise elements in once, then stop watching them.
    const revealEls = document.querySelectorAll(".reveal");
    if (reducedMotion || !("IntersectionObserver" in window)) {
        revealEls.forEach((el) => el.classList.add("is-visible"));
    } else {
        const revealObserver = new IntersectionObserver(
            (entries, observer) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add("is-visible");
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.15, rootMargin: "0px 0px -8% 0px" }
        );
        revealEls.forEach((el) => revealObserver.observe(el));
    }

    // Scroll-story: whichever step is most centered in the viewport becomes
    // the "active" layer on the sticky resume mock.
    const steps = document.querySelectorAll(".story-step");
    const mock = document.getElementById("story-resume");

    if (steps.length && mock && "IntersectionObserver" in window) {
        const setActive = (layer, activeStep) => {
            mock.setAttribute("data-active", layer);
            steps.forEach((s) => s.classList.toggle("is-active", s === activeStep));
        };

        const stepObserver = new IntersectionObserver(
            (entries) => {
                const visible = entries
                    .filter((e) => e.isIntersecting)
                    .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
                if (visible.length > 0) {
                    const target = visible[0].target;
                    setActive(target.dataset.layer, target);
                }
            },
            { threshold: [0.3, 0.5, 0.7], rootMargin: "-20% 0px -20% 0px" }
        );
        steps.forEach((step) => stepObserver.observe(step));

        // Start on the first layer instead of an unstyled blank state.
        setActive(steps[0].dataset.layer, steps[0]);
    }

    // Smooth-scroll same-page anchor CTAs (instant if the user prefers reduced motion).
    document.querySelectorAll('a[href^="#"]').forEach((link) => {
        link.addEventListener("click", (e) => {
            const target = document.querySelector(link.getAttribute("href"));
            if (!target) return;
            e.preventDefault();
            target.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
        });
    });

    // FAQ accordion -- each item toggles independently (not single-open), state
    // lives in aria-expanded (source of truth) mirrored onto data-open for CSS.
    document.querySelectorAll(".faq-trigger").forEach((trigger) => {
        trigger.addEventListener("click", () => {
            const item = trigger.closest(".faq-item");
            const isOpen = trigger.getAttribute("aria-expanded") === "true";
            trigger.setAttribute("aria-expanded", String(!isOpen));
            item.dataset.open = String(!isOpen);
        });
    });
})();
