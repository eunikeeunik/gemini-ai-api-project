/**
 * UI Utilities and Modals
 */

export function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export function renderMarkdown(markdownText) {
  if (!markdownText) return '';

  if (window.marked && window.DOMPurify) {
    try {
      const rawHtml = window.marked.parse(markdownText, { breaks: true, gfm: true });
      return window.DOMPurify.sanitize(rawHtml);
    } catch (e) {
      console.warn('Marked parse failed, using fallback', e);
    }
  }

  // Fallback jika library belum termuat
  return `<p>${escapeHtml(markdownText).replace(/\n/g, '<br>')}</p>`;
}

export function showConfirmModal({ title, description, confirmText = 'Konfirmasi', cancelText = 'Batal', isDanger = false }) {
  return new Promise((resolve) => {
    const dialog = document.getElementById('confirm-dialog');
    if (!dialog) {
      resolve(window.confirm(`${title}\n\n${description}`));
      return;
    }

    const titleEl = dialog.querySelector('.dialog-title');
    const descEl = dialog.querySelector('.dialog-desc');
    const confirmBtn = dialog.querySelector('#dialog-confirm-btn');
    const cancelBtn = dialog.querySelector('#dialog-cancel-btn');

    titleEl.textContent = title;
    descEl.textContent = description;
    confirmBtn.textContent = confirmText;
    cancelBtn.textContent = cancelText;

    if (isDanger) {
      confirmBtn.className = 'btn btn-danger-outline';
    } else {
      confirmBtn.className = 'btn btn-primary';
    }

    const onConfirm = () => {
      cleanup();
      dialog.close();
      resolve(true);
    };

    const onCancel = () => {
      cleanup();
      dialog.close();
      resolve(false);
    };

    function cleanup() {
      confirmBtn.removeEventListener('click', onConfirm);
      cancelBtn.removeEventListener('click', onCancel);
    }

    confirmBtn.addEventListener('click', onConfirm);
    cancelBtn.addEventListener('click', onCancel);

    dialog.showModal();
  });
}
