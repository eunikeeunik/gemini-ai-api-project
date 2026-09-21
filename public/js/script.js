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
      updateMessageInUI(thinkingMessageId, data.result);
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
 * Replace the thinking bubble with the actual AI response
 */
function updateMessageInUI(messageId, text) {
  const rowDiv = document.getElementById(messageId);
  if (!rowDiv) return;
  
  const bubbleDiv = rowDiv.querySelector('.message-bubble');
  if (bubbleDiv) {
    bubbleDiv.innerHTML = formatMarkdown(text);
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
 * Update ticker bar secara live dari endpoint backend /api/stock/:symbol
 */
async function updateLiveTicker() {
  const symbols = ['BBCA', 'BBRI', 'BMRI', 'BBNI', 'ASII', 'TLKM', 'ADRO'];
  for (const sym of symbols) {
    try {
      const res = await fetch(`/api/stock/${sym}`);
      if (!res.ok) continue;
      const data = await res.json();
      
      const tickerItems = document.querySelectorAll('.ticker-item');
      tickerItems.forEach(item => {
        const symbolSpan = item.querySelector('.ticker-symbol');
        if (symbolSpan && symbolSpan.textContent.trim() === sym) {
          const priceSpan = item.querySelector('.ticker-price');
          const changeSpan = item.querySelector('.ticker-change');
          if (priceSpan) {
            priceSpan.textContent = `Rp ${Number(data.price).toLocaleString('id-ID')}`;
          }
          if (changeSpan && data.changePercent !== 'N/A') {
            changeSpan.textContent = data.changePercent;
            const isNegative = String(data.changePercent).startsWith('-');
            changeSpan.className = `ticker-change ${isNegative ? 'down' : 'up'}`;
          }
        }
      });
    } catch (e) {
      // Abaikan jika error jaringan
    }
  }
}

// Jalankan pembaruan ticker saat inisialisasi halaman
updateLiveTicker();
