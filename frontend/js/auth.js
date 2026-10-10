const authTabs = document.querySelectorAll("[data-auth-mode]");
const loginForm = document.getElementById("login-panel");
const registerForm = document.getElementById("register-panel");
const authTitle = document.getElementById("auth-title");
const authDescription = document.getElementById("auth-description");
const authStatus = document.getElementById("auth-status");
const registerPassword = document.getElementById("register-password");
const confirmPassword = document.getElementById("register-confirm-password");
const API_URL = window.location.protocol === "file:"
    ? "http://127.0.0.1:8000"
    : window.location.origin;

if (window.location.protocol === "file:") {
    window.location.replace(`${API_URL}/frontend/auth.html${window.location.hash}`);
}

function setAuthMode(mode) {
    const isRegistering = mode === "register";

    loginForm.hidden = isRegistering;
    registerForm.hidden = !isRegistering;
    authTitle.textContent = isRegistering ? "Create your account" : "Sign in to your account";
    authDescription.textContent = isRegistering
        ? "Set up your account to access the monitoring workspace."
        : "Enter your details to access the monitoring dashboard.";
    authStatus.hidden = true;
    authStatus.textContent = "";

    authTabs.forEach(tab => {
        const isActive = tab.dataset.authMode === mode;
        tab.classList.toggle("is-active", isActive);
        tab.setAttribute("aria-selected", String(isActive));
        tab.tabIndex = isActive ? 0 : -1;
    });
}

authTabs.forEach(tab => {
    tab.addEventListener("click", () => {
        setAuthMode(tab.dataset.authMode);
        history.replaceState(null, "", tab.dataset.authMode === "register" ? "#register" : "#login");
    });
});

document.querySelector(".auth-tabs").addEventListener("keydown", event => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") {
        return;
    }

    event.preventDefault();
    const mode = event.key === "ArrowRight" ? "register" : "login";
    document.querySelector(`[data-auth-mode="${mode}"]`).focus();
    setAuthMode(mode);
});

registerForm.addEventListener("submit", event => {
    event.preventDefault();

    if (registerPassword.value !== confirmPassword.value) {
        confirmPassword.setCustomValidity("Passwords do not match.");
        confirmPassword.reportValidity();
        confirmPassword.addEventListener("input", () => confirmPassword.setCustomValidity(""), { once: true });
        return;
    }

    submitAuthForm("/api/auth/register", {
        name: document.getElementById("register-name").value,
        email: document.getElementById("register-email").value,
        password: registerPassword.value
    });
});

loginForm.addEventListener("submit", event => {
    event.preventDefault();
    submitAuthForm("/api/auth/login", {
        email: document.getElementById("login-email").value,
        password: document.getElementById("login-password").value
    });
});

async function submitAuthForm(path, credentials) {
    const submitButton = document.querySelector(
        `${path.endsWith("register") ? "#register-panel" : "#login-panel"} .auth-submit`
    );
    submitButton.disabled = true;
    submitButton.textContent = "Please wait...";
    authStatus.hidden = true;

    try {
        const response = await fetch(`${API_URL}${path}`, {
            method: "POST",
            credentials: "include",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(credentials)
        });
        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(result.detail || "Unable to sign in. Please try again.");
        }

        authStatus.textContent = result.message;
        authStatus.classList.add("is-success");
        authStatus.hidden = false;
        window.setTimeout(() => window.location.assign("index.html"), 700);
    } catch (error) {
        authStatus.textContent = error.message;
        authStatus.classList.remove("is-success");
        authStatus.hidden = false;
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = path.endsWith("register") ? "Create account" : "Sign in";
    }
}

setAuthMode(window.location.hash === "#register" ? "register" : "login");
