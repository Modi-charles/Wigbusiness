document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");

    toggleBtn.addEventListener("click", function () {
        sidebar.classList.toggle("collapsed");
    });
});