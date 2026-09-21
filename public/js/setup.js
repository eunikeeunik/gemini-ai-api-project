/**
 * Setup Screen Handler & 14-Language Searchable Dropdown
 */

export const LANGUAGES = [
  // 3 Teratas selalu paling atas
  { code: 'id-ID', name: 'Bahasa Indonesia', native: 'Indonesia', top: true },
  { code: 'en-US', name: 'English', native: 'English (US)', top: true },
  { code: 'zh-CN', name: '中文 Mandarin (Sederhana)', native: 'Chinese (Simplified)', top: true },

  // 11 Bahasa lainnya
  { code: 'ja-JP', name: '日本語', native: 'Japanese' },
  { code: 'ko-KR', name: '한국어', native: 'Korean' },
  { code: 'es-ES', name: 'Español', native: 'Spanish' },
  { code: 'fr-FR', name: 'Français', native: 'French' },
  { code: 'de-DE', name: 'Deutsch', native: 'German' },
  { code: 'pt-BR', name: 'Português', native: 'Portuguese (Brazil)' },
  { code: 'ar-SA', name: 'العربية', native: 'Arabic' },
  { code: 'ms-MY', name: 'Bahasa Melayu', native: 'Malay' },
  { code: 'th-TH', name: 'ไทย', native: 'Thai' },
  { code: 'vi-VN', name: 'Tiếng Việt', native: 'Vietnamese' },
  { code: 'hi-IN', name: 'हिन्दी', native: 'Hindi' },
];

export function initSetupScreen({ onStartSession }) {
  const roleInput = document.getElementById('setup-role');
  const levelSelect = document.getElementById('setup-level');
  const companyInput = document.getElementById('setup-company');
  const startBtn = document.getElementById('start-interview-btn');

  let selectedLang = 'Bahasa Indonesia';
  let selectedLangCode = 'id-ID';
  let cvFile = null;
  let jdFile = null;

  // Searchable Language Dropdown
  setupLanguageDropdown({
    onSelect: (lang) => {
      selectedLang = lang.name;
      selectedLangCode = lang.code;
    }
  });

  // Validasi tombol mulai
  function checkValidity() {
    const hasRole = roleInput.value.trim().length > 0;
    startBtn.disabled = !hasRole;
  }

  roleInput.addEventListener('input', checkValidity);

  // File Dropzones
  setupDropzone({
    zoneId: 'cv-dropzone',
    inputId: 'cv-file-input',
    previewId: 'cv-preview',
    errorId: 'cv-error',
    onFileSelected: (file) => { cvFile = file; },
    onFileRemoved: () => { cvFile = null; },
  });

  setupDropzone({
    zoneId: 'jd-dropzone',
    inputId: 'jd-file-input',
    previewId: 'jd-preview',
    errorId: 'jd-error',
    onFileSelected: (file) => { jdFile = file; },
    onFileRemoved: () => { jdFile = null; },
  });

  // Handle Form Submit
  startBtn.addEventListener('click', async () => {
    const position = roleInput.value.trim();
    if (!position) return;

    startBtn.disabled = true;

    try {
      await onStartSession({
        position,
        level: levelSelect.value || 'Mid',
        companyName: companyInput ? companyInput.value.trim() : '',
        language: selectedLang,
        languageCode: selectedLangCode,
        cvFile,
        jdFile
      });
    } catch (err) {
      alert(err.message || 'Gagal memulai sesi.');
      startBtn.disabled = false;
      checkValidity();
    }
  });
}

function setupLanguageDropdown({ onSelect }) {
  const container = document.getElementById('language-dropdown-container');
  if (!container) return;

  const trigger = container.querySelector('.lang-dropdown-trigger');
  const menu = container.querySelector('.lang-dropdown-menu');
  const searchInput = container.querySelector('.lang-search-input');
  const list = container.querySelector('.lang-options-list');
  const selectedDisplay = container.querySelector('.selected-lang-name');

  let activeLang = LANGUAGES[0];

  function renderList(query = '') {
    const q = query.toLowerCase().trim();
    const filtered = LANGUAGES.filter(l =>
      l.name.toLowerCase().includes(q) ||
      l.native.toLowerCase().includes(q) ||
      l.code.toLowerCase().includes(q)
    );

    if (filtered.length === 0) {
      list.innerHTML = `<li class="lang-no-results">Tidak ada bahasa yang cocok</li>`;
      return;
    }

    list.innerHTML = filtered.map(l => `
      <li class="lang-option-item ${l.code === activeLang.code ? 'active' : ''}" data-code="${l.code}">
        <div class="lang-item-main">
          <span class="lang-item-name">${l.name}</span>
          <span class="lang-item-native">${l.native}</span>
        </div>
        ${l.top ? '<span class="lang-tag-top">Utama</span>' : ''}
      </li>
    `).join('');

    list.querySelectorAll('.lang-option-item').forEach(item => {
      item.addEventListener('click', () => {
        const code = item.dataset.code;
        const found = LANGUAGES.find(l => l.code === code);
        if (found) {
          activeLang = found;
          selectedDisplay.textContent = found.name;
          menu.classList.remove('open');
          trigger.setAttribute('aria-expanded', 'false');
          onSelect(found);
          renderList();
        }
      });
    });
  }

  renderList();

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = menu.classList.contains('open');
    if (isOpen) {
      menu.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
    } else {
      menu.classList.add('open');
      trigger.setAttribute('aria-expanded', 'true');
      searchInput.value = '';
      renderList();
      setTimeout(() => searchInput.focus(), 50);
    }
  });

  searchInput.addEventListener('input', (e) => {
    renderList(e.target.value);
  });

  // Tutup menu jika klik di luar
  document.addEventListener('click', (e) => {
    if (!container.contains(e.target)) {
      menu.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
    }
  });
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function setupDropzone({ zoneId, inputId, previewId, errorId, onFileSelected, onFileRemoved }) {
  const dropzone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const preview = document.getElementById(previewId);
  const errorEl = document.getElementById(errorId);

  dropzone.addEventListener('click', () => input.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('drag-over');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });

  input.addEventListener('change', () => {
    if (input.files.length > 0) {
      handleFile(input.files[0]);
    }
  });

  function handleFile(file) {
    errorEl.textContent = '';

    // Validasi tipe file dan ukuran
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      errorEl.textContent = 'File harus berupa PDF dengan ukuran maksimal 5 MB.';
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      errorEl.textContent = 'File harus berupa PDF dengan ukuran maksimal 5 MB.';
      return;
    }

    onFileSelected(file);

    // Tampilkan preview
    dropzone.style.display = 'none';
    preview.style.display = 'flex';
    preview.innerHTML = `
      <div class="file-info">
        <span class="file-name" title="${file.name}">${file.name}</span>
        <div class="file-meta">
          <span>${formatBytes(file.size)}</span>
          <span class="file-status-badge">✓ Terpilih</span>
        </div>
      </div>
      <button type="button" class="file-remove-btn" title="Hapus file" aria-label="Hapus file">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    `;

    const removeBtn = preview.querySelector('.file-remove-btn');
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      input.value = '';
      preview.style.display = 'none';
      dropzone.style.display = 'flex';
      errorEl.textContent = '';
      onFileRemoved();
    });
  }
}
