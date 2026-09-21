import { apiUploadFile, apiPrepareSession, apiSendMessage, apiEvaluateSession } from './api.js';
import { initSetupScreen } from './setup.js';
import { initChatScreen } from './chat.js';
import { initReportScreen } from './report.js';
import { initTheme } from './theme.js';

const state = {
  screen: 'setup', // 'setup' | 'preparation' | 'chat' | 'evaluating' | 'report'
  sessionId: null,
  profile: null,
  documents: [],
  answersCount: 0,
  botTurnCount: 0,
  averageCoverage: 0,
  lastCandidateMessage: '',
  report: null,
  busy: false,
};

let chatScreen;
let reportScreen;

function switchScreen(newScreen) {
  state.screen = newScreen;
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));

  const target = document.getElementById(`${newScreen}-screen`);
  if (target) {
    target.classList.add('active');
  }
}

/**
 * Memulai sesi wawancara adaptif v3 (Upload -> 4-Step Prep -> Chat)
 */
async function startSession({ position, level, companyName, language, cvFile, jdFile }) {
  state.busy = true;

  // Tampilkan layar persiapan 4-langkah
  switchScreen('preparation');

  const prepStep1 = document.getElementById('prep-step-1');
  const prepStep2 = document.getElementById('prep-step-2');
  const prepStep3 = document.getElementById('prep-step-3');
  const prepStep4 = document.getElementById('prep-step-4');

  const resetPrepSteps = () => {
    [prepStep1, prepStep2, prepStep3, prepStep4].forEach(s => {
      if (!s) return;
      s.className = 'prep-step';
      const ind = s.querySelector('.step-indicator');
      if (ind) ind.textContent = '';
    });
  };

  resetPrepSteps();

  try {
    // Langkah 1: Upload CV jika ada & aktifkan step 1
    if (prepStep1) prepStep1.classList.add('active');
    state.documents = [];

    if (cvFile) {
      const uploadCvRes = await apiUploadFile(state.sessionId, 'cv', cvFile);
      state.sessionId = uploadCvRes.sessionId;
      state.documents.push(uploadCvRes.doc);
    }
    if (prepStep1) {
      prepStep1.className = 'prep-step done';
      prepStep1.querySelector('.step-indicator').textContent = '✓';
    }

    // Langkah 2: Upload JD jika ada & aktifkan step 2
    if (prepStep2) prepStep2.classList.add('active');
    if (jdFile) {
      const uploadJdRes = await apiUploadFile(state.sessionId, 'jd', jdFile);
      state.sessionId = uploadJdRes.sessionId;
      state.documents.push(uploadJdRes.doc);
    }
    if (prepStep2) {
      prepStep2.className = 'prep-step done';
      prepStep2.querySelector('.step-indicator').textContent = '✓';
    }

    // Langkah 3: Meriset perusahaan & Langkah 4: Rencana wawancara
    if (prepStep3) prepStep3.classList.add('active');

    // Timer simulasi visual saat request backend prepare berjalan
    const timerStep3 = setTimeout(() => {
      if (prepStep3) {
        prepStep3.className = 'prep-step done';
        prepStep3.querySelector('.step-indicator').textContent = '✓';
      }
      if (prepStep4) prepStep4.classList.add('active');
    }, 1800);

    const prepData = await apiPrepareSession({
      sessionId: state.sessionId,
      position,
      level,
      language,
      companyName,
    });

    clearTimeout(timerStep3);
    state.sessionId = prepData.sessionId;

    if (prepStep3) {
      prepStep3.className = 'prep-step done';
      prepStep3.querySelector('.step-indicator').textContent = '✓';
    }
    if (prepStep4) {
      prepStep4.className = 'prep-step done';
      prepStep4.querySelector('.step-indicator').textContent = '✓';
    }

    // Konfigurasi sidebar chat
    chatScreen.clearMessages();
    chatScreen.setSessionMeta({
      position,
      level,
      companyName: prepData.companyName || companyName,
      language,
      recruitmentProfile: prepData.recruitmentProfile,
      documents: state.documents,
    });

    state.profile = {
      position,
      level,
      company: prepData.companyName || companyName,
      companyName: prepData.companyName || companyName,
      language
    };

    chatScreen.setAnswersCount(0);
    chatScreen.updateCoverage(15);

    // Jeda sejenak untuk feedback visual yang halus
    setTimeout(() => {
      switchScreen('chat');
      if (prepData.firstMessage) {
        chatScreen.appendMessage('interviewer', prepData.firstMessage);
      }
    }, 500);

  } catch (err) {
    alert(err.message || 'Gagal mempersiapkan sesi wawancara.');
    switchScreen('setup');
    const startBtn = document.getElementById('start-interview-btn');
    if (startBtn) startBtn.disabled = false;
  } finally {
    state.busy = false;
  }
}

/**
 * Mengirim pesan jawaban kandidat
 */
async function sendMessage(text) {
  if (state.busy) return;
  state.busy = true;
  state.lastCandidateMessage = text;

  chatScreen.appendMessage('candidate', text);
  chatScreen.setBusy(true);
  chatScreen.showTyping();

  try {
    const res = await apiSendMessage(state.sessionId, text);
    chatScreen.hideTyping();

    // Tampilkan balasan pewawancara
    chatScreen.appendMessage('interviewer', res.message);
    state.answersCount = res.answersCount;
    state.botTurnCount = res.botTurnCount;
    chatScreen.setAnswersCount(res.answersCount);
    chatScreen.updateCoverage(res.averageCoverage || 0);

    if (res.done) {
      chatScreen.setDoneState();
      chatScreen.appendSystemMessage('Sesi wawancara selesai. Menyiapkan rapor evaluasi...');
      setTimeout(() => {
        runEvaluation();
      }, 1500);
    }
  } catch (err) {
    chatScreen.hideTyping();
    chatScreen.showError(err.message || 'Pesan belum terkirim. Periksa koneksi Anda, lalu coba lagi.');
  } finally {
    state.busy = false;
    chatScreen.setBusy(false);
  }
}

async function retryLastMessage() {
  if (!state.lastCandidateMessage || state.busy) return;
  state.busy = true;
  chatScreen.setBusy(true);
  chatScreen.showTyping();

  try {
    const res = await apiSendMessage(state.sessionId, state.lastCandidateMessage);
    chatScreen.hideTyping();

    chatScreen.appendMessage('interviewer', res.message);
    state.answersCount = res.answersCount;
    state.botTurnCount = res.botTurnCount;
    chatScreen.setAnswersCount(res.answersCount);
    chatScreen.updateCoverage(res.averageCoverage || 0);

    if (res.done) {
      chatScreen.setDoneState();
      chatScreen.appendSystemMessage('Sesi wawancara selesai. Menyiapkan rapor evaluasi...');
      setTimeout(() => {
        runEvaluation();
      }, 1500);
    }
  } catch (err) {
    chatScreen.hideTyping();
    chatScreen.showError(err.message || 'Pesan belum terkirim. Periksa koneksi Anda, lalu coba lagi.');
  } finally {
    state.busy = false;
    chatScreen.setBusy(false);
  }
}

/**
 * Menjalankan evaluasi komprehensif
 */
async function runEvaluation() {
  switchScreen('evaluating');

  const step1 = document.getElementById('eval-step-1');
  const step2 = document.getElementById('eval-step-2');
  const step3 = document.getElementById('eval-step-3');

  const resetEvalSteps = () => {
    [step1, step2, step3].forEach(s => {
      if (!s) return;
      s.className = 'loading-step';
      const ind = s.querySelector('.step-indicator');
      if (ind) ind.textContent = '';
    });
  };

  resetEvalSteps();
  if (step1) step1.classList.add('active');

  const timer1 = setTimeout(() => {
    if (step1) {
      step1.className = 'loading-step done';
      step1.querySelector('.step-indicator').textContent = '✓';
    }
    if (step2) step2.classList.add('active');
  }, 1200);

  const timer2 = setTimeout(() => {
    if (step2) {
      step2.className = 'loading-step done';
      step2.querySelector('.step-indicator').textContent = '✓';
    }
    if (step3) step3.classList.add('active');
  }, 2800);

  try {
    const reportData = await apiEvaluateSession(state.sessionId);
    state.report = reportData;

    clearTimeout(timer1);
    clearTimeout(timer2);

    if (step1) {
      step1.className = 'loading-step done';
      step1.querySelector('.step-indicator').textContent = '✓';
    }
    if (step2) {
      step2.className = 'loading-step done';
      step2.querySelector('.step-indicator').textContent = '✓';
    }
    if (step3) {
      step3.className = 'loading-step done';
      step3.querySelector('.step-indicator').textContent = '✓';
    }

    setTimeout(() => {
      reportScreen.renderReport(reportData, state.profile);
      switchScreen('report');
    }, 450);
  } catch (err) {
    alert(err.message || 'Gagal menyusun laporan evaluasi.');
    switchScreen('chat');
  }
}

function restartSession() {
  state.sessionId = null;
  state.answersCount = 0;
  state.botTurnCount = 0;
  state.averageCoverage = 0;
  state.report = null;
  state.lastCandidateMessage = '';
  state.busy = false;

  const roleInput = document.getElementById('setup-role');
  const companyInput = document.getElementById('setup-company');
  if (roleInput) roleInput.value = '';
  if (companyInput) companyInput.value = '';

  const cvInput = document.getElementById('cv-file-input');
  const jdInput = document.getElementById('jd-file-input');
  if (cvInput) cvInput.value = '';
  if (jdInput) jdInput.value = '';

  const cvPreview = document.getElementById('cv-preview');
  const jdPreview = document.getElementById('jd-preview');
  const cvDrop = document.getElementById('cv-dropzone');
  const jdDrop = document.getElementById('jd-dropzone');

  if (cvPreview) cvPreview.style.display = 'none';
  if (jdPreview) jdPreview.style.display = 'none';
  if (cvDrop) cvDrop.style.display = 'flex';
  if (jdDrop) jdDrop.style.display = 'flex';

  const startBtn = document.getElementById('start-interview-btn');
  if (startBtn) {
    startBtn.disabled = true;
    startBtn.textContent = 'Mulai wawancara';
  }

  switchScreen('setup');
}

// Inisialisasi Aplikasi saat DOM siap
window.addEventListener('DOMContentLoaded', () => {
  initTheme();

  initSetupScreen({
    onStartSession: startSession,
  });

  chatScreen = initChatScreen({
    onSendMessage: sendMessage,
    onEndSession: runEvaluation,
    onRetryLastMessage: retryLastMessage,
  });

  reportScreen = initReportScreen({
    onRestartSession: restartSession,
  });
});
