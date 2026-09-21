// DOM Elements
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatBox = document.getElementById('chat-box');
const clearChatBtn = document.getElementById('clear-chat-btn');
const promptChips = document.querySelectorAll('.prompt-chip');
const welcomeMessage = document.getElementById('welcome-message');

// Conversation history required by /api/chat
let conversation = [];

// Initialize Markdown configuration if marked is loaded
if (typeof marked !== 'undefined') {
  marked.setOptions({
    breaks: true,
    gfm: true
  });
}

/**
 * Handle form submission
 */
chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const messageText = userInput.value.trim();
  if (!messageText) return;
  
  // Hide initial welcome card after first message to keep view clean
  if (welcomeMessage) {
    welcomeMessage.style.display = 'none';
  }
  
  // 1. Add user message to UI
  addMessageToUI('user', messageText);
  
  // Add to conversation history
  conversation.push({ role: 'user', text: messageText });
  
  // Clear input
  userInput.value = '';
  
  // Disable submit button temporarily
  const submitBtn = chatForm.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.disabled = true;
  
  // 2. Show temporary "Thinking..." bot message
  const thinkingMessageId = addThinkingToUI();
  
  try {
    // 3. Send POST request to /api/chat
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ conversation })
    });
    
    if (!response.ok) {
      throw new Error(`Server status error: ${response.status}`);
    }
    
    const data = await response.json();
    
    // 4. Update the message with the AI reply
    if (data && data.result) {
      updateMessageInUI(thinkingMessageId, data.result, data.validation);
      // Append model response to conversation history
      conversation.push({ role: 'model', text: data.result });
    } else {
      updateMessageInUI(thinkingMessageId, 'Sorry, no response received.');
    }
    
  } catch (error) {
    console.error('Error during chat request:', error);
    updateMessageInUI(thinkingMessageId, 'Failed to get response from server.');
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    userInput.focus();
  }
});

/**
 * Helper to add a user or model message to UI
 */
function addMessageToUI(role, text) {
  const rowDiv = document.createElement('div');
  rowDiv.classList.add('message-row', role);
  
  const avatarDiv = document.createElement('div');
  avatarDiv.classList.add('message-avatar');
  avatarDiv.innerHTML = role === 'user' 
    ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`
    : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>`;
  
  const bubbleDiv = document.createElement('div');
  bubbleDiv.classList.add('message-bubble');
  
  if (role === 'user') {
    bubbleDiv.textContent = text;
    rowDiv.appendChild(bubbleDiv);
    rowDiv.appendChild(avatarDiv);
  } else {
    bubbleDiv.innerHTML = formatMarkdown(text);
    rowDiv.appendChild(avatarDiv);
    rowDiv.appendChild(bubbleDiv);
  }
  
  const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 7)}`;
  rowDiv.id = messageId;
  
  chatBox.appendChild(rowDiv);
  scrollToBottom();
  
  return messageId;
}

/**
 * Helper to render animated "Thinking..." state
 */
function addThinkingToUI() {
  const rowDiv = document.createElement('div');
  rowDiv.classList.add('message-row', 'model');
  
  const avatarDiv = document.createElement('div');
  avatarDiv.classList.add('message-avatar');
  avatarDiv.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline><polyline points="17 6 23 6 23 12"></polyline></svg>`;
  
  const bubbleDiv = document.createElement('div');
  bubbleDiv.classList.add('message-bubble');
  
  bubbleDiv.innerHTML = `
    <div class="thinking-container">
      <div class="wave-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <span>Menganalisis data pasar & laporan keuangan...</span>
    </div>
  `;
  
  rowDiv.appendChild(avatarDiv);
  rowDiv.appendChild(bubbleDiv);
  
  const messageId = `msg-thinking-${Date.now()}`;
  rowDiv.id = messageId;
  
  chatBox.appendChild(rowDiv);
  scrollToBottom();
  
  return messageId;
}

/**
 * Replace the thinking bubble with the actual AI response and validation badge
 */
function updateMessageInUI(messageId, text, validation) {
  const rowDiv = document.getElementById(messageId);
  if (!rowDiv) return;
  
  const bubbleDiv = rowDiv.querySelector('.message-bubble');
  if (bubbleDiv) {
    let html = formatMarkdown(text);
    
    // Append Grounding Verification Badge if available
    if (validation) {
      const isValid = validation.is_valid !== false;
      const flags = validation.flags || [];
      const badgeClass = isValid ? 'badge-verified' : 'badge-warning';
      const badgeIcon = isValid ? '✓' : '⚠️';
      const badgeText = isValid 
        ? 'Data & Perhitungan Terverifikasi Engine (Grounding OK)' 
        : `Peringatan Verifikasi Engine: ${flags[0] || 'Angka tidak berpadanan'}`;
      
      html += `
        <div style="margin-top: 14px; padding: 6px 12px; font-size: 11px; font-family: var(--font-mono); border-radius: 6px; display: inline-flex; align-items: center; gap: 6px; ${isValid ? 'background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.25);' : 'background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25);'}">
          <span>${badgeIcon}</span>
          <span>${badgeText}</span>
        </div>
      `;
    }
    
    bubbleDiv.innerHTML = html;
  }
  scrollToBottom();
}

/**
 * Format markdown string safely using Marked + DOMPurify (with fallback)
 */
function formatMarkdown(content) {
  if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
    try {
      const rawHtml = marked.parse(content);
      return DOMPurify.sanitize(rawHtml);
    } catch (err) {
      console.warn('Markdown parse failed, using fallback:', err);
    }
  }
  
  // Safe basic formatting fallback if libraries unavailable
  const escapeHtml = (str) => str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return escapeHtml(content).replace(/\n/g, '<br>');
}

/**
 * Scroll chat box smoothly to bottom
 */
function scrollToBottom() {
  chatBox.scrollTop = chatBox.scrollHeight;
}

/**
 * Quick Suggestion Chips Click Event
 */
promptChips.forEach(chip => {
  chip.addEventListener('click', () => {
    const prompt = chip.getAttribute('data-prompt');
    if (prompt) {
      userInput.value = prompt;
      chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
    }
  });
});

/**
 * Clear Chat / Reset History Event
 */
if (clearChatBtn) {
  clearChatBtn.addEventListener('click', () => {
    if (confirm('Hapus seluruh riwayat percakapan analisis saham?')) {
      conversation = [];
      chatBox.innerHTML = '';
      if (welcomeMessage) {
        welcomeMessage.style.display = 'block';
        chatBox.appendChild(welcomeMessage);
      }
    }
  });
}

/**
 * Update ticker bar secara live dari batch endpoint /api/quotes
 */
async function updateLiveTicker() {
  const symbols = ['^JKSE', 'BBCA', 'BBRI', 'BMRI', 'BBNI', 'ASII', 'TLKM', '^GSPC', 'AAPL', 'NVDA'];
  try {
    const res = await fetch(`/api/quotes?symbols=${encodeURIComponent(symbols.join(','))}`);
    if (!res.ok) return;
    const quotes = await res.json();
    if (!Array.isArray(quotes) || quotes.length === 0) return;

    const tickerWrapper = document.querySelector('.ticker-wrapper');
    if (!tickerWrapper) return;

    // Map existing items or update in-place
    const quoteMap = {};
    quotes.forEach(q => {
      const symKey = (q.code || q.symbol || '').replace('IDX:', '').replace('US:', '').replace('.JK', '');
      quoteMap[symKey] = q;
      if (q.symbol) quoteMap[q.symbol] = q;
      if (q.yahoo_ticker) quoteMap[q.yahoo_ticker] = q;
    });

    const tickerItems = tickerWrapper.querySelectorAll('.ticker-item');
    tickerItems.forEach(item => {
      const symSpan = item.querySelector('.ticker-symbol');
      if (!symSpan) return;
      const rawText = symSpan.textContent.trim();
      const q = quoteMap[rawText] || (rawText === 'IHSG' ? quoteMap['^JKSE'] : null);
      if (q && q.price !== null && q.price !== undefined) {
        const priceSpan = item.querySelector('.ticker-price');
        const changeSpan = item.querySelector('.ticker-change');
        if (priceSpan) {
          const isIdr = (q.currency === 'IDR' || q.market === 'IDX');
          const formatted = isIdr 
            ? `Rp ${Number(q.price).toLocaleString('id-ID')}`
            : `$${Number(q.price).toFixed(2)}`;
          priceSpan.textContent = formatted;
        }
        if (changeSpan) {
          const chgPct = Number(q.change_pct || 0);
          const isPos = chgPct >= 0;
          changeSpan.textContent = `${isPos ? '+' : ''}${chgPct.toFixed(2)}%`;
          changeSpan.className = `ticker-change ${isPos ? 'up' : 'down'}`;
        }
      }
    });
  } catch (e) {
    console.warn('Ticker update skipped:', e);
  }
}

// Jalankan pembaruan ticker saat inisialisasi halaman & refresh setiap 30 detik
updateLiveTicker();
setInterval(updateLiveTicker, 30000);


