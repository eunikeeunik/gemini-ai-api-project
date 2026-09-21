import { renderMarkdown, escapeHtml, showConfirmModal } from './ui.js';

export function initChatScreen({ onSendMessage, onEndSession, onRetryLastMessage }) {
  const messagesContainer = document.getElementById('chat-messages');
  const textarea = document.getElementById('composer-input');
  const sendBtn = document.getElementById('composer-send-btn');
  const errorBanner = document.getElementById('error-banner');
  const errorText = document.getElementById('error-banner-text');
  const retryBtn = document.getElementById('error-retry-btn');
  const endSessionBtn = document.getElementById('end-session-btn');
  const mobileToggleBtn = document.getElementById('mobile-sidebar-toggle');
  const sidebar = document.getElementById('chat-sidebar');

  let currentAnswersCount = 0;
  let isWaiting = false;

  // Auto-scroll cerdas
  function scrollToBottom(force = false) {
    const threshold = 80;
    const isNearBottom =
      messagesContainer.scrollHeight - messagesContainer.scrollTop - messagesContainer.clientHeight <= threshold;

    if (force || isNearBottom) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  // Auto-grow textarea
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 144);
    textarea.style.height = `${newHeight}px`;
  });

  // Mobile sidebar toggle
  if (mobileToggleBtn) {
    mobileToggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('mobile-open');
    });
  }

  // Kirim dengan Enter, Shift+Enter untuk baris baru
  textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!sendBtn.disabled && textarea.value.trim().length > 0) {
        submitMessage();
      }
    }
  });

  sendBtn.addEventListener('click', () => {
    if (!sendBtn.disabled && textarea.value.trim().length > 0) {
      submitMessage();
    }
  });

  function submitMessage() {
    const text = textarea.value.trim();
    if (!text || isWaiting) return;

    textarea.value = '';
    textarea.style.height = 'auto';
    hideErrorBanner();

    onSendMessage(text);
  }

  // Tombol Coba Lagi pada Banner Error
  retryBtn.addEventListener('click', () => {
    hideErrorBanner();
    onRetryLastMessage();
  });

  // Tombol Akhiri & Nilai
  endSessionBtn.addEventListener('click', async () => {
    if (currentAnswersCount < 1) {
      await showConfirmModal({
        title: 'Belum ada jawaban',
        description: 'Penilaian butuh minimal 1 jawaban dari kandidat. Silakan jawab pertanyaan terlebih dahulu.',
        confirmText: 'Kembali menjawab',
        cancelText: '',
      });
      return;
    }

    const confirmed = await showConfirmModal({
      title: 'Akhiri sesi wawancara?',
      description: 'AI akan menyusun rapor komprehensif berdasarkan jawaban yang sudah Anda berikan sejauh ini.',
      confirmText: 'Akhiri & nilai',
      cancelText: 'Lanjutkan latihan',
      isDanger: false,
    });

    if (confirmed) {
      onEndSession();
    }
  });

  function showErrorBanner(message) {
    errorText.textContent = message;
    errorBanner.classList.add('active');
  }

  function hideErrorBanner() {
    errorBanner.classList.remove('active');
  }

  return {
    appendMessage(role, text) {
      const row = document.createElement('div');
      row.className = `message-row ${role}`;

      if (role === 'interviewer') {
        row.innerHTML = `
          <div class="message-avatar" aria-hidden="true">IC</div>
          <div class="message-bubble">${renderMarkdown(text)}</div>
        `;
      } else if (role === 'candidate') {
        row.innerHTML = `
          <div class="message-bubble"><p>${escapeHtml(text).replace(/\n/g, '<br>')}</p></div>
        `;
      }

      messagesContainer.appendChild(row);
      scrollToBottom(true);
    },

    appendSystemMessage(text) {
      const el = document.createElement('div');
      el.className = 'message-system';
      el.textContent = text;
      messagesContainer.appendChild(el);
      scrollToBottom(true);
    },

    showTyping() {
      if (document.getElementById('typing-row')) return;
      const row = document.createElement('div');
      row.id = 'typing-row';
      row.className = 'message-row interviewer';
      row.innerHTML = `
        <div class="message-avatar" aria-hidden="true">IC</div>
        <div class="typing-indicator" aria-label="Pewawancara sedang merespons...">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      `;
      messagesContainer.appendChild(row);
      scrollToBottom();
    },

    hideTyping() {
      const row = document.getElementById('typing-row');
      if (row) row.remove();
    },

    setBusy(busy) {
      isWaiting = busy;
      sendBtn.disabled = busy;
      textarea.disabled = busy;
      endSessionBtn.disabled = busy;
      if (!busy) {
        textarea.focus();
      }
    },

    setDoneState() {
      textarea.disabled = true;
      sendBtn.disabled = true;
      textarea.placeholder = 'Wawancara telah selesai. Sedang menyiapkan penilaian...';
    },

    showError(message) {
      showErrorBanner(message);
    },

    setAnswersCount(count) {
      currentAnswersCount = count;
    },

    updateCoverage(avgPercent = 0) {
      const clamped = Math.min(100, Math.max(0, Math.round(avgPercent)));
      const fillBar = document.getElementById('coverage-bar-fill');
      const textVal = document.getElementById('coverage-val-text');
      const mobileStatus = document.getElementById('mobile-header-status');

      if (fillBar) fillBar.style.width = `${clamped}%`;
      if (textVal) textVal.textContent = `${clamped}%`;
      if (mobileStatus) mobileStatus.textContent = `Cakupan ${clamped}%`;
    },

    setSessionMeta({ position, level, companyName, language, recruitmentProfile, documents }) {
      const roleTitle = document.getElementById('sidebar-role-title');
      const metaText = document.getElementById('sidebar-role-meta');
      const docsContainer = document.getElementById('sidebar-docs-list');
      const mobileRole = document.getElementById('mobile-header-role');

      const profileLabels = {
        ukm_startup: 'Startup / UKM',
        mnc: 'MNC / Korporasi',
        elite: 'Elite Tier Global'
      };
      const profName = profileLabels[recruitmentProfile] || 'MNC';

      if (roleTitle) roleTitle.textContent = position;
      if (metaText) {
        const companyStr = companyName ? `${companyName} · ` : '';
        metaText.textContent = `${companyStr}${level} · ${profName}`;
      }
      if (mobileRole) mobileRole.textContent = position;

      if (docsContainer) {
        docsContainer.innerHTML = '';
        if (documents && documents.length > 0) {
          documents.forEach(doc => {
            const pill = document.createElement('div');
            pill.className = 'doc-pill';
            pill.innerHTML = `
              <svg class="doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              <span class="doc-name" title="${escapeHtml(doc.name)}">${escapeHtml(doc.name)} (${doc.pages} hal)</span>
            `;
            docsContainer.appendChild(pill);
          });
        } else {
          const emptyPill = document.createElement('div');
          emptyPill.className = 'text-soft';
          emptyPill.style.fontSize = 'var(--t-xs)';
          emptyPill.textContent = 'Tanpa dokumen PDF';
          docsContainer.appendChild(emptyPill);
        }
      }
    },

    clearMessages() {
      messagesContainer.innerHTML = '';
      hideErrorBanner();
    }
  };
}
