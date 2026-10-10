const API_URL = window.location.protocol === "file:"
    ? "http://127.0.0.1:8000"
    : window.location.origin;

if (window.location.protocol === "file:") {
    window.location.replace(`${API_URL}/frontend/index.html`);
}

let isRedirectingToLogin = false;

const incidentList = document.getElementById("incident-list");
const loadMoreButton = document.getElementById("load-more-incidents");
const loadMoreLabel = document.getElementById("load-more-label");
const deleteAllIncidentsButton = document.getElementById("delete-all-incidents");
const videoStream = document.getElementById("video-stream");
const cameraSourceSelect = document.getElementById("camera-source");
const cameraSourceStatus = document.getElementById("camera-source-status");

const cameraConnectionStatus = document.getElementById("camera-connection-status");
const reconnectCameraButton = document.getElementById("reconnect-camera");

let cameraStatusTimer = null;
let cameraStatusRequestInProgress = false;

const zoneCanvas = document.getElementById("zone-canvas");
const zoneStatus = document.getElementById("zone-status");
const saveZoneButton = document.getElementById("save-zone");
const clearZoneButton = document.getElementById("clear-zone");

const incidentStatisticsRefreshInterval = 10000;
let videoWidth = 0;
let videoHeight = 0;
const zonePoints = [];
const incidentsPerBatch = 5;
let incidents = [];
let totalIncidentCount = 0;
let hasMoreIncidents = false;
let isLoadingMoreIncidents = false;
let isRefreshingIncidents = false;


let hasLoadedIncidentsOnce = false;
const notifiedIncidentIds = new Set();

function showIncidentNotification(incident) {
    const type = String(incident.violation_type || "").toLowerCase();

    let message;
    let color;
    let icon;

    if (type === "restricted_zone_entry_without_ppe") {
        message = "Person entered without PPE kit";
        color = "#dc2626";
        icon = "🚨";
    } else if (type === "restricted_zone_entry_with_ppe") {
        message = "Person entered with PPE kit";
        color = "#16a34a";
        icon = "✅";
    } else if (type === "restricted_zone_entry_partial_ppe") {
        message = incident.message ||
            "Person entered with incomplete PPE";
        color = "#ca8a04";
        icon = "⚠️";
    }

     else {
        return;
    }

    let container = document.getElementById("incident-notifications");

    if (!container) {
        container = document.createElement("div");
        container.id = "incident-notifications";

        Object.assign(container.style, {
            position: "fixed",
            top: "20px",
            right: "20px",
            zIndex: "9999",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            width: "min(380px, calc(100vw - 40px))"
        });

        document.body.appendChild(container);
    }

    const notification = document.createElement("div");

    Object.assign(notification.style, {
        background: "rgba(12, 20, 32, 0.92)",
        color: "#f1f6ff",
        padding: "15px 17px",
        borderRadius: "14px",
        border: `1px solid ${color}80`,
        borderLeft: `3px solid ${color}`,
        boxShadow: "0 18px 45px rgba(0,0,0,0.38)",
        backdropFilter: "blur(18px) saturate(140%)",
        WebkitBackdropFilter: "blur(18px) saturate(140%)",
        fontWeight: "600",
        fontSize: "13px",
        lineHeight: "1.5"
    });

    notification.textContent = `${icon} ${message} | Incident #${incident.id}`;
    container.appendChild(notification);

    window.setTimeout(() => {
        notification.remove();

        if (container.childElementCount === 0) {
            container.remove();
        }
    }, 6000);
}



async function requestJSON(path, options) {
    const response = await fetch(`${API_URL}${path}`, {
        credentials: "include",
        ...options
    });
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        if (response.status === 401 && !isRedirectingToLogin) {
            isRedirectingToLogin = true;
            window.location.replace("auth.html");
        }
        throw new Error(data.detail || `Request failed (${response.status})`);
    }

    return data;
}


function escapeHTML(value) {
    const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#39;"
    };

    return String(value ?? "").replace(/[&<>"']/g, character => entities[character]);
}


async function loadIncidents() {
    try {
        const data = await requestJSON(
            `/api/incidents/page?limit=${incidentsPerBatch}`
        );

        if (!Array.isArray(data.items)) {
            throw new Error("Unexpected incidents response");
        }

        totalIncidentCount = Number(data.total) || 0;
        hasMoreIncidents = Boolean(data.has_more);
        incidents = data.items;

        notifiedIncidentIds.clear();
        incidents.forEach(incident => {
            notifiedIncidentIds.add(String(incident.id));
        });

        hasLoadedIncidentsOnce = true;

        updateStatistics(data);
        displayIncidents(incidents);
    } catch (error) {
        console.error("Error loading incidents:", error);
        incidentList.innerHTML = '<div class="error">Unable to load incidents.</div>';
        loadMoreButton.hidden = true;
    }
}


async function refreshRecentIncidents() {
    if (document.hidden || isRefreshingIncidents || isLoadingMoreIncidents) {
        return;
    }

    isRefreshingIncidents = true;

    try {
        const refreshLimit = Math.max(
            incidentsPerBatch,
            Math.min(incidents.length, 100)
        );
        const summary = await requestJSON(
            `/api/incidents/page?limit=${refreshLimit}`,
            { cache: "no-store" }
        );

        
        if (hasLoadedIncidentsOnce) {
            for (const incident of summary.items) {
                const incidentId = String(incident.id);

                if (!notifiedIncidentIds.has(incidentId)) {
                    notifiedIncidentIds.add(incidentId);
                    showIncidentNotification(incident);
                }
            }
        }


        const visibleOlderIncidents = incidents.slice(summary.items.length);
        const refreshedIds = new Set(summary.items.map(item => String(item.id)));
        incidents = [
            ...summary.items,
            ...visibleOlderIncidents.filter(item => !refreshedIds.has(String(item.id)))
        ];
        totalIncidentCount = Number(summary.total) || 0;
        hasMoreIncidents = Boolean(summary.has_more) || incidents.length < totalIncidentCount;
        updateStatistics(summary);
        displayIncidents(incidents);
    } catch (error) {
        console.error("Error refreshing recent incidents:", error);
    } finally {
        isRefreshingIncidents = false;
    }
}



function updateStatistics(summary) {
    document.getElementById("total-incidents").textContent =
        summary.total ?? 0;

    const redIncidents = incidents.filter(incident =>
        String(incident.violation_type || "").toLowerCase() ===
        "restricted_zone_entry_without_ppe"
    );

    const needsAttentionCount = redIncidents.filter(incident =>
        String(incident.status || "").toLowerCase() === "open"
    ).length;

    document.getElementById("open-incidents").textContent =
        needsAttentionCount;

    deleteAllIncidentsButton.disabled =
        Number(summary.total) === 0;
}



function renderIncident(incident) {
    const timestampValue = String(incident.timestamp ?? "");
    const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestampValue);
    const date = new Date(hasTimezone ? timestampValue : `${timestampValue}Z`);
    
    const timestamp = Number.isNaN(date.getTime())
        ? "Unknown"
        : date.toLocaleString(undefined, { timeZone: "Asia/Kolkata" });

    const confidence = Number(incident.confidence);
    const confidenceText = Number.isFinite(confidence)
        ? `${(confidence * 100).toFixed(1)}%`
        : "N/A";

    const type = String(incident.violation_type || "").toLowerCase();
    let incidentColor = "#43d3c2";
    let incidentBorder = "rgba(67, 211, 194, 0.3)";
    let incidentBackground = "rgba(67, 211, 194, 0.06)";
    let incidentIcon = "ℹ️";

    if (type === "restricted_zone_entry_without_ppe") {
        incidentColor = "#dc2626";
        incidentBorder = "rgba(220, 38, 38, 0.6)";
        incidentBackground = "rgba(220, 38, 38, 0.08)";
        incidentIcon = "🚨";
    } else if (type === "restricted_zone_entry_with_ppe") {
        incidentColor = "#16a34a";
        incidentBorder = "rgba(22, 163, 74, 0.6)";
        incidentBackground = "rgba(22, 163, 74, 0.08)";
        incidentIcon = "✅";
    } else if (type === "restricted_zone_entry_partial_ppe") {
        incidentColor = "#ca8a04";
        incidentBorder = "rgba(202, 138, 4, 0.6)";
        incidentBackground = "rgba(202, 138, 4, 0.08)";
        incidentIcon = "⚠️";
    }

    let incidentMessage;

    if (type === "restricted_zone_entry_with_ppe") {
        incidentMessage = "Person entered with PPE kit";
    } else if (incident.message) {
        incidentMessage = incident.message;
    } else if (type === "restricted_zone_entry_without_ppe") {
        incidentMessage = "Person entered without PPE kit";
    } else if (type === "restricted_zone_entry_partial_ppe") {
        incidentMessage = "Person entered with incomplete PPE";
    } else {
        incidentMessage = type || "Unknown incident";
    }

    return `
        <article
            class="incident-card"
            data-incident-id="${escapeHTML(incident.id)}"
            style="
                border-left: 5px solid ${incidentBorder};
                background-color: ${incidentBackground};
            "
        >
            <div class="incident-header">
                <h3 style="color: ${incidentColor};">
                    ${incidentIcon} ${escapeHTML(incidentMessage)}
                </h3>

                <div class="incident-actions">
                    <span class="status">
                        ${escapeHTML(incident.status || "unknown")}
                    </span>

                    <button
                        class="delete-incident-button"
                        type="button"
                        data-incident-id="${escapeHTML(incident.id)}"
                        aria-label="Delete incident ${escapeHTML(incident.id)}"
                    >Delete</button>
                </div>
            </div>

            <div class="incident-details">
                <p><strong>Incident ID:</strong> ${escapeHTML(incident.id)}</p>
                <p><strong>Person ID:</strong> ${escapeHTML(incident.person_track_id)}</p>
                <p><strong>Confidence:</strong> ${confidenceText}</p>
                <p><strong>Time:</strong> ${escapeHTML(timestamp)}</p>
            </div>

            <div class="evidence">
                <p><strong>Original:</strong> ${escapeHTML(incident.snapshot_path || "Unavailable")}</p>
                <p><strong>Annotated:</strong> ${escapeHTML(incident.annotated_snapshot_path || "Unavailable")}</p>
            </div>
        </article>
    `;
}


async function deleteIncident(button) {
    const incidentId = button.dataset.incidentId;

    if (!incidentId || !window.confirm(`Delete incident ${incidentId}? This cannot be undone.`)) {
        return;
    }

    button.disabled = true;

    try {
        await requestJSON(`/api/incidents/${encodeURIComponent(incidentId)}`, {
            method: "DELETE"
        });

        const incident = incidents.find(item => String(item.id) === incidentId);
        const card = button.closest(".incident-card");
        card?.remove();
        incidents = incidents.filter(item => String(item.id) !== incidentId);

        if (incident) {
            totalIncidentCount = Math.max(0, totalIncidentCount - 1);
            const openCount = Number(document.getElementById("open-incidents").textContent) || 0;
            const updatedOpenCount = incident.status === "open"
                ? Math.max(0, openCount - 1)
                : openCount;

            updateStatistics({
                total: totalIncidentCount,
                open: updatedOpenCount
            });
        }

        if (incidents.length === 0 && hasMoreIncidents) {
            await loadIncidents();
        } else if (incidents.length === 0) {
            incidentList.innerHTML = '<div class="empty">No incidents recorded yet.</div>';
            updateLoadMoreButton();
        }
    } catch (error) {
        console.error("Error deleting incident:", error);
        window.alert(`Unable to delete incident: ${error.message}`);
        button.disabled = false;
    }
}


async function deleteAllIncidents() {
    if (totalIncidentCount === 0 || !window.confirm(
        `Delete all ${totalIncidentCount} incidents? This cannot be undone.`
    )) {
        return;
    }

    deleteAllIncidentsButton.disabled = true;

    try {
        await requestJSON("/api/incidents/", { method: "DELETE" });
        incidents = [];
        totalIncidentCount = 0;
        hasMoreIncidents = false;
        updateStatistics({ total: 0, open: 0 });
        displayIncidents(incidents);
    } catch (error) {
        console.error("Error deleting all incidents:", error);
        window.alert(`Unable to delete all incidents: ${error.message}`);
        deleteAllIncidentsButton.disabled = totalIncidentCount === 0;
    }
}


function updateLoadMoreButton() {
    loadMoreButton.hidden = !hasMoreIncidents;

    if (hasMoreIncidents) {
        loadMoreLabel.textContent = "Show more incidents";
        loadMoreButton.setAttribute("aria-label", "Show more incidents");
    }
}


async function showMoreIncidents() {
    if (isLoadingMoreIncidents || !hasMoreIncidents) {
        return;
    }

    isLoadingMoreIncidents = true;
    loadMoreButton.disabled = true;
    loadMoreLabel.textContent = "Loading incidents...";

    try {
        const lastIncidentId = incidents[incidents.length - 1]?.id;
        const data = await requestJSON(
            `/api/incidents/page?before_id=${encodeURIComponent(lastIncidentId)}&limit=${incidentsPerBatch}`
        );

        if (!Array.isArray(data.items)) {
            throw new Error("Unexpected incidents response");
        }

        incidentList.insertAdjacentHTML(
            "beforeend",
            data.items.map(renderIncident).join("")
        );
        incidents.push(...data.items);
        totalIncidentCount = Number(data.total) || totalIncidentCount;
        hasMoreIncidents = Boolean(data.has_more);
        updateStatistics(data);
        updateLoadMoreButton();
    } catch (error) {
        console.error("Error loading more incidents:", error);
        loadMoreLabel.textContent = "Retry loading incidents";
        loadMoreButton.setAttribute("aria-label", "Retry loading incidents");
    } finally {
        isLoadingMoreIncidents = false;
        loadMoreButton.disabled = false;
    }
}


function displayIncidents(incidentRecords) {
    incidents = incidentRecords;

    if (incidents.length === 0) {
        incidentList.innerHTML = '<div class="empty">No incidents recorded yet.</div>';
        updateLoadMoreButton();
        return;
    }

    incidentList.replaceChildren();
    incidentList.insertAdjacentHTML(
        "beforeend",
        incidents.map(renderIncident).join("")
    );
    updateLoadMoreButton();
}


loadMoreButton.addEventListener("click", showMoreIncidents);
deleteAllIncidentsButton.addEventListener("click", deleteAllIncidents);
incidentList.addEventListener("click", event => {
    const button = event.target.closest(".delete-incident-button");

    if (button) {
        deleteIncident(button);
    }
});


function setZoneStatus(message) {
    if (zoneStatus) {
        zoneStatus.textContent = message;
    }


    async function initializeAccount() {
        const accountName = document.getElementById("account-name");
        const logoutButton = document.getElementById("logout-button");
        const accountLinks = document.querySelectorAll(".header-auth-links a");

        try {
            const user = await requestJSON("/api/auth/me");
            accountName.textContent = `Signed in as ${user.name}`;
            accountName.hidden = false;
            logoutButton.hidden = false;
            accountLinks.forEach(link => {
                link.hidden = true;
            });
        } catch (error) {
            if (!isRedirectingToLogin) {
                console.error("Unable to load account:", error);
            }
        }
    }


    document.getElementById("logout-button").addEventListener("click", async () => {
        const logoutButton = document.getElementById("logout-button");
        logoutButton.disabled = true;
        try {
            await requestJSON("/api/auth/logout", { method: "POST" });
            window.location.assign("auth.html");
        } catch (error) {
            console.error("Unable to sign out:", error);
            window.alert(`Unable to sign out: ${error.message}`);
            logoutButton.disabled = false;
        }
    });
}


function setupZoneCanvas() {
    if (!zoneCanvas || videoWidth <= 0 || videoHeight <= 0) {
        return;
    }

    const videoBounds = videoStream.getBoundingClientRect();

    if (videoBounds.width <= 0 || videoBounds.height <= 0) {
        return;
    }

    const scale = Math.min(
        videoBounds.width / videoWidth,
        videoBounds.height / videoHeight
    );
    const displayWidth = videoWidth * scale;
    const displayHeight = videoHeight * scale;

    zoneCanvas.style.left = `${(videoBounds.width - displayWidth) / 2}px`;
    zoneCanvas.style.top = `${(videoBounds.height - displayHeight) / 2}px`;
    zoneCanvas.style.width = `${displayWidth}px`;
    zoneCanvas.style.height = `${displayHeight}px`;

    if (zoneCanvas.width !== videoWidth || zoneCanvas.height !== videoHeight) {
        zoneCanvas.width = videoWidth;
        zoneCanvas.height = videoHeight;
    }

    drawZone();
}


function drawZone() {
    if (!zoneCanvas || videoWidth <= 0 || videoHeight <= 0) {
        return;
    }

    const context = zoneCanvas.getContext("2d");
    context.clearRect(0, 0, zoneCanvas.width, zoneCanvas.height);

    if (zonePoints.length === 0) {
        return;
    }

    context.beginPath();
    context.moveTo(zonePoints[0][0], zonePoints[0][1]);

    for (const [x, y] of zonePoints.slice(1)) {
        context.lineTo(x, y);
    }

    if (zonePoints.length >= 3) {
        context.closePath();
        context.fillStyle = "rgba(255, 0, 0, 0.15)";
        context.fill();
    }

    context.strokeStyle = "red";
    context.lineWidth = Math.max(2, videoWidth / 640);
    context.stroke();

    for (const [x, y] of zonePoints) {
        context.beginPath();
        context.arc(x, y, Math.max(4, videoWidth / 384), 0, Math.PI * 2);
        context.fillStyle = "red";
        context.fill();
    }
}


async function loadVideoInfo(source = getSelectedCameraSource()) {
    try {
        const data = await requestJSON(`/api/video/info?source=${encodeURIComponent(source)}`);
        const width = Number(data.width);
        const height = Number(data.height);

        if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
            throw new Error(data.error || "Invalid video dimensions");
        }

        videoWidth = width;
        videoHeight = height;
        setupZoneCanvas();
    } catch (error) {
        console.error("Failed to load video information:", error);
        setZoneStatus(`Unable to load video dimensions for ${source === "phone" ? "phone camera" : "local video"}.`);
    }
}


function getSelectedCameraSource() {
    return cameraSourceSelect?.value === "phone" ? "phone" : "local";
}



async function switchCameraSource() {
    const source = getSelectedCameraSource();
    const label = source === "phone"
        ? "Phone Camera (RTSP)"
        : "Local Test Video";

    if (cameraSourceStatus) {
        cameraSourceStatus.textContent = `Connecting to ${label}...`;
    }

    if (cameraConnectionStatus) {
        cameraConnectionStatus.textContent = "Connecting...";
        cameraConnectionStatus.className =
            "connection-status status-connecting";
    }

    setZoneStatus("Switching camera feed...");

    // Clear unsaved zone points when changing cameras.
    zonePoints.length = 0;
    drawZone();

    // Force the browser to open a fresh video stream.
    if (videoStream) {
        videoStream.src =
            `${API_URL}/api/video/stream?source=${encodeURIComponent(source)}&t=${Date.now()}`;
    }

    await loadVideoInfo(source);

    if (cameraSourceStatus) {
        cameraSourceStatus.textContent = `${label} selected`;
    }

    setZoneStatus(
        "Camera switched. Re-draw and save the restricted zone if needed."
    );

    startCameraStatusPolling();
}



async function loadSavedZone() {
    try {
        const data = await requestJSON("/api/zone/");
        const points = Array.isArray(data.points) ? data.points : [];

        zonePoints.splice(0, zonePoints.length, ...points.filter(
            point => Array.isArray(point) && point.length >= 2 &&
                Number.isFinite(Number(point[0])) && Number.isFinite(Number(point[1]))
        ).map(point => [Number(point[0]), Number(point[1])]));

        drawZone();
        setZoneStatus(
            zonePoints.length >= 3
                ? "Saved restricted zone loaded."
                : "No saved restricted zone."
        );
    } catch (error) {
        console.error("Failed to load restricted zone:", error);
        setZoneStatus("Unable to load the saved restricted zone.");
    }
}


async function saveZone() {
    if (zonePoints.length < 3) {
        setZoneStatus("Select at least 3 points.");
        return;
    }

    saveZoneButton.disabled = true;

    try {
        const data = await requestJSON("/api/zone/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ points: zonePoints })
        });

        if (Array.isArray(data.points)) {
            zonePoints.splice(
                0,
                zonePoints.length,
                ...data.points.map(point => [Number(point[0]), Number(point[1])])
            );
        }

        drawZone();
        setZoneStatus("Restricted zone saved and displayed.");
    } catch (error) {
        console.error("Failed to save restricted zone:", error);
        setZoneStatus(`Failed to save restricted zone: ${error.message}`);
    } finally {
        saveZoneButton.disabled = false;
    }
}


async function clearZone() {
    clearZoneButton.disabled = true;

    try {
        await requestJSON("/api/zone/", { method: "DELETE" });
        zonePoints.length = 0;
        drawZone();
        setZoneStatus("Restricted zone cleared.");
    } catch (error) {
        console.error("Failed to clear restricted zone:", error);
        setZoneStatus(`Failed to clear restricted zone: ${error.message}`);
    } finally {
        clearZoneButton.disabled = false;
    }
}


if (zoneCanvas) {
    zoneCanvas.addEventListener("click", event => {
        if (videoWidth <= 0 || videoHeight <= 0) {
            setZoneStatus("Video dimensions are not ready yet.");
            return;
        }

        const bounds = zoneCanvas.getBoundingClientRect();
        const displayX = event.clientX - bounds.left;
        const displayY = event.clientY - bounds.top;

        if (bounds.width <= 0 || bounds.height <= 0 || displayX < 0 || displayY < 0 ||
            displayX > bounds.width || displayY > bounds.height) {
            return;
        }

        const x = Math.min(videoWidth - 1, Math.round(displayX * videoWidth / bounds.width));
        const y = Math.min(videoHeight - 1, Math.round(displayY * videoHeight / bounds.height));
        zonePoints.push([x, y]);
        drawZone();
        setZoneStatus(`${zonePoints.length} points selected`);
    });
}


async function refreshCameraStatus() {
    if (cameraStatusRequestInProgress || document.hidden) {
        return;
    }

    cameraStatusRequestInProgress = true;
    const source = getSelectedCameraSource();

    try {
        const data = await requestJSON(
            `/api/video/status?source=${encodeURIComponent(source)}`,
            { cache: "no-store" }
        );

        // Ignore the response if the user has switched cameras.
        if (source !== getSelectedCameraSource()) {
            return;
        }

        const status = String(data.status || "unknown").toLowerCase();

        const labels = {
            idle: "Idle",
            connecting: "Connecting",
            connected: "Connected",
            reconnecting: "Reconnecting",
            disconnected: "Disconnected",
            ended: "Video ended",
            error: "Error",
            unknown: "Unknown"
        };

        const safeStatus = Object.prototype.hasOwnProperty.call(
            labels,
            status
        ) ? status : "unknown";

        if (cameraConnectionStatus) {
            cameraConnectionStatus.textContent = labels[safeStatus];
            cameraConnectionStatus.className =
                `connection-status status-${safeStatus}`;
            cameraConnectionStatus.title = data.message || "";
        }
    } catch (error) {
        if (cameraConnectionStatus) {
            cameraConnectionStatus.textContent = "Unavailable";
            cameraConnectionStatus.className =
                "connection-status status-unavailable";
            cameraConnectionStatus.title = error.message;
        }
    } finally {
        cameraStatusRequestInProgress = false;
    }
}


function startCameraStatusPolling() {
    if (cameraStatusTimer !== null) {
        window.clearInterval(cameraStatusTimer);
    }

    refreshCameraStatus();

    // Refresh the connection indicator every two seconds.
    cameraStatusTimer = window.setInterval(
        refreshCameraStatus,
        2000
    );
}


function reconnectCamera() {
    const source = getSelectedCameraSource();

    if (cameraConnectionStatus) {
        cameraConnectionStatus.textContent = "Reconnecting...";
        cameraConnectionStatus.className =
            "connection-status status-reconnecting";
    }

    if (videoStream) {
        videoStream.src =
            `${API_URL}/api/video/stream?source=${encodeURIComponent(source)}&t=${Date.now()}`;
    }

    startCameraStatusPolling();
}


if (cameraSourceSelect) {
    cameraSourceSelect.addEventListener(
        "change",
        switchCameraSource
    );
}

if (reconnectCameraButton) {
    reconnectCameraButton.addEventListener(
        "click",
        reconnectCamera
    );
}

startCameraStatusPolling();

document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
        refreshCameraStatus();
    }
});

if (videoStream) {
    videoStream.addEventListener("error", () => {
        if (cameraSourceStatus) {
            cameraSourceStatus.textContent = "Stream unavailable — check the phone connection and API server";
        }
        setZoneStatus("Video stream could not be loaded. Check that the selected source is reachable.");
    });

    videoStream.addEventListener("load", () => {
        if (videoStream.naturalWidth > 0 && videoStream.naturalHeight > 0) {
            videoWidth = videoStream.naturalWidth;
            videoHeight = videoStream.naturalHeight;
            setupZoneCanvas();
        }
    });
}


if (saveZoneButton) {
    saveZoneButton.addEventListener("click", saveZone);
}

if (clearZoneButton) {
    clearZoneButton.addEventListener("click", clearZone);
}

window.addEventListener("resize", setupZoneCanvas);
window.setInterval(refreshRecentIncidents, incidentStatisticsRefreshInterval);
document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
        refreshRecentIncidents();
    }
});

initializeAccount();
loadIncidents();
loadVideoInfo("phone").then(loadSavedZone);
