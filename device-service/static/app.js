const deviceList = document.getElementById("device-list");
const deviceCount = document.getElementById("device-count");
const formSection = document.getElementById("register-section");
const deviceForm = document.getElementById("device-form");
const message = document.getElementById("message");
let messageTimeout;

document.getElementById("show-form-button").addEventListener("click", () => {
    formSection.classList.remove("hidden");
});

document.getElementById("cancel-button").addEventListener("click", () => {
    formSection.classList.add("hidden");
    deviceForm.reset();
});

async function loadDevices() {
    try {
        const response = await fetch("/devices");

        if (!response.ok) {
            throw new Error("Could not load devices.");
        }

        const devices = await response.json();

        deviceCount.textContent =
            `${devices.length} device${devices.length === 1 ? "" : "s"}`;

        deviceList.innerHTML = "";

        if (devices.length === 0) {
            deviceList.innerHTML =
                '<div class="panel">No devices registered yet.</div>';
            return;
        }

        for (const device of devices) {
            await renderDevice(device);
        }
    } catch (error) {
        showMessage(error.message, true);
    }
}

async function renderDevice(device) {
    let health = null;

    try {
        const response = await fetch(`/devices/${device.id}/details`);

        if (response.ok) {
            const details = await response.json();
            health = details.health;
        }
    } catch (error) {
        console.error("Unable to retrieve device health:", error);
    }

    const card = document.createElement("article");
    card.className = "device-card";

    const status = health ? health.status : "NO DATA";
    const statusClass = ["ONLINE", "WARNING", "OFFLINE"].includes(status)
        ? status.toLowerCase()
        : "unknown";

    card.innerHTML = `
        <div class="card-header">
            <div>
                <h3>${escapeHtml(device.name)}</h3>
                <p>
                    ${escapeHtml(device.type)} ·
                    ${escapeHtml(device.location)}
                </p>
            </div>

            <span class="status ${statusClass}">
                ● ${escapeHtml(status)}
            </span>
        </div>

        <div class="device-info">
            <p>
                <strong>Software:</strong>
                ${escapeHtml(device.software_version)}
            </p>

            <p>
                <strong>IP:</strong>
                ${escapeHtml(device.ip_address)}
            </p>
        </div>

        <div class="metrics">
            <div>
                <span>CPU Usage</span>
                <strong>${health ? `${escapeHtml(health.cpu_usage)}%` : "—"}</strong>
            </div>

            <div>
                <span>Memory Usage</span>
                <strong>${health ? `${escapeHtml(health.memory_usage)}%` : "—"}</strong>
            </div>
        </div>
    `;

    deviceList.appendChild(card);
}

deviceForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const device = {
        name: document.getElementById("name").value,
        type: document.getElementById("type").value,
        location: document.getElementById("location").value,
        software_version:
            document.getElementById("software-version").value,
        ip_address:
            document.getElementById("ip-address").value
    };

    try {
        const response = await fetch("/devices", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(device)
        });

        if (!response.ok) {
            throw new Error("Device registration failed.");
        }

        deviceForm.reset();
        formSection.classList.add("hidden");

        showMessage("Device registered successfully.", false);

        await loadDevices();
    } catch (error) {
        showMessage(error.message, true);
    }
});

function showMessage(text, isError) {
    message.textContent = text;
    message.className = isError ? "message error" : "message success";

    clearTimeout(messageTimeout);
    messageTimeout = setTimeout(() => {
        message.textContent = "";
        message.className = "";
    }, 4000);
}

function escapeHtml(value) {
    const element = document.createElement("div");
    element.textContent = value;
    return element.innerHTML;
}

loadDevices();
