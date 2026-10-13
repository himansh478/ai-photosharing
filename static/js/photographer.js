// Photographer / host page: create or join an event, upload photos, share the guest link.

const SAVED_EVENT = 'photoai.event';
const MAX_PHOTOS = 120;
const CHUNK_SIZE = 20;

// The event being worked on: { code, key, role ('host' | 'contributor'), eventName }
let current = null;
let selectedFiles = [];
let upload = null;      // { jobId, nextIndex } while an upload is in progress

function authHeaders() {
    return { 'X-Event-Key': current.key };
}

// ─── Step navigation ───
function goToStep(n) {
    ['panel1', 'panel2', 'panel3'].forEach((id, i) => {
        $(id).classList.toggle('active', i === n - 1);
        $(`step${i + 1}`).className = 'step' + (i < n - 1 ? ' done' : i === n - 1 ? ' active' : '');
    });
    if (n === 3) renderShare();
}

function switchMode(mode) {
    const isRegister = mode === 'register';
    show($('registerForm'), isRegister);
    show($('joinForm'), !isRegister);
    $('tabRegister').classList.toggle('active', isRegister);
    $('tabJoin').classList.toggle('active', !isRegister);
}

function setCurrent(event) {
    current = event;
    store.set(SAVED_EVENT, event);
}

// ─── Create a new event ───
async function registerEvent() {
    const name = $('pName').value.trim();
    const email = $('pEmail').value.trim();
    const event_name = $('pEventName').value.trim();
    const event_type = $('pEventType').value;
    const errEl = $('regError');
    show(errEl, false);

    if (!name || !email || !event_name) return showError(errEl, 'Please fill in all fields.');

    const btn = $('regBtn');
    btn.disabled = true;
    btn.textContent = 'Creating event...';
    try {
        const data = await apiFetch('/api/photographer/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, event_name, event_type }),
            retry: false,
        });
        setCurrent({ code: data.code, key: data.host_key, role: 'host', eventName: data.event_name });

        // The keys are shown exactly once; the server only keeps their hashes.
        $('hostKeyValue').textContent = data.host_key;
        $('contributorLinkValue').textContent = contributorLink(data.code, data.contributor_key);
        show($('keysCard'), true);
        goToStep(2);
    } catch (e) {
        showError(errEl, e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Event & Get Code';
    }
}

function contributorLink(code, contributorKey) {
    // The key sits after '#', which browsers never send to a server or write to its logs.
    return `${location.origin}/photographer?code=${encodeURIComponent(code)}#key=${contributorKey}`;
}

// ─── Join an existing event with a key ───
async function joinEvent(code, key, errEl) {
    show(errEl, false);
    if (!code || !key) return showError(errEl, 'Please enter the event code and your upload key.');

    const btn = $('joinBtn');
    btn.disabled = true;
    btn.textContent = 'Checking...';
    try {
        const data = await apiFetch(`/api/photographer/access?code=${encodeURIComponent(code)}`,
            { headers: { 'X-Event-Key': key }, retry: false });
        setCurrent({ code: data.code, key, role: data.role, eventName: data.event_name });
        show($('keysCard'), false);
        goToStep(2);
    } catch (e) {
        showError(errEl, e.status === 403 || e.status === 401
            ? 'That code and key do not match an event. Please check them.'
            : e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Join & Start Uploading';
    }
}

// ─── File selection ───
function handleFileSelect(files) {
    const errEl = $('uploadError');
    show(errEl, false);

    if (files.length > MAX_PHOTOS) {
        showError(errEl, `You can upload at most ${MAX_PHOTOS} photos at once. Please reduce your selection.`);
        $('fileInput').value = '';
        selectedFiles = [];
        show($('fileCount'), false);
        $('uploadBtn').disabled = true;
        return;
    }

    selectedFiles = Array.from(files).filter((f) => f.type.match(/^image\//));
    upload = null;
    const count = selectedFiles.length;
    show($('fileCount'), count > 0);
    $('fileCount').textContent = `${count} photo${count !== 1 ? 's' : ''} selected`;
    $('uploadBtn').disabled = count === 0;
    $('uploadBtn').textContent = 'Start Processing Photos';
    show($('uploadSummary'), false);
}

// ─── Upload ───
function setProgress(pct, label, sub) {
    show($('progressSection'), true);
    $('progressBar').style.width = pct + '%';
    $('progressLabel').textContent = label;
    $('progressSub').textContent = sub || '';
}

async function uploadPhotos() {
    if (!selectedFiles.length || !current) return;
    const btn = $('uploadBtn');
    const errEl = $('uploadError');
    show(errEl, false);
    show($('uploadSummary'), false);
    btn.disabled = true;
    btn.textContent = 'Uploading...';

    // A retry continues from the chunk that failed, into the same job.
    upload = upload || { jobId: null, nextIndex: 0 };
    const total = selectedFiles.length;

    while (upload.nextIndex < total) {
        const chunk = selectedFiles.slice(upload.nextIndex, upload.nextIndex + CHUNK_SIZE);
        setProgress(Math.round((upload.nextIndex / total) * 40),
            `Preparing photos ${upload.nextIndex + 1}–${upload.nextIndex + chunk.length} of ${total}…`);
        const prepared = await Promise.all(chunk.map((file) => compressImage(file)));

        const formData = new FormData();
        formData.append('code', current.code);
        if (upload.jobId) formData.append('job_id', upload.jobId);
        prepared.forEach((file, i) => formData.append('photos', file, chunk[i].name || 'photo.jpg'));

        try {
            const data = await apiFetch('/api/photographer/upload-batch',
                { method: 'POST', headers: authHeaders(), body: formData },
                (message) => setProgress(Math.round((upload.nextIndex / total) * 40), message));
            upload.jobId = data.job_id;
        } catch (e) {
            showError(errEl, 'Upload error: ' + e.message);
            btn.disabled = false;
            btn.textContent = 'Retry Upload';
            return;
        }

        upload.nextIndex += chunk.length;
        setProgress(Math.round((upload.nextIndex / total) * 40),
            `Uploaded ${upload.nextIndex} / ${total} photos`, 'Face detection is running in the background…');
    }

    await pollJob(upload.jobId);
}

async function pollJob(jobId) {
    for (;;) {
        let data;
        try {
            data = await apiFetch(`/api/photographer/batch-status/${jobId}`);
        } catch (e) {
            // A dropped connection should not lose the progress display; just try again.
            await sleep(3000);
            continue;
        }
        const total = data.total || 1;
        setProgress(40 + Math.round((data.processed / total) * 60),
            `Processing ${data.processed} / ${total} photos`,
            `With faces: ${data.uploaded} · For everyone: ${data.no_face} · Duplicates: ${data.duplicates} · Failed: ${data.failed}`);

        if (data.status === 'completed') {
            finishUpload(data);
            return;
        }
        await sleep(1500);
    }
}

function finishUpload(data) {
    setProgress(100, '✅ All photos processed', '');
    upload = null;
    selectedFiles = [];
    $('fileInput').value = '';
    show($('fileCount'), false);

    const summary = $('uploadSummary');
    summary.textContent = '';
    const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;
    const lines = [
        `${count(data.uploaded, 'photo with faces is', 'photos with faces are')} ready for guests to find.`,
        data.no_face ? `${count(data.no_face, 'photo', 'photos')} without faces went to the “For everyone” album.` : '',
        data.duplicates ? `${count(data.duplicates, 'photo was', 'photos were')} already uploaded and skipped.` : '',
        data.failed ? `${count(data.failed, 'file', 'files')} could not be processed:` : '',
    ].filter(Boolean);
    lines.forEach((text) => {
        const line = document.createElement('div');
        line.textContent = text;
        summary.appendChild(line);
    });
    if (data.failed_files && data.failed_files.length) {
        const list = document.createElement('div');
        list.className = 'failed-list';
        data.failed_files.forEach((f) => {
            const row = document.createElement('div');
            row.textContent = `${f.filename} — ${f.reason}`;
            list.appendChild(row);
        });
        summary.appendChild(list);
    }
    show(summary, true);

    const btn = $('uploadBtn');
    btn.textContent = 'Start Processing Photos';
    btn.disabled = true;
    show($('toShareBtn'), true);
}

// ─── Share step ───
function renderShare() {
    const link = guestLink(current.code);
    $('codeDisplay').textContent = current.code;
    $('guestLinkValue').textContent = link;
    $('whatsappShare').href = whatsappLink(
        `Photos from ${current.eventName} are ready! Open this link and take a selfie to find yours: ${link}`);

    const qr = qrcode(0, 'M');
    qr.addData(link);
    qr.make();
    const img = document.createElement('img');
    img.src = qr.createDataURL(8, 0);
    img.alt = 'QR code for the guest link';
    $('qrBox').replaceChildren(img);

    const isHost = current.role === 'host';
    show($('statsCard'), isHost);
    show($('deleteEventBtn'), isHost);
    if (isHost) loadStats();
}

async function loadStats() {
    try {
        const data = await apiFetch(`/api/photographer/stats?code=${encodeURIComponent(current.code)}`,
            { headers: authHeaders() });
        $('statPhotos').textContent = data.total_photos || 0;
        $('statFaces').textContent = data.faces_detected || 0;
        $('statCommon').textContent = data.common_photos || 0;
        $('statGuests').textContent = data.total_users || 0;
        $('statDownloads').textContent = data.total_downloads || 0;
    } catch (e) {
        console.error('Could not load stats', e);
    }
}

async function deleteEvent() {
    const errEl = $('deleteError');
    show(errEl, false);
    const typed = window.prompt(
        `This permanently deletes every photo of “${current.eventName}” for all guests.\n` +
        `Type the event code ${current.code} to confirm.`);
    if (typed === null) return;
    if (typed.trim().toUpperCase() !== current.code) return showError(errEl, 'The code did not match. Nothing was deleted.');

    try {
        await apiFetch(`/api/photographer/event?code=${encodeURIComponent(current.code)}`,
            { method: 'DELETE', headers: authHeaders(), retry: false });
        store.remove(SAVED_EVENT);
        current = null;
        window.alert('The event and all of its photos were deleted.');
        location.href = '/photographer';
    } catch (e) {
        showError(errEl, 'Could not delete the event: ' + e.message);
    }
}

// ─── Start-up ───
function init() {
    $('tabRegister').addEventListener('click', () => switchMode('register'));
    $('tabJoin').addEventListener('click', () => switchMode('join'));
    $('regBtn').addEventListener('click', registerEvent);
    $('joinBtn').addEventListener('click', () =>
        joinEvent($('joinCode').value.trim().toUpperCase(), $('joinKey').value.trim(), $('joinError')));

    const dropZone = $('dropZone');
    dropZone.addEventListener('click', () => $('fileInput').click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFileSelect(e.dataTransfer.files);
    });
    $('fileInput').addEventListener('click', (e) => e.stopPropagation());
    $('fileInput').addEventListener('change', (e) => handleFileSelect(e.target.files));
    $('uploadBtn').addEventListener('click', uploadPhotos);
    $('toShareBtn').addEventListener('click', () => goToStep(3));
    $('uploadMoreBtn').addEventListener('click', () => { show($('toShareBtn'), false); goToStep(2); });

    $('copyHostKey').addEventListener('click', (e) => copyText($('hostKeyValue').textContent, e.currentTarget));
    $('copyContributorLink').addEventListener('click', (e) => copyText($('contributorLinkValue').textContent, e.currentTarget));
    $('copyGuestLink').addEventListener('click', (e) => copyText(guestLink(current.code), e.currentTarget));
    $('deleteEventBtn').addEventListener('click', deleteEvent);

    // A helper opened an upload link: /photographer?code=EVT-…#key=ck_…
    const linkCode = new URLSearchParams(location.search).get('code');
    const linkKey = new URLSearchParams(location.hash.slice(1)).get('key');
    if (linkCode && linkKey) {
        history.replaceState(null, '', location.pathname);   // keep the key out of the address bar
        switchMode('join');
        $('joinCode').value = linkCode.toUpperCase();
        $('joinKey').value = linkKey;
        joinEvent(linkCode.toUpperCase(), linkKey, $('joinError'));
        return;
    }

    // Offer to continue the event this device was last used for.
    const saved = store.get(SAVED_EVENT);
    if (saved && saved.code && saved.key) {
        $('resumeName').textContent = `${saved.eventName} (${saved.code})`;
        show($('resumeBox'), true);
        $('resumeBtn').addEventListener('click', () => joinEvent(saved.code, saved.key, $('resumeError')));
        $('forgetBtn').addEventListener('click', () => { store.remove(SAVED_EVENT); show($('resumeBox'), false); });
    }
}

document.addEventListener('DOMContentLoaded', init);
