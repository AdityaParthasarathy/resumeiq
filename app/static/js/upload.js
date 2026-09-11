(function () {
    const dropzone = document.getElementById("dropzone");
    const input = document.getElementById("resume-input");
    const label = document.getElementById("dropzone-label");

    if (!dropzone || !input) return;

    function showFilename(file) {
        if (file) {
            label.innerHTML = `<span class="font-medium text-indigo-600">${file.name}</span> selected`;
        }
    }

    dropzone.addEventListener("click", () => input.click());

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
})();
