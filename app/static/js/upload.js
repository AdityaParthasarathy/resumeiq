(function () {
    const dropzone = document.getElementById("dropzone");
    const input = document.getElementById("resume-input");
    const label = document.getElementById("dropzone-label");
    const form = document.getElementById("upload-form");
    const submitBtn = document.getElementById("submit-btn");

    if (!dropzone || !input) return;

    function showFilename(file) {
        if (!file) return;
        label.textContent = "";
        const name = document.createElement("span");
        name.className = "font-medium text-indigo-600";
        name.textContent = file.name;
        label.appendChild(name);
        label.appendChild(document.createTextNode(" selected"));
    }

    dropzone.addEventListener("click", () => input.click());

    dropzone.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            input.click();
        }
    });

    input.addEventListener("change", () => showFilename(input.files[0]));

    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add("border-indigo-500", "bg-indigo-50");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove("border-indigo-500", "bg-indigo-50");
        });
    });

    dropzone.addEventListener("drop", (e) => {
        const file = e.dataTransfer.files[0];
        if (file) {
            input.files = e.dataTransfer.files;
            showFilename(file);
        }
    });

    if (form && submitBtn) {
        form.addEventListener("submit", () => {
            submitBtn.disabled = true;
            submitBtn.textContent = "Analyzing…";
        });
    }
})();
