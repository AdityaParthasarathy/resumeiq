/* Custom "target role" picker: a button that opens an icon + descriptor
   listbox, replacing a plain <select>. The real <select id="target_role">
   stays in the DOM as the single source of truth for the form -- this
   widget only ever reads/writes its value, so submission and server-side
   validation ("Please select a role") are untouched. If JS never runs, the
   native select is what's shown (styled to match, not the browser default),
   so the form keeps working either way -- same fallback pattern the
   dropzone file input already uses elsewhere in this file's sibling. */
(function () {
    "use strict";

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const field = document.querySelector(".role-field");
    const trigger = document.getElementById("role-trigger");
    const listbox = document.getElementById("role-listbox");
    const select = document.getElementById("target_role");
    const label = document.getElementById("role-label");

    if (!field || !trigger || !listbox || !select) return;

    const options = Array.from(listbox.querySelectorAll(".role-option"));
    const triggerIcon = trigger.querySelector(".role-trigger__icon svg");
    const triggerName = trigger.querySelector(".role-trigger__name");
    const triggerBlurb = trigger.querySelector(".role-trigger__blurb");

    let open = false;
    let activeIndex = -1;
    let typeaheadBuffer = "";
    let typeaheadTimer = null;

    function applySelection(index) {
        options.forEach((opt, i) => opt.setAttribute("aria-selected", String(i === index)));
        const opt = options[index];
        if (!opt) return;
        triggerIcon.innerHTML = opt.querySelector(".role-option__icon svg").innerHTML;
        triggerName.textContent = opt.querySelector(".role-option__label").textContent;
        triggerBlurb.textContent = opt.querySelector(".role-option__blurb").textContent;
        trigger.classList.add("has-value");
    }

    function selectRole(index) {
        const opt = options[index];
        if (!opt) return;
        applySelection(index);
        if (select.value !== opt.dataset.value) {
            select.value = opt.dataset.value;
            select.dispatchEvent(new Event("change", { bubbles: true }));
        }
        closeListbox();
    }

    function setActive(index) {
        index = Math.max(0, Math.min(index, options.length - 1));
        options.forEach((opt) => opt.classList.remove("is-active"));
        const opt = options[index];
        opt.classList.add("is-active");
        trigger.setAttribute("aria-activedescendant", opt.id);
        opt.scrollIntoView({ block: "nearest" });
        activeIndex = index;
    }

    function reallyHide() {
        listbox.hidden = true;
        delete listbox.dataset.closing;
    }

    function onDocPointerDown(e) {
        if (!field.contains(e.target)) closeListbox({ restoreFocus: false });
    }

    function openListbox() {
        if (open) return;
        open = true;
        listbox.hidden = false;
        delete listbox.dataset.closing;
        trigger.setAttribute("aria-expanded", "true");
        const selectedIndex = options.findIndex((o) => o.getAttribute("aria-selected") === "true");
        setActive(selectedIndex >= 0 ? selectedIndex : 0);
        document.addEventListener("pointerdown", onDocPointerDown, true);
    }

    function closeListbox({ restoreFocus = true } = {}) {
        if (!open) return;
        open = false;
        trigger.setAttribute("aria-expanded", "false");
        trigger.removeAttribute("aria-activedescendant");
        document.removeEventListener("pointerdown", onDocPointerDown, true);
        if (reducedMotion) {
            reallyHide();
        } else {
            listbox.dataset.closing = "true";
            listbox.addEventListener("animationend", reallyHide, { once: true });
        }
        if (restoreFocus) trigger.focus();
    }

    function typeahead(char) {
        typeaheadBuffer += char.toLowerCase();
        clearTimeout(typeaheadTimer);
        typeaheadTimer = setTimeout(() => (typeaheadBuffer = ""), 600);
        const startFrom = (activeIndex + 1) % options.length;
        for (let i = 0; i < options.length; i++) {
            const idx = (startFrom + i) % options.length;
            if (options[idx].dataset.value.toLowerCase().startsWith(typeaheadBuffer)) {
                setActive(idx);
                return;
            }
        }
    }

    trigger.addEventListener("click", () => (open ? closeListbox() : openListbox()));
    label.addEventListener("click", () => trigger.focus());

    trigger.addEventListener("keydown", (e) => {
        switch (e.key) {
            case "ArrowDown":
                e.preventDefault();
                open ? setActive(activeIndex + 1) : openListbox();
                break;
            case "ArrowUp":
                e.preventDefault();
                open ? setActive(activeIndex - 1) : openListbox();
                break;
            case "Home":
                if (open) {
                    e.preventDefault();
                    setActive(0);
                }
                break;
            case "End":
                if (open) {
                    e.preventDefault();
                    setActive(options.length - 1);
                }
                break;
            case "Enter":
            case " ":
                e.preventDefault();
                open ? selectRole(activeIndex) : openListbox();
                break;
            case "Escape":
                if (open) {
                    e.preventDefault();
                    closeListbox();
                }
                break;
            case "Tab":
                if (open) closeListbox({ restoreFocus: false });
                break;
            default:
                if (open && e.key.length === 1 && /[a-z0-9]/i.test(e.key)) typeahead(e.key);
        }
    });

    options.forEach((opt, i) => {
        opt.addEventListener("click", () => selectRole(i));
        opt.addEventListener("mouseenter", () => setActive(i));
    });

    // Hand the real select's visible role over to the widget. Kept until now
    // so a JS error above leaves a normal, fully working native select.
    select.classList.add("js-enhanced");
    select.tabIndex = -1;
    select.setAttribute("aria-hidden", "true");

    // Reflect a value the browser restored (back/forward cache, autofill).
    const restoredIndex = options.findIndex((o) => o.dataset.value === select.value);
    if (restoredIndex >= 0) applySelection(restoredIndex);
})();
