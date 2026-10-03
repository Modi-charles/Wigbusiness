function initSidebar() {
    const button = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("sidebar");

    if (!button || !sidebar) {
        return;
    }

    button.addEventListener("click", function () {
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle("show");
        } else {
            sidebar.classList.toggle("collapsed");
        }
    });
}

function initThemeSettings() {
    const themeButtons = document.querySelectorAll("[data-theme-choice]");

    themeButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const theme = button.dataset.themeChoice;

            if (!theme) {
                return;
            }

            document.documentElement.setAttribute("data-theme", theme);
            localStorage.setItem("wigbiz-theme", theme);
        });
    });

    const savedTheme = localStorage.getItem("wigbiz-theme");

    if (savedTheme) {
        document.documentElement.setAttribute("data-theme", savedTheme);
    }
}

function initPrintButtons() {
    document.querySelectorAll("[data-print]").forEach(function (button) {
        button.addEventListener("click", function () {
            window.print();
        });
    });
}

function initNotificationButton() {
    const button = document.querySelector("[data-notifications]");

    if (button) {
        button.addEventListener("click", function () {
            window.alert("Notification system will be connected here.");
        });
    }
}

function initManagerDashboard() {
    document
        .querySelectorAll(".target-bar-fill[data-percent]")
        .forEach(function (element) {
            element.style.width = `${element.dataset.percent}%`;
        });
}

function initSaleForm() {
    const itemRows = document.getElementById("item-rows");
    const addProductButton = document.getElementById("add-product");
    const totalForms = document.getElementById("id_form-TOTAL_FORMS");
    const discountInput = document.getElementById("id_discount");
    const taxInput = document.getElementById("id_tax");
    const amountPaidInput = document.getElementById("id_amount_paid");
    const barcodeInput = document.getElementById("barcode-input");
    const scanBarcodeButton = document.getElementById("scan-barcode");
    const barcodeMessage = document.getElementById("barcode-message");

    if (
        !itemRows ||
        !addProductButton ||
        !totalForms ||
        !discountInput ||
        !taxInput ||
        !amountPaidInput
    ) {
        return;
    }

    function formatMoney(value) {
        return Number(value).toFixed(2);
    }

    function createNewRow() {
        const formCount = parseInt(totalForms.value, 10);
        const template = document.getElementById("empty-row-template");
        const newRow = template.cloneNode(true);

        newRow.removeAttribute("id");
        newRow.innerHTML = newRow.innerHTML.replace(
            /__prefix__/g,
            formCount,
        );
        totalForms.value = formCount + 1;

        return newRow;
    }

    function calculateRow(row) {
        const productSelect = row.querySelector("select[name$='product']");
        const quantityInput = row.querySelector("input[name$='quantity']");
        const priceDisplay = row.querySelector(".selling-price");
        const totalDisplay = row.querySelector(".line-total");

        if (!productSelect || !quantityInput) {
            return 0;
        }

        const selectedOption = productSelect.options[productSelect.selectedIndex];
        const price = parseFloat(selectedOption?.dataset.price || 0);
        const quantity = parseInt(quantityInput.value || 0, 10);
        const lineTotal = price * quantity;

        if (priceDisplay) {
            priceDisplay.textContent = formatMoney(price);
        }

        if (totalDisplay) {
            totalDisplay.textContent = formatMoney(lineTotal);
        }

        return lineTotal;
    }

    function calculateSale() {
        let subtotal = 0;

        itemRows.querySelectorAll(".item-row").forEach(function (row) {
            if (row.style.display !== "none") {
                subtotal += calculateRow(row);
            }
        });

        const discount = parseFloat(discountInput.value || 0);
        const tax = parseFloat(taxInput.value || 0);
        const amountPaid = parseFloat(amountPaidInput.value || 0);
        const total = subtotal - discount + tax;
        const balance = total - amountPaid;

        const values = {
            subtotal,
            "discount-display": discount,
            "tax-display": tax,
            total,
            "paid-display": amountPaid,
            balance,
        };

        Object.entries(values).forEach(function ([id, value]) {
            const element = document.getElementById(id);

            if (element) {
                element.textContent = formatMoney(value);
            }
        });
    }

    itemRows.addEventListener("change", function (event) {
        if (event.target.matches("select[name$='product']")) {
            calculateSale();
        }
    });

    itemRows.addEventListener("input", function (event) {
        if (event.target.matches("input[name$='quantity']")) {
            calculateSale();
        }
    });

    [discountInput, taxInput, amountPaidInput].forEach(function (input) {
        input.addEventListener("input", calculateSale);
    });

    addProductButton.addEventListener("click", function () {
        itemRows.appendChild(createNewRow());
        calculateSale();
    });

    itemRows.addEventListener("click", function (event) {
        if (!event.target.classList.contains("delete-row")) {
            return;
        }

        const row = event.target.closest(".item-row");
        const deleteInput = row?.querySelector("input[name$='DELETE']");

        if (!row) {
            return;
        }

        if (deleteInput) {
            deleteInput.value = "on";
            row.style.display = "none";
        } else {
            row.remove();
        }

        calculateSale();
    });

    function addProductToCart(product) {
        for (const row of itemRows.querySelectorAll(".item-row")) {
            if (row.style.display === "none") {
                continue;
            }

            const productSelect = row.querySelector("select[name$='product']");
            const quantityInput = row.querySelector("input[name$='quantity']");

            if (productSelect?.value == product.id) {
                quantityInput.value = parseInt(quantityInput.value || 0, 10) + 1;
                calculateSale();
                return;
            }
        }

        const newRow = createNewRow();
        const productSelect = newRow.querySelector("select[name$='product']");
        const quantityInput = newRow.querySelector("input[name$='quantity']");
        const priceDisplay = newRow.querySelector(".selling-price");
        const totalDisplay = newRow.querySelector(".line-total");

        productSelect.value = product.id;
        quantityInput.value = 1;

        if (priceDisplay) {
            priceDisplay.textContent = formatMoney(product.selling_price);
        }

        if (totalDisplay) {
            totalDisplay.textContent = formatMoney(product.selling_price);
        }

        itemRows.appendChild(newRow);
        calculateSale();
    }

    async function scanBarcode() {
        const barcode = barcodeInput.value.trim();

        if (!barcode) {
            return;
        }

        barcodeMessage.textContent = "Searching...";

        try {
            const response = await fetch(
                `/sales/product-by-barcode/?barcode=${encodeURIComponent(barcode)}`,
            );
            const data = await response.json();

            if (!response.ok || !data.success) {
                barcodeMessage.textContent =
                    data.message || "Product not found.";
                barcodeInput.select();
                return;
            }

            addProductToCart(data.product);
            barcodeInput.value = "";
            barcodeMessage.textContent = `${data.product.name} added.`;
            barcodeInput.focus();
        } catch (error) {
            barcodeMessage.textContent = "Unable to search for product.";
            console.error(error);
        }
    }

    if (barcodeInput && scanBarcodeButton && barcodeMessage) {
        scanBarcodeButton.addEventListener("click", scanBarcode);
        barcodeInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                scanBarcode();
            }
        });
    }

    calculateSale();
}

function initPurchaseForm() {
    const addButton = document.getElementById("add-item");
    const itemsContainer = document.getElementById("purchase-items");
    const totalForms = document.querySelector('input[name$="-TOTAL_FORMS"]');
    const emptyForm = document.getElementById("empty-form");
    const totalDisplay = document.getElementById("purchase-total");

    if (
        !addButton ||
        !itemsContainer ||
        !totalForms ||
        !emptyForm ||
        !totalDisplay
    ) {
        return;
    }

    function calculateTotal() {
        let total = 0;

        itemsContainer.querySelectorAll(".purchase-item").forEach(function (item) {
            const quantityInput = item.querySelector(
                'input[name$="-quantity"]',
            );
            const costInput = item.querySelector(
                'input[name$="-cost_price"]',
            );
            const subtotalCell = item.querySelector(".item-subtotal");

            if (!quantityInput || !costInput) {
                return;
            }

            const subtotal =
                (parseFloat(quantityInput.value) || 0) *
                (parseFloat(costInput.value) || 0);

            if (subtotalCell) {
                subtotalCell.textContent = subtotal.toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                });
            }

            total += subtotal;
        });

        totalDisplay.textContent = total.toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    addButton.addEventListener("click", function () {
        const formIndex = parseInt(totalForms.value, 10);
        const newForm = emptyForm.outerHTML.replace(
            /__prefix__/g,
            formIndex,
        );

        itemsContainer.insertAdjacentHTML("beforeend", newForm);
        totalForms.value = formIndex + 1;
        calculateTotal();
    });

    itemsContainer.addEventListener("click", function (event) {
        if (!event.target.classList.contains("remove-item")) {
            return;
        }

        const item = event.target.closest(".purchase-item");

        if (item) {
            item.remove();
            calculateTotal();
        }
    });

    itemsContainer.addEventListener("input", function (event) {
        if (
            event.target.matches(
                'input[name$="-quantity"], input[name$="-cost_price"]',
            )
        ) {
            calculateTotal();
        }
    });

    calculateTotal();
}

function readJsonScript(id, fallback) {
    const element = document.getElementById(id);

    if (!element) {
        return fallback;
    }

    try {
        return JSON.parse(element.textContent);
    } catch (error) {
        console.error(`Unable to read chart data from ${id}.`, error);
        return fallback;
    }
}

function initFinancialChart() {
    const canvas = document.getElementById("financialChart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const values = [
        "financial-revenue-data",
        "financial-cogs-data",
        "financial-expenses-data",
        "financial-gross-profit-data",
        "financial-net-profit-data",
    ].map(function (id) {
        return Number(readJsonScript(id, 0));
    });

    new Chart(canvas, {
        type: "bar",
        data: {
            labels: ["Revenue", "COGS", "Expenses", "Gross Profit", "Net Profit"],
            datasets: [
                {
                    label: "Amount (UGX)",
                    data: values,
                    borderWidth: 1,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return `UGX ${Number(value).toLocaleString()}`;
                        },
                    },
                },
            },
        },
    });
}

function initInventoryChart() {
    const canvas = document.getElementById("movementChart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    const labels = readJsonScript("movement-labels-data", []);
    const received = readJsonScript("movement-received-data", []);
    const sold = readJsonScript("movement-sold-data", []);

    new Chart(canvas, {
        type: "bar",
        data: {
            labels,
            datasets: [
                { label: "Received", data: received, borderWidth: 1 },
                { label: "Sold", data: sold, borderWidth: 1 },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true },
            },
            scales: {
                y: { beginAtZero: true },
            },
        },
    });
}

function initAdministratorCharts() {
    if (typeof Chart === "undefined") {
        return;
    }

    const signupCanvas = document.getElementById("signupChart");
    const roleCanvas = document.getElementById("roleChart");
    const signupLabels = readJsonScript("signup-labels-data", []);
    const signupCounts = readJsonScript("signup-counts-data", []);
    const roleLabels = readJsonScript("role-labels-data", []);
    const roleCounts = readJsonScript("role-counts-data", []);

    if (signupCanvas) {
        new Chart(signupCanvas, {
            type: "line",
            data: {
                labels: signupLabels,
                datasets: [
                    {
                        label: "New Sign-ups",
                        data: signupCounts,
                        borderWidth: 2,
                        fill: false,
                        tension: 0.3,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: "index",
                },
                plugins: {
                    legend: { display: true },
                },
                scales: {
                    x: {
                        title: { display: true, text: "Date" },
                    },
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "New Users" },
                        ticks: { precision: 0 },
                    },
                },
            },
        });
    }

    if (roleCanvas) {
        new Chart(roleCanvas, {
            type: "doughnut",
            data: {
                labels: roleLabels,
                datasets: [
                    {
                        label: "Users",
                        data: roleCounts,
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "60%",
                plugins: {
                    legend: { position: "right" },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.label || "";
                                const value = context.raw || 0;
                                return `${label}: ${value} users`;
                            },
                        },
                    },
                },
            },
        });
    }
}

document.addEventListener("DOMContentLoaded", function () {
    initSidebar();
    initThemeSettings();
    initPrintButtons();
    initNotificationButton();
    initManagerDashboard();
    initSaleForm();
    initPurchaseForm();
    initFinancialChart();
    initInventoryChart();
    initAdministratorCharts();
});