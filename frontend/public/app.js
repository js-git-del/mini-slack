const API_URL = 'http://localhost:5000/api';

// 전역 상태
let currentUser = null;
let currentChannel = null;
let channels = [];
let users = [];
let messages = [];

// ============================================
// 초기화
// ============================================
async function init() {
    
    // DOM 요소 (const 없이!)
    elements = {  // ← 여기! const 빼기
        // 모달
        loginModal: document.getElementById('loginModal'),
        createChannelModal: document.getElementById('createChannelModal'),
        
        // 로그인
        usernameInput: document.getElementById('usernameInput'),
        emailInput: document.getElementById('emailInput'),
        displayNameInput: document.getElementById('displayNameInput'),
        confirmLogin: document.getElementById('confirmLogin'),
        
        // 채널
        channelList: document.getElementById('channelList'),
        createChannelBtn: document.getElementById('createChannelBtn'),
        channelNameInput: document.getElementById('channelNameInput'),
        channelDescInput: document.getElementById('channelDescInput'),
        confirmCreateChannel: document.getElementById('confirmCreateChannel'),
        currentChannelName: document.getElementById('currentChannelName'),
        currentChannelDesc: document.getElementById('currentChannelDesc'),
        
        // 메시지
        messageArea: document.getElementById('messageArea'),
        messageInput: document.getElementById('messageInput'),
        sendBtn: document.getElementById('sendBtn'),
        
        // 사용자
        userList: document.getElementById('userList')
    };
    
    // 로그인 체크
    const savedUser = localStorage.getItem('currentUser');
    if (savedUser) {
        currentUser = JSON.parse(savedUser);
        elements.loginModal.classList.add('hidden');
        await loadInitialData();
    }
    
    // 이벤트 리스너
    setupEventListeners();
}

function setupEventListeners() {
    // 로그인
    elements.confirmLogin.addEventListener('click', handleLogin);
    
    // 채널 생성
    elements.createChannelBtn.addEventListener('click', openCreateChannelModal);
    elements.confirmCreateChannel.addEventListener('click', handleCreateChannel);
    
    // 모달 닫기
    document.querySelectorAll('.modal-close, .btn-cancel').forEach(btn => {
        btn.addEventListener('click', closeModals);
    });
    
    // 메시지 전송
    elements.sendBtn.addEventListener('click', handleSendMessage);
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
}

// ============================================
// 로그인
// ============================================
async function handleLogin() {
    const username = elements.usernameInput.value.trim();
    const email = elements.emailInput.value.trim();
    const displayName = elements.displayNameInput.value.trim();
    
    if (!username || !email) {
        alert('사용자 이름과 이메일을 입력해주세요');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/users`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                email,
                display_name: displayName || username
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            alert(error.error || '사용자 생성 실패');
            return;
        }
        
        currentUser = await response.json();
        localStorage.setItem('currentUser', JSON.stringify(currentUser));
        
        elements.loginModal.classList.add('hidden');
        await loadInitialData();
    } catch (error) {
        console.error('로그인 에러:', error);
        alert('서버 연결 실패');
    }
}

// ============================================
// 초기 데이터 로드
// ============================================
async function loadInitialData() {
    await Promise.all([
        loadChannels(),
        loadUsers()
    ]);
}

async function loadChannels() {
    try {
        const response = await fetch(`${API_URL}/channels`);
        channels = await response.json();
        renderChannels();
    } catch (error) {
        console.error('채널 로드 에러:', error);
    }
}

async function loadUsers() {
    try {
        const response = await fetch(`${API_URL}/users`);
        users = await response.json();
        renderUsers();
    } catch (error) {
        console.error('사용자 로드 에러:', error);
    }
}

// ============================================
// 렌더링
// ============================================
function renderChannels() {
    elements.channelList.innerHTML = channels.map(channel => `
        <div class="channel-item ${currentChannel?.id === channel.id ? 'active' : ''}" 
             data-id="${channel.id}">
            # ${channel.name}
        </div>
    `).join('');
    
    // 채널 클릭 이벤트
    document.querySelectorAll('.channel-item').forEach(item => {
        item.addEventListener('click', () => {
            const channelId = parseInt(item.dataset.id);
            selectChannel(channelId);
        });
    });
}

function renderUsers() {
    elements.userList.innerHTML = users.map(user => `
        <div class="user-item">
            <span class="status ${user.status === 'online' ? 'online' : 'offline'}"></span>
            ${user.display_name || user.username}
        </div>
    `).join('');
}

function renderMessages() {
    if (messages.length === 0) {
        elements.messageArea.innerHTML = `
            <div class="welcome-message">
                <h2>💬 대화를 시작해보세요!</h2>
                <p>아래 입력창에 메시지를 입력하세요.</p>
            </div>
        `;
        return;
    }
    
    elements.messageArea.innerHTML = messages.map(msg => {
        const initial = (msg.display_name || msg.username).charAt(0).toUpperCase();
        const time = new Date(msg.created_at).toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        
        return `
            <div class="message-item" data-id="${msg.id}">
                <div class="message-avatar">${initial}</div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-author">${msg.display_name || msg.username}</span>
                        <span class="message-time">${time}</span>
                        ${msg.is_edited ? '<span class="message-edited">(수정됨)</span>' : ''}
                    </div>
                    <div class="message-text">${escapeHtml(msg.content)}</div>
                    ${msg.user_id === currentUser.id ? `
                        <div class="message-actions">
                            <button onclick="editMessage(${msg.id})">수정</button>
                            <button onclick="deleteMessage(${msg.id})">삭제</button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
    
    // 스크롤 맨 아래로
    elements.messageArea.scrollTop = elements.messageArea.scrollHeight;
}

// ============================================
// 채널 관리
// ============================================
async function selectChannel(channelId) {
    currentChannel = channels.find(c => c.id === channelId);
    if (!currentChannel) return;
    
    // UI 업데이트
    elements.currentChannelName.textContent = `# ${currentChannel.name}`;
    elements.currentChannelDesc.textContent = currentChannel.description || '';
    elements.messageInput.disabled = false;
    elements.sendBtn.disabled = false;
    
    // 채널 목록 active 상태 업데이트
    renderChannels();
    
    // 메시지 로드
    await loadMessages(channelId);
}

async function loadMessages(channelId) {
    try {
        const response = await fetch(`${API_URL}/channels/${channelId}/messages`);
        messages = await response.json();
        renderMessages();
    } catch (error) {
        console.error('메시지 로드 에러:', error);
    }
}

function openCreateChannelModal() {
    elements.createChannelModal.classList.remove('hidden');
}

async function handleCreateChannel() {
    const name = elements.channelNameInput.value.trim();
    const description = elements.channelDescInput.value.trim();
    
    if (!name) {
        alert('채널 이름을 입력해주세요');
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/channels`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description,
                created_by: currentUser.id
            })
        });
        
        if (!response.ok) {
            alert('채널 생성 실패');
            return;
        }
        
        const newChannel = await response.json();
        channels.push(newChannel);
        renderChannels();
        
        elements.channelNameInput.value = '';
        elements.channelDescInput.value = '';
        closeModals();
        
        // 새 채널 선택
        selectChannel(newChannel.id);
    } catch (error) {
        console.error('채널 생성 에러:', error);
        alert('서버 연결 실패');
    }
}

// ============================================
// 메시지 관리
// ============================================
async function handleSendMessage() {
    const content = elements.messageInput.value.trim();
    
    if (!content || !currentChannel) return;
    
    try {
        const response = await fetch(`${API_URL}/channels/${currentChannel.id}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.id,
                content
            })
        });
        
        if (!response.ok) {
            alert('메시지 전송 실패');
            return;
        }
        
        const newMessage = await response.json();
        messages.push(newMessage);
        renderMessages();
        
        elements.messageInput.value = '';
    } catch (error) {
        console.error('메시지 전송 에러:', error);
        alert('서버 연결 실패');
    }
}

async function editMessage(messageId) {
    const message = messages.find(m => m.id === messageId);
    if (!message) return;
    
    const newContent = prompt('메시지 수정:', message.content);
    if (!newContent || newContent === message.content) return;
    
    try {
        const response = await fetch(`${API_URL}/messages/${messageId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent })
        });
        
        if (!response.ok) {
            alert('메시지 수정 실패');
            return;
        }
        
        await loadMessages(currentChannel.id);
    } catch (error) {
        console.error('메시지 수정 에러:', error);
    }
}

async function deleteMessage(messageId) {
    if (!confirm('이 메시지를 삭제하시겠습니까?')) return;
    
    try {
        const response = await fetch(`${API_URL}/messages/${messageId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            alert('메시지 삭제 실패');
            return;
        }
        
        await loadMessages(currentChannel.id);
    } catch (error) {
        console.error('메시지 삭제 에러:', error);
    }
}

// ============================================
// 유틸리티
// ============================================
function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.add('hidden');
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// 시작
// ============================================
init();