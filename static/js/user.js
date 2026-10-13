// Guest page: enter the event, give a selfie, see and download your photos.

let currentCode = null;
let currentSessionId = null;
let selfieFile = null;
let commonOffset = 0;

// ─── Event code ───
async function verifyCode() {
    const code = $('codeInput').value.trim().toUpperCase();
    const errEl = $('codeError');
    show(errEl, false);
    if (!code) return showError(errEl, 'Please enter the event code.');

    const btn = $('verifyBtn');
    btn.disabled = true;
    btn.textContent = 'Verifying...';
    try {
        const data = await apiFetch('/api/user/verify-code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code }),
        }, (message) => showError(errEl, message));
        show(errEl, false);

        currentCode = code;
        $('eventName').textContent = data.event_name;
        $('eventPhotog').textContent = `By ${data.photographer_name} · ${data.total_photos} photos`;
        $('eventBanner').classList.add('show');
        $('selfieSection').classList.add('show');
        btn.textContent = '✓ Verified';
    } catch (e) {
        showError(errEl, e.message);
        btn.disabled = false;
        btn.textContent = 'Verify →';
    }
}

// ─── Selfie ───
function handleSelfieFile(file) {
    if (!file || !file.type.match(/^image\//)) return;
    selfieFile = file;
    const preview = $('selfiePreview');
    if (preview.src) URL.revokeObjectURL(preview.src);
    preview.src = URL.createObjectURL(file);
    $('selfieDropZone').classList.add('has-preview');
    updateSearchButton();
}

function updateSearchButton() {
    $('searchBtn').disabled = !(selfieFile && $('consentCheck').checked);
}

// ─── Search ───
function setSearching(searching) {
    $('selfieSection').classList.toggle('show', !searching);
    $('eventBanner').classList.toggle('show', !searching);
    $('loadingSection').classList.toggle('show', searching);
}

async function searchPhotos() {
    if (!selfieFile || !$('consentCheck').checked) return;
    const errEl = $('selfieError');
    show(errEl, false);
    setSearching(true);
    $('loadingSub').textContent = 'Comparing your face against all event photos. This may take 5–30 seconds.';

    const prepared = await compressImage(selfieFile, { maxSizeMB: 0.8, maxWidthOrHeight: 1600 });
    const formData = new FormData();
    formData.append('code', currentCode);
    formData.append('consent', 'yes');
    formData.append('photo', prepared, selfieFile.name || 'selfie.jpg');

    try {
        const data = await apiFetch('/api/user/upload-selfie', { method: 'POST', body: formData },
            (message) => { $('loadingSub').textContent = message; });
        currentSessionId = data.session_id;
        setSearching(false);
        $('selfieSection').classList.remove('show');
        $('eventBanner').classList.remove('show');
        showResults(data);
    } catch (e) {
        setSearching(false);
        showError(errEl, e.message);
    }
}

// ─── Results ───
function photoCard(photo, index) {
    const card = document.createElement('div');
    card.className = 'photo-card';

    if (photo.thumbnail_url) {
        const img = document.createElement('img');
        img.src = photo.thumbnail_url;
        img.className = 'photo-thumb';
        img.alt = `Photo ${index + 1}`;
        img.loading = 'lazy';
        img.addEventListener('click', () => openLightbox(photo.thumbnail_url));
        card.appendChild(img);
    } else {
        const missing = document.createElement('div');
        missing.className = 'photo-thumb-missing';
        missing.textContent = 'Preview not available';
        card.appendChild(missing);
    }

    const info = document.createElement('div');
    info.className = 'photo-info';
    if (typeof photo.similarity === 'number') {
        const score = document.createElement('div');
        score.className = 'match-score';
        score.textContent = `✦ ${Math.round(photo.similarity * 100)}% match`;
        info.appendChild(score);
    }
    const download = document.createElement('a');
    download.href = photo.download_url;
    download.className = 'dl-btn';
    download.textContent = '⬇ Download';
    info.appendChild(download);
    card.appendChild(info);
    return card;
}

function showResults(data) {
    show($('resultsSection'), true);
    $('matchCount').textContent = data.photos.length;

    const gallery = $('gallery');
    gallery.replaceChildren(...data.photos.map(photoCard));
    show(gallery, data.photos.length > 0);
    show($('noResults'), data.photos.length === 0);

    commonOffset = 0;
    $('commonGallery').replaceChildren();
    show($('commonSection'), data.common_count > 0);
    if (data.common_count > 0) {
        $('commonTitle').textContent = `Photos for everyone (${data.common_count})`;
        loadCommonPhotos();
    }
}

async function loadCommonPhotos() {
    const btn = $('commonMoreBtn');
    btn.disabled = true;
    try {
        const data = await apiFetch(
            `/api/user/common-photos?session_id=${encodeURIComponent(currentSessionId)}&offset=${commonOffset}`);
        data.photos.forEach((photo, i) => $('commonGallery').appendChild(photoCard(photo, commonOffset + i)));
        commonOffset = data.next_offset;
        show(btn, data.next_offset !== null);
    } catch (e) {
        console.error('Could not load common photos', e);
    } finally {
        btn.disabled = false;
    }
}

function resetSearch() {
    show($('resultsSection'), false);
    $('selfieSection').classList.add('show');
    $('eventBanner').classList.add('show');
    $('selfieDropZone').classList.remove('has-preview');
    $('selfiePreview').removeAttribute('src');
    $('selfieCameraInput').value = '';
    $('selfieFileInput').value = '';
    selfieFile = null;
    updateSearchButton();
}

async function deleteMyData() {
    if (!currentSessionId) return;
    if (!window.confirm('Delete your search and its history from this event? Your links will stop working.')) return;
    try {
        await apiFetch(`/api/user/session/${encodeURIComponent(currentSessionId)}`, { method: 'DELETE', retry: false });
    } catch (e) {
        if (e.status !== 404) return window.alert('Could not delete your data: ' + e.message);
    }
    currentSessionId = null;
    resetSearch();
    window.alert('Your data for this event has been deleted.');
}

// ─── Lightbox ───
function openLightbox(src) {
    $('lbImg').src = src;
    $('lightbox').classList.add('open');
}

function closeLightbox() {
    $('lightbox').classList.remove('open');
}

// ─── Start-up ───
function init() {
    $('verifyBtn').addEventListener('click', verifyCode);
    $('codeInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') verifyCode(); });

    const dropZone = $('selfieDropZone');
    dropZone.addEventListener('click', () => $('selfieCameraInput').click());
    dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.style.borderColor = 'var(--accent)'; });
    dropZone.addEventListener('dragleave', () => { dropZone.style.borderColor = ''; });
    dropZone.addEventListener('drop', (e) => { e.preventDefault(); handleSelfieFile(e.dataTransfer.files[0]); });
    $('takeSelfieBtn').addEventListener('click', () => $('selfieCameraInput').click());
    $('chooseSelfieBtn').addEventListener('click', () => $('selfieFileInput').click());
    $('selfieCameraInput').addEventListener('change', (e) => handleSelfieFile(e.target.files[0]));
    $('selfieFileInput').addEventListener('change', (e) => handleSelfieFile(e.target.files[0]));
    $('consentCheck').addEventListener('change', updateSearchButton);

    $('searchBtn').addEventListener('click', searchPhotos);
    $('resetBtn').addEventListener('click', resetSearch);
    $('commonMoreBtn').addEventListener('click', loadCommonPhotos);
    $('deleteDataBtn').addEventListener('click', deleteMyData);
    $('lightbox').addEventListener('click', closeLightbox);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeLightbox(); });

    // Opened from a QR code or shared link: /user?code=EVT-…
    const linkCode = new URLSearchParams(location.search).get('code');
    if (linkCode) {
        $('codeInput').value = linkCode.toUpperCase();
        verifyCode();
    }
}

document.addEventListener('DOMContentLoaded', init);
