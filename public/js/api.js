/**
 * API Client untuk Chatbot Interview
 */

async function handleResponse(response) {
  let data;
  try {
    data = await response.json();
  } catch (err) {
    const error = new Error('Gagal membaca respons dari server.');
    error.code = 'PARSE_ERROR';
    throw error;
  }

  if (!response.ok) {
    const err = new Error(data?.error?.message || 'Terjadi kesalahan pada server.');
    err.code = data?.error?.code || 'SERVER_ERROR';
    throw err;
  }

  return data;
}

/**
 * Mengunggah file PDF (CV atau JD) ke server
 */
export async function apiUploadFile(sessionId, kind, file) {
  const formData = new FormData();
  if (sessionId) formData.append('sessionId', sessionId);
  formData.append('kind', kind);
  formData.append('file', file);

  try {
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    return await handleResponse(response);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const networkErr = new Error('Gagal mengunggah dokumen. Periksa koneksi internet Anda.');
      networkErr.code = 'NETWORK_ERROR';
      throw networkErr;
    }
    throw err;
  }
}

/**
 * Memulai persiapan otomatis sesi wawancara (4 langkah)
 */
export async function apiPrepareSession({ sessionId, position, level, language, companyName }) {
  try {
    const response = await fetch('/api/prepare', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sessionId, position, level, language, companyName }),
    });
    return await handleResponse(response);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const networkErr = new Error('Gagal mempersiapkan sesi wawancara. Periksa koneksi internet Anda.');
      networkErr.code = 'NETWORK_ERROR';
      throw networkErr;
    }
    throw err;
  }
}

/**
 * Mengirim pesan jawaban kandidat ke interviewer AI
 */
export async function apiSendMessage(sessionId, message) {
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sessionId, message }),
    });
    return await handleResponse(response);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const networkErr = new Error('Pesan belum terkirim. Periksa koneksi Anda, lalu coba lagi.');
      networkErr.code = 'NETWORK_ERROR';
      throw networkErr;
    }
    throw err;
  }
}

/**
 * Mengakhiri sesi dan meminta evaluasi menyeluruh
 */
export async function apiEvaluateSession(sessionId) {
  try {
    const response = await fetch('/api/evaluate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ sessionId }),
    });
    return await handleResponse(response);
  } catch (err) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      const networkErr = new Error('Gagal memuat evaluasi. Periksa koneksi Anda, lalu coba lagi.');
      networkErr.code = 'NETWORK_ERROR';
      throw networkErr;
    }
    throw err;
  }
}
