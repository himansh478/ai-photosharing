// Helpers shared by the photographer and guest pages.

const $ = (id) => document.getElementById(id);

function show(el, visible = true) {
    el.classList.toggle('hidden', !visible);
}

function showError(el, message) {
    el.textContent = message;
    show(el, true);
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Photos are resized in the browser before upload: far less data over a venue's
// network, and the server never has to handle 20 MB camera originals.
function compressionOptions(overrides) {
    return Object.assign({
        maxSizeMB: 1.5,
        maxWidthOrHeight: 2560,
        useWebWorker: true,
        // The worker loads the library from this server, not from a CDN.
        libURL: location.origin + '/static/vendor/browser-image-compression.js',
    }, overrides);
}

async function compressImage(file, overrides) {
    try {
        return await imageCompression(file, compressionOptions(overrides));
    } catch (e) {
        console.error('Compression failed for', file.name, e);
        return file; // fall back to the original
    }
}

// fetch() that understands this API's errors and waits out "starting up" and "slow down".
// onWait(message) is called while it is waiting so the page can say so.
async function apiFetch(url, options = {}, onWait) {
    const maxAttempts = options.retry === false ? 1 : 12;
    for (let attempt = 1; ; attempt++) {
        const res = await fetch(url, options);
        let data = {};
        try { data = await res.json(); } catch (e) { /* not JSON */ }

        const retriable = res.status === 503 || res.status === 429;
        if (retriable && attempt < maxAttempts) {
            const wait = Math.min(Number(res.headers.get('Retry-After')) || 10, 60);
            if (onWait) {
                onWait(res.status === 503
                    ? `The system is starting up. Retrying in ${wait} seconds…`
                    : `Too many requests. Retrying in ${wait} seconds…`);
            }
            await sleep(wait * 1000);
            continue;
        }
        if (!res.ok) {
            const error = new Error(data.error || `Request failed (${res.status})`);
            error.status = res.status;
            throw error;
        }
        return data;
    }
}

async function copyText(text, button) {
    try {
        await navigator.clipboard.writeText(text);
    } catch (e) {
        // Clipboard access can be blocked (e.g. inside an iframe); fall back to a prompt.
        window.prompt('Copy this:', text);
        return;
    }
    if (button) {
        const original = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => { button.textContent = original; }, 2000);
    }
}

function whatsappLink(text) {
    return 'https://wa.me/?text=' + encodeURIComponent(text);
}

function guestLink(code) {
    return `${location.origin}/user?code=${encodeURIComponent(code)}`;
}

// Small persistent store that never throws (storage can be unavailable in private windows).
const store = {
    get(key) {
        try { return JSON.parse(localStorage.getItem(key)); } catch (e) { return null; }
    },
    set(key, value) {
        try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* ignore */ }
    },
    remove(key) {
        try { localStorage.removeItem(key); } catch (e) { /* ignore */ }
    },
};
