import { escapeHtml, showConfirmModal } from './ui.js';
import { printReport } from './report-pdf.js';

export function initReportScreen({ onRestartSession }) {
  const downloadPdfBtn = document.getElementById('report-download-btn');
  const restartBtn = document.getElementById('report-restart-btn');

  let currentReport = null;
  let currentMeta = {};

  // Unduh laporan PDF profesional terisolasi via report-pdf.js (anti teks putih di dark mode)
  downloadPdfBtn.addEventListener('click', () => {
    if (!currentReport) return;
    printReport(currentReport, {
      position: currentMeta.position || currentMeta.role || '',
      company: currentMeta.company || currentMeta.companyName || '',
      level: currentMeta.level || '',
      language: currentMeta.language || ''
    });
  });

  restartBtn.addEventListener('click', async () => {
    const confirmed = await showConfirmModal({
      title: 'Mulai sesi baru?',
      description: 'Anda akan kembali ke form awal untuk memulai simulasi baru.',
      confirmText: 'Mulai baru',
      cancelText: 'Batal',
    });

    if (confirmed) {
      onRestartSession();
    }
  });

  return {
    renderReport(report, meta = {}) {
      currentReport = report;
      currentMeta = meta;

      renderHeroAndVerdict(report);
      renderFitScoreSection(report);
      renderDimensionsSection(report.dimensions || []);
      renderKeywordGaps(report.keyword_gaps || []);
      renderStarSection(report.star);
      renderStrengths(report.strengths || []);
      renderGrammar(report.grammar || []);
      renderSkills(report.skills || []);
    },
  };
}

function renderHeroAndVerdict(report) {
  const scoreEl = document.getElementById('report-overall-score');
  const levelBadge = document.getElementById('report-level-badge');
  const verdictEl = document.getElementById('report-verdict-text');
  const summaryEl = document.getElementById('report-summary-text');
  const sessionNoteEl = document.getElementById('report-session-note');

  const overall = report.overall_score || 0;
  const tier = report.overall_tier || { label: 'Cukup', badgeClass: 'badge-medium' };

  if (scoreEl) scoreEl.textContent = overall;
  if (levelBadge) {
    levelBadge.textContent = tier.label;
    levelBadge.className = `hero-level-badge ${tier.badgeClass}`;
  }
  if (verdictEl) {
    verdictEl.textContent = report.verdict || '';
  }
  if (summaryEl) {
    summaryEl.textContent = report.summary || '';
  }

  if (sessionNoteEl) {
    if (report.session_note) {
      sessionNoteEl.style.display = 'block';
      sessionNoteEl.innerHTML = `
        <div class="session-note-box">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>${escapeHtml(report.session_note)}</span>
        </div>
      `;
    } else {
      sessionNoteEl.style.display = 'none';
    }
  }
}

function renderFitScoreSection(report) {
  const fitScoreEl = document.getElementById('report-fit-score');
  const fitBadgeEl = document.getElementById('report-fit-badge');
  const fitFillEl = document.getElementById('report-fit-fill');
  const fitNoteEl = document.getElementById('report-fit-note');

  const fitScore = report.fit_score || 0;
  const fitTier = report.fit_tier || { label: 'Cukup', badgeClass: 'badge-medium' };

  if (fitScoreEl) fitScoreEl.textContent = `${fitScore}%`;
  if (fitBadgeEl) {
    fitBadgeEl.textContent = fitTier.label;
    fitBadgeEl.className = `fit-tier-badge ${fitTier.badgeClass}`;
  }
  if (fitFillEl) {
    fitFillEl.style.width = `${fitScore}%`;
    fitFillEl.className = `fit-bar-fill ${fitTier.badgeClass}`;
  }
  if (fitNoteEl) {
    fitNoteEl.textContent = report.fit_note || 'Tingkat kesesuaian berdasarkan profil lowongan dan jawaban wawancara.';
  }
}

function renderDimensionsSection(dimensions = []) {
  const container = document.getElementById('report-dimensions-list');
  if (!container) return;

  if (dimensions.length === 0) {
    container.innerHTML = '<p class="text-soft">Tidak ada data profil kompetensi.</p>';
    return;
  }

  container.innerHTML = dimensions.map(dim => {
    const score = dim.score || 0;
    let barColorClass = 'fill-strong';
    if (score < 50) barColorClass = 'fill-weak';
    else if (score < 75) barColorClass = 'fill-gap';

    return `
      <div class="dimension-card">
        <div class="dimension-header">
          <div class="dimension-title-group">
            <span class="dimension-id-badge">${escapeHtml(dim.id)}</span>
            <span class="dimension-name">${escapeHtml(dim.name)}</span>
          </div>
          <span class="dimension-score-val">${score}/100</span>
        </div>
        <div class="dimension-bar-track">
          <div class="dimension-bar-fill ${barColorClass}" style="width: ${score}%;"></div>
        </div>
        ${dim.evidence ? `
          <div class="dimension-evidence">
            <span class="evidence-tag">Bukti:</span> "${escapeHtml(dim.evidence)}"
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

function renderKeywordGaps(keywords = []) {
  const container = document.getElementById('report-keyword-gaps');
  if (!container) return;

  if (keywords.length === 0) {
    container.innerHTML = '<p class="text-soft" style="font-size:var(--t-sm);">Semua kata kunci utama lowongan telah tersampaikan dengan baik.</p>';
    return;
  }

  container.innerHTML = `
    <div class="keyword-chips-wrap">
      ${keywords.map(kw => `
        <span class="keyword-gap-chip">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          ${escapeHtml(kw)}
        </span>
      `).join('')}
    </div>
  `;
}

function renderStarSection(starData = {}) {
  const container = document.getElementById('star-columns-container');
  const detailsContainer = document.getElementById('star-details-container');
  if (!container || !detailsContainer) return;

  const elements = [
    { key: 'situation', letter: 'S', name: 'Situation', label: 'Situasi' },
    { key: 'task', letter: 'T', name: 'Task', label: 'Tugas' },
    { key: 'action', letter: 'A', name: 'Action', label: 'Tindakan' },
    { key: 'result', letter: 'R', name: 'Result', label: 'Hasil' },
  ];

  container.innerHTML = '';
  detailsContainer.innerHTML = '';

  elements.forEach((elem, index) => {
    const data = starData[elem.key] || { score: 0, feedback: '-' };
    const score = data.score || 0;

    let fillClass = 'fill-strong';
    if (score < 50) fillClass = 'fill-weak';
    else if (score < 75) fillClass = 'fill-gap';

    // Buat Kartu Kolom STAR
    const card = document.createElement('div');
    card.className = `star-card ${index === 0 ? 'active' : ''}`;
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.setAttribute('aria-label', `${elem.name}: Skor ${score}/100`);

    card.innerHTML = `
      <div class="star-letter">${elem.letter}</div>
      <div class="star-name">${elem.name}</div>
      <div class="star-score">${score}/100</div>
      <div class="star-bar-track">
        <div class="star-bar-fill ${fillClass}" style="width: ${score}%;"></div>
      </div>
    `;

    // Buat Panel Detail
    const panel = document.createElement('div');
    panel.id = `star-detail-${elem.key}`;
    panel.className = `star-detail-panel ${index === 0 ? 'active' : ''}`;

    panel.innerHTML = `
      <div>
        <div class="detail-item-title">Evaluasi Unsur ${elem.name} (${elem.label})</div>
        <div class="detail-item-text">${escapeHtml(data.feedback)}</div>
      </div>
    `;

    // Klik kartu untuk membuka detail
    const activateCard = () => {
      container.querySelectorAll('.star-card').forEach(c => c.classList.remove('active'));
      detailsContainer.querySelectorAll('.star-detail-panel').forEach(p => p.classList.remove('active'));
      card.classList.add('active');
      panel.classList.add('active');
    };

    card.addEventListener('click', activateCard);
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        activateCard();
      }
    });

    container.appendChild(card);
    detailsContainer.appendChild(panel);
  });
}

function renderStrengths(strengths = []) {
  const container = document.getElementById('report-strengths-list');
  if (!container) return;

  if (strengths.length === 0) {
    container.innerHTML = '<p class="text-soft">Tidak ada catatan kekuatan khusus.</p>';
    return;
  }

  container.innerHTML = strengths.map(st => `
    <div class="strength-item">
      <svg class="strength-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
        <polyline points="22 4 12 14.01 9 11.01"></polyline>
      </svg>
      <span>${escapeHtml(st)}</span>
    </div>
  `).join('');
}

function renderGrammar(corrections = []) {
  const container = document.getElementById('report-grammar-list');
  if (!container) return;

  if (!corrections || corrections.length === 0) {
    container.innerHTML = '<p class="text-soft">Bahasa dan struktur kalimat Anda sudah sangat baik. Tidak ada catatan perbaikan signifikan.</p>';
    return;
  }

  container.innerHTML = corrections.map(c => `
    <div class="grammar-item">
      <div class="grammar-diff">
        <div class="grammar-original">Kutipan Anda: "${escapeHtml(c.original)}"</div>
        <div class="grammar-corrected">Versi Lebih Efektif: <span>${escapeHtml(c.improved)}</span></div>
        ${c.romanization ? `
          <div class="grammar-romanization">
            <span class="roman-tag">Pelafalan:</span> ${escapeHtml(c.romanization)}
          </div>
        ` : ''}
      </div>
      <div class="grammar-expl">${escapeHtml(c.note)}</div>
    </div>
  `).join('');
}

function renderSkills(skills = []) {
  const container = document.getElementById('report-skills-list');
  if (!container) return;

  if (!skills || skills.length === 0) {
    container.innerHTML = '<p class="text-soft">Tidak ada rekomendasi pelatihan lanjutan khusus.</p>';
    return;
  }

  container.innerHTML = skills.map(sk => `
    <div class="skill-card">
      <div class="skill-card-header">
        <span class="skill-card-title">${escapeHtml(sk.area)}</span>
      </div>
      <div class="skill-reason">${escapeHtml(sk.why)}</div>
      <div class="skill-tip-box">
        <span class="tip-label">Langkah Latihan:</span> ${escapeHtml(sk.tip)}
      </div>
    </div>
  `).join('');
}
