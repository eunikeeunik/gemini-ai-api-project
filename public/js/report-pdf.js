/**
 * report-pdf.js — Engine Ekspor & Cetak PDF Profesional untuk Chatbot Interview
 * Menghasilkan tampilan cetak A4 portrait yang bersih, elegan, dan berstandar dokumen eksekutif.
 * Sepenuhnya mengisolasi style cetak dari dark-mode agar tidak terjadi teks putih di kertas putih.
 */

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function getTierBadgeClass(score) {
  if (score >= 75) return 'badge-strong';
  if (score >= 50) return 'badge-medium';
  return 'badge-weak';
}

function getTierLabel(score) {
  if (score >= 75) return 'Kuat';
  if (score >= 50) return 'Cukup';
  return 'Perlu Banyak Latihan';
}

/**
 * Mencetak atau mengunduh laporan evaluasi dalam format PDF A4 Portrait
 * @param {Object} report - Objek laporan evaluasi hasil penilaian AI
 * @param {Object} meta - Metadata sesi: { position, company, level, language }
 */
export function printReport(report, meta = {}) {
  if (!report) {
    console.error('[report-pdf] Laporan evaluasi kosong.');
    return;
  }

  const position = meta.position || 'Posisi Tidak Ditentukan';
  const company = meta.company || meta.companyName || 'Perusahaan Terkait';
  const level = meta.level || 'Mid';
  const language = meta.language || 'Bahasa Indonesia';
  const dateStr = new Date().toLocaleDateString('id-ID', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  });
  const timeStr = new Date().toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit'
  });

  const overallScore = report.overall_score !== undefined ? report.overall_score : 0;
  const fitScore = report.fit_score !== undefined ? report.fit_score : 0;
  const overallLabel = report.overall_tier?.label || getTierLabel(overallScore);
  const overallBadgeClass = getTierBadgeClass(overallScore);
  const fitBadgeClass = getTierBadgeClass(fitScore);

  const safePosName = position.replace(/[^a-zA-Z0-9_-]/g, '_');
  const safeCompName = (meta.company || meta.companyName || 'Umum').replace(/[^a-zA-Z0-9_-]/g, '_');
  const filename = `Chatbot_Interview_Laporan_${safePosName}_${safeCompName}`;

  // Generate HTML Laporan Eksekutif Standalone
  const html = `<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>${escapeHtml(filename)}</title>
  <style>
    @page {
      size: A4 portrait;
      margin: 12mm 14mm;
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      background-color: #ffffff !important;
      color: #1e293b !important;
      font-size: 11pt;
      line-height: 1.5;
      padding: 0;
    }

    .report-sheet {
      width: 100%;
      max-width: 100%;
      margin: 0 auto;
    }

    /* Header & Brand */
    .header-bar {
      border-bottom: 2px solid #2563eb;
      padding-bottom: 12px;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .brand-logo {
      background: #2563eb;
      color: #ffffff;
      font-weight: 800;
      font-size: 13pt;
      width: 38px;
      height: 38px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      letter-spacing: -0.5px;
    }

    .brand-title {
      font-size: 18pt;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.2;
    }

    .brand-subtitle {
      font-size: 9pt;
      color: #64748b;
      margin-top: 2px;
    }

    .header-meta {
      text-align: right;
      font-size: 8.5pt;
      color: #64748b;
      line-height: 1.4;
    }

    /* Meta Info Grid */
    .meta-box {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 14px;
      margin-bottom: 18px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
    }

    .meta-item {
      font-size: 8.5pt;
    }

    .meta-label {
      color: #64748b;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-size: 7pt;
      margin-bottom: 2px;
    }

    .meta-val {
      font-size: 9.5pt;
      font-weight: 600;
      color: #0f172a;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Score Cards Banner */
    .score-banner {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 18px;
    }

    .score-card {
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 14px 16px;
      background: #ffffff;
      page-break-inside: avoid;
    }

    .score-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .score-card-title {
      font-size: 9pt;
      font-weight: 600;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .score-value-row {
      display: flex;
      align-items: baseline;
      gap: 6px;
      margin-bottom: 6px;
    }

    .score-number {
      font-size: 26pt;
      font-weight: 800;
      line-height: 1;
      color: #0f172a;
    }

    .score-max {
      font-size: 11pt;
      font-weight: 500;
      color: #94a3b8;
    }

    /* Badges */
    .badge {
      display: inline-block;
      font-size: 8pt;
      font-weight: 700;
      padding: 3px 10px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.4px;
    }

    .badge-strong {
      background: #ecfdf5 !important;
      color: #047857 !important;
      border: 1px solid #a7f3d0;
    }

    .badge-medium {
      background: #fffbeb !important;
      color: #b45309 !important;
      border: 1px solid #fde68a;
    }

    .badge-weak {
      background: #fef2f2 !important;
      color: #b91c1c !important;
      border: 1px solid #fecaca;
    }

    .progress-track {
      height: 8px;
      background: #e2e8f0;
      border-radius: 999px;
      overflow: hidden;
      margin: 8px 0 6px 0;
    }

    .progress-bar {
      height: 100%;
      border-radius: 999px;
    }

    .progress-bar.badge-strong { background: #10b981 !important; }
    .progress-bar.badge-medium { background: #f59e0b !important; }
    .progress-bar.badge-weak { background: #ef4444 !important; }

    .score-subnote {
      font-size: 8.5pt;
      color: #64748b;
      margin-top: 4px;
      line-height: 1.35;
    }

    /* Verdict Box */
    .verdict-box {
      background: #eff6ff;
      border-left: 4px solid #2563eb;
      border-radius: 0 8px 8px 0;
      padding: 12px 16px;
      margin-bottom: 18px;
      page-break-inside: avoid;
    }

    .verdict-title {
      font-size: 9pt;
      font-weight: 700;
      color: #1e40af;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }

    .verdict-text {
      font-size: 11pt;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 6px;
    }

    .summary-text {
      font-size: 9pt;
      color: #334155;
      line-height: 1.45;
    }

    .session-note-box {
      margin-top: 8px;
      padding: 6px 10px;
      background: #fef3c7;
      border: 1px solid #fcd34d;
      border-radius: 6px;
      font-size: 8pt;
      color: #92400e;
    }

    /* Section Headings */
    .section-title {
      font-size: 11pt;
      font-weight: 700;
      color: #0f172a;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1.5px solid #e2e8f0;
      padding-bottom: 5px;
      margin: 18px 0 10px 0;
      display: flex;
      align-items: center;
      gap: 6px;
      page-break-after: avoid;
    }

    /* Dimension Matrix */
    .dimensions-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 16px;
      page-break-inside: avoid;
    }

    .dim-card {
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 8px 10px;
      background: #ffffff;
      font-size: 8.5pt;
    }

    .dim-header {
      display: flex;
      justify-content: space-between;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 4px;
    }

    .dim-bar-track {
      height: 6px;
      background: #f1f5f9;
      border-radius: 999px;
      overflow: hidden;
      margin-bottom: 4px;
    }

    .dim-bar-fill {
      height: 100%;
      border-radius: 999px;
    }

    .dim-note {
      font-size: 7.5pt;
      color: #64748b;
      line-height: 1.25;
    }

    /* Keyword Gaps */
    .chips-container {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 16px;
    }

    .chip-item {
      display: inline-block;
      background: #fef2f2;
      color: #991b1b;
      border: 1px solid #fecaca;
      border-radius: 6px;
      padding: 3px 8px;
      font-size: 8pt;
      font-weight: 600;
    }

    /* STAR Framework */
    .star-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
      margin-bottom: 16px;
      page-break-inside: avoid;
    }

    .star-box {
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 8px 10px;
      background: #f8fafc;
    }

    .star-box-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }

    .star-box-title {
      font-weight: 700;
      font-size: 8pt;
      color: #2563eb;
      text-transform: uppercase;
    }

    .star-box-score {
      font-weight: 800;
      font-size: 9pt;
      color: #0f172a;
    }

    .star-box-notes {
      font-size: 7.5pt;
      color: #475569;
      line-height: 1.3;
    }

    /* Strengths & Skills Grid */
    .two-col-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      margin-bottom: 16px;
      page-break-inside: avoid;
    }

    .bullet-list {
      list-style: none;
      font-size: 8.5pt;
      line-height: 1.4;
    }

    .bullet-list li {
      position: relative;
      padding-left: 16px;
      margin-bottom: 6px;
      color: #334155;
    }

    .bullet-list li::before {
      content: '✓';
      position: absolute;
      left: 0;
      color: #10b981;
      font-weight: 800;
    }

    .skill-card {
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 6px 10px;
      margin-bottom: 6px;
      background: #ffffff;
      font-size: 8.5pt;
    }

    .skill-card-top {
      display: flex;
      justify-content: space-between;
      font-weight: 600;
      color: #0f172a;
      margin-bottom: 2px;
    }

    .skill-prio {
      font-size: 7pt;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .prio-tinggi { background: #fee2e2; color: #991b1b; }
    .prio-sedang { background: #fef3c7; color: #92400e; }
    .prio-rendah { background: #f1f5f9; color: #475569; }

    .skill-reason {
      font-size: 7.5pt;
      color: #64748b;
      line-height: 1.25;
    }

    /* Grammar Corrections */
    .grammar-item {
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 8px 10px;
      margin-bottom: 8px;
      background: #ffffff;
      font-size: 8.5pt;
      page-break-inside: avoid;
    }

    .grammar-row {
      margin-bottom: 4px;
      line-height: 1.35;
    }

    .grammar-label {
      font-weight: 700;
      font-size: 7.5pt;
      text-transform: uppercase;
      display: inline-block;
      width: 80px;
    }

    .label-orig { color: #dc2626; }
    .label-corr { color: #16a34a; }
    .label-rom { color: #8b5cf6; }

    .grammar-exp {
      font-size: 7.5pt;
      color: #64748b;
      margin-top: 4px;
      border-top: 1px dashed #e2e8f0;
      padding-top: 4px;
    }

    /* Footer */
    .report-footer {
      border-top: 1px solid #e2e8f0;
      padding-top: 10px;
      margin-top: 20px;
      display: flex;
      justify-content: space-between;
      font-size: 7.5pt;
      color: #94a3b8;
    }
  </style>
</head>
<body>
  <div class="report-sheet">
    <!-- Header -->
    <header class="header-bar">
      <div class="brand-group">
        <div class="brand-logo">CI</div>
        <div>
          <div class="brand-title">Chatbot Interview</div>
          <div class="brand-subtitle">Laporan Evaluasi & Penilaian Wawancara Profesional</div>
        </div>
      </div>
      <div class="header-meta">
        <div>Tanggal: <strong>${escapeHtml(dateStr)}</strong> (${escapeHtml(timeStr)})</div>
        <div>Status: Terverifikasi Sistem AI</div>
      </div>
    </header>

    <!-- Meta Grid -->
    <div class="meta-box">
      <div class="meta-item">
        <div class="meta-label">Posisi Tujuan</div>
        <div class="meta-val">${escapeHtml(position)}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Target Perusahaan</div>
        <div class="meta-val">${escapeHtml(company)}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Tingkat Karir</div>
        <div class="meta-val">${escapeHtml(level)}</div>
      </div>
      <div class="meta-item">
        <div class="meta-label">Bahasa Sesi</div>
        <div class="meta-val">${escapeHtml(language)}</div>
      </div>
    </div>

    <!-- Score Banner -->
    <div class="score-banner">
      <div class="score-card">
        <div class="score-card-header">
          <span class="score-card-title">Skor Performa Keseluruhan</span>
          <span class="badge ${overallBadgeClass}">${escapeHtml(overallLabel)}</span>
        </div>
        <div class="score-value-row">
          <span class="score-number">${overallScore}</span>
          <span class="score-max">/ 100</span>
        </div>
        <div class="progress-track">
          <div class="progress-bar ${overallBadgeClass}" style="width: ${Math.min(100, Math.max(0, overallScore))}%;"></div>
        </div>
        <div class="score-subnote">Berdasarkan ketuntasan STAR, relevansi jawaban, dan konsistensi kompetensi peran.</div>
      </div>

      <div class="score-card">
        <div class="score-card-header">
          <span class="score-card-title">Skor Kesesuaian Posisi (Fit Score)</span>
          <span class="badge ${fitBadgeClass}">${fitScore}% Cocok</span>
        </div>
        <div class="score-value-row">
          <span class="score-number">${fitScore}%</span>
          <span class="score-max">Kesesuaian</span>
        </div>
        <div class="progress-track">
          <div class="progress-bar ${fitBadgeClass}" style="width: ${Math.min(100, Math.max(0, fitScore))}%;"></div>
        </div>
        <div class="score-subnote">${escapeHtml(report.fit_note || 'Tingkat keselarasan antara profil kandidat dengan ekspektasi rekrutmen.')}</div>
      </div>
    </div>

    <!-- Verdict & Summary -->
    <div class="verdict-box">
      <div class="verdict-title">Keputusan & Kesimpulan Evaluator</div>
      <div class="verdict-text">${escapeHtml(report.verdict || 'Evaluasi Sesi Wawancara Selesai')}</div>
      <div class="summary-text">${escapeHtml(report.summary || '')}</div>
      ${report.session_note ? `<div class="session-note-box">⚠️ ${escapeHtml(report.session_note)}</div>` : ''}
    </div>

    <!-- 8 Dimensi Kompetensi -->
    ${Array.isArray(report.dimensions) && report.dimensions.length > 0 ? `
    <h3 class="section-title">Matriks Profil Kompetensi & Karakter (D1 – D8)</h3>
    <div class="dimensions-grid">
      ${report.dimensions.map(d => {
        const dScore = d.score || 0;
        const dClass = getTierBadgeClass(dScore);
        return `
        <div class="dim-card">
          <div class="dim-header">
            <span>${escapeHtml(d.id ? d.id + ': ' : '')}${escapeHtml(d.name || 'Dimensi')}</span>
            <span>${dScore}%</span>
          </div>
          <div class="dim-bar-track">
            <div class="dim-bar-fill ${dClass}" style="width: ${dScore}%;"></div>
          </div>
          <div class="dim-note">${escapeHtml(d.note || '')}</div>
        </div>
        `;
      }).join('')}
    </div>
    ` : ''}

    <!-- Keyword Gaps -->
    ${Array.isArray(report.keyword_gaps) && report.keyword_gaps.length > 0 ? `
    <h3 class="section-title">Kesenjangan Kata Kunci Lowongan (Keyword Gaps)</h3>
    <div class="chips-container">
      ${report.keyword_gaps.map(kw => `<span class="chip-item">${escapeHtml(kw)}</span>`).join('')}
    </div>
    ` : ''}

    <!-- STAR Breakdown -->
    ${report.star ? `
    <h3 class="section-title">Analisis Kerangka STAR</h3>
    <div class="star-grid">
      <div class="star-box">
        <div class="star-box-header">
          <span class="star-box-title">Situation</span>
          <span class="star-box-score">${report.star.situation?.score ?? '-'}%</span>
        </div>
        <div class="star-box-notes">${escapeHtml(report.star.situation?.notes || 'Konteks dan latar belakang masalah.')}</div>
      </div>
      <div class="star-box">
        <div class="star-box-header">
          <span class="star-box-title">Task</span>
          <span class="star-box-score">${report.star.task?.score ?? '-'}%</span>
        </div>
        <div class="star-box-notes">${escapeHtml(report.star.task?.notes || 'Tanggung jawab dan target yang dihadapi.')}</div>
      </div>
      <div class="star-box">
        <div class="star-box-header">
          <span class="star-box-title">Action</span>
          <span class="star-box-score">${report.star.action?.score ?? '-'}%</span>
        </div>
        <div class="star-box-notes">${escapeHtml(report.star.action?.notes || 'Tindakan spesifik dan inisiatif nyata.')}</div>
      </div>
      <div class="star-box">
        <div class="star-box-header">
          <span class="star-box-title">Result</span>
          <span class="star-box-score">${report.star.result?.score ?? '-'}%</span>
        </div>
        <div class="star-box-notes">${escapeHtml(report.star.result?.notes || 'Dampak, hasil akhir, dan metrik terukur.')}</div>
      </div>
    </div>
    ` : ''}

    <!-- Strengths & Recommended Skills -->
    <div class="two-col-grid">
      <div>
        <h3 class="section-title">Kekuatan Utama</h3>
        <ul class="bullet-list">
          ${Array.isArray(report.strengths) && report.strengths.length > 0
            ? report.strengths.map(s => `<li>${escapeHtml(s)}</li>`).join('')
            : '<li>Menunjukkan motivasi dan respon yang konsisten selama sesi berlangsung.</li>'}
        </ul>
      </div>

      <div>
        <h3 class="section-title">Rekomendasi Pelatihan Skill</h3>
        ${Array.isArray(report.skills) && report.skills.length > 0 ? report.skills.map(sk => {
          if (typeof sk === 'string') {
            return `
            <div class="skill-card">
              <div class="skill-card-top"><span>${escapeHtml(sk)}</span></div>
            </div>`;
          }
          const p = (sk.priority || 'sedang').toLowerCase();
          const pClass = p === 'tinggi' ? 'prio-tinggi' : (p === 'rendah' ? 'prio-rendah' : 'prio-sedang');
          return `
          <div class="skill-card">
            <div class="skill-card-top">
              <span>${escapeHtml(sk.skill || '')}</span>
              <span class="skill-prio ${pClass}">${escapeHtml(sk.priority || 'Sedang')}</span>
            </div>
            <div class="skill-reason">${escapeHtml(sk.reason || '')}</div>
          </div>`;
        }).join('') : '<div style="font-size:8.5pt; color:#64748b;">Tidak ada rekomendasi pelatihan spesifik.</div>'}
      </div>
    </div>

    <!-- Grammar & Language Corrections -->
    ${Array.isArray(report.grammar) && report.grammar.length > 0 ? `
    <h3 class="section-title">Koreksi Struktur Kalimat & Diksi Profesional</h3>
    <div>
      ${report.grammar.map(g => `
      <div class="grammar-item">
        <div class="grammar-row"><span class="grammar-label label-orig">Asli:</span> "${escapeHtml(g.original || '')}"</div>
        ${g.romanization ? `<div class="grammar-row"><span class="grammar-label label-rom">Pelafalan:</span> <em>${escapeHtml(g.romanization)}</em></div>` : ''}
        <div class="grammar-row"><span class="grammar-label label-corr">Saran:</span> <strong>"${escapeHtml(g.correction || '')}"</strong></div>
        ${g.explanation ? `<div class="grammar-exp">${escapeHtml(g.explanation)}</div>` : ''}
      </div>
      `).join('')}
    </div>
    ` : ''}

    <!-- Footer -->
    <footer class="report-footer">
      <div>Chatbot Interview · Platform Latihan & Simulasi Wawancara Kerja Berbasis AI</div>
      <div>Dokumen Resmi Penilaian · Halaman 1</div>
    </footer>
  </div>
</body>
</html>`;

  // Gunakan isolated iframe agar print dialog tidak terpengaruh tema aktif (termasuk Dark Mode)
  const printIframe = document.createElement('iframe');
  printIframe.setAttribute('title', 'Cetak Laporan Chatbot Interview');
  printIframe.style.position = 'fixed';
  printIframe.style.right = '0';
  printIframe.style.bottom = '0';
  printIframe.style.width = '0';
  printIframe.style.height = '0';
  printIframe.style.border = 'none';
  printIframe.style.visibility = 'hidden';

  document.body.appendChild(printIframe);

  const prevTitle = document.title;
  // Ubah document.title browser agar nama default unduh PDF otomatis sesuai
  document.title = filename;

  const iframeDoc = printIframe.contentDocument || printIframe.contentWindow.document;
  iframeDoc.open();
  iframeDoc.write(html);
  iframeDoc.close();

  // Berikan waktu render font dan layout
  setTimeout(() => {
    try {
      printIframe.contentWindow.focus();
      printIframe.contentWindow.print();
    } catch (err) {
      console.error('[report-pdf] Gagal memicu print:', err);
    } finally {
      setTimeout(() => {
        document.title = prevTitle;
        if (printIframe.parentNode) {
          printIframe.parentNode.removeChild(printIframe);
        }
      }, 2000);
    }
  }, 350);
}

// Pasang ke window agar dapat dipanggil langsung dari mana pun
if (typeof window !== 'undefined') {
  window.printReport = printReport;
}
