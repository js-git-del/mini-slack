const API_URL = 'http://localhost:5000/api';
const SOCKET_URL = 'http://localhost:5000';

// Socket.IO 클라이언트
let socket = null;

// 전역 상태
let currentUser = null;
let currentChannel = null;
let channels = [];
let users = [];
let messages = [];
let elements = {};
let typingTimeout = null;

// ============================================
// 초기화
// ============================================
async function init() {
    // 로그인 체크
    const savedUser = localStorage.getItem('currentUser');
    if (!savedUser) {
        window.location.href = 'login.html';
        return;
    }
    
    currentUser = JSON.parse(savedUser);
    
    // DOM 요소
    elements = {
        createChannelModal: document.getElementById('createChannelModal'),
        channelList: document.getElementById('channelList'),
        createChannelBtn: document.getElementById('createChannelBtn'),
        channelNameInput: document.getElementById('channelNameInput'),
        channelDescInput: document.getElementById('channelDescInput'),
        confirmCreateChannel: document.getElementById('confirmCreateChannel'),
        currentChannelName: document.getElementById('currentChannelName'),
        currentChannelDesc: document.getElementById('currentChannelDesc'),
        messageArea: document.getElementById('messageArea'),
        messageInput: document.getElementById('messageInput'),
        sendBtn: document.getElementById('sendBtn'),
        userList: document.getElementById('userList'),
        currentUserName: document.getElementById('currentUserName'),
        logoutBtn: document.getElementById('logoutBtn'),
        typingIndicator: document.getElementById('typingIndicator')
    };
    
    elements.currentUserName.textContent = currentUser.display_name || currentUser.username;
    
    setupEventListeners();
    
    // Socket.IO 연결
    initializeSocket();
    
    // 초기 데이터 로드
    await loadInitialData();
}

// ============================================
// Socket.IO 초기화 및 이벤트 핸들러
// ============================================
function initializeSocket() {
    socket = io(SOCKET_URL, {
        transports: ['websocket', 'polling']
    });
    
    // 연결 이벤트
    socket.on('connect', () => {
        console.log('✅ Socket.IO 연결됨:', socket.id);
        
        // 사용자 온라인 상태 알림
        socket.emit('user_online', { user_id: currentUser.id });
    });
    
    socket.on('disconnect', () => {
        console.log('❌ Socket.IO 연결 해제됨');
    });
    
    socket.on('error', (error) => {
        console.error('Socket 에러:', error);
    });
    
    // 사용자 상태 변경
    socket.on('user_status_changed', (data) => {
        console.log('사용자 상태 변경:', data);
        loadUsers();
    });
    
    // 온라인 사용자 목록
    socket.on('online_users', (data) => {
        console.log('온라인 사용자:', data.user_ids);
    });
    
    // 새 메시지 수신
    socket.on('new_message', (message) => {
        console.log('새 메시지 수신:', message);
        
        // 현재 채널의 메시지인 경우에만 추가
        if (currentChannel && message.channel_id === currentChannel.id) {
            // 중복 방지
            if (!messages.find(m => m.id === message.id)) {
                messages.push(message);
                renderMessages();
            }
        }
    });
    
    // 메시지 수정
    socket.on('message_updated', (message) => {
        console.log('메시지 수정됨:', message);
        
        if (currentChannel && message.channel_id === currentChannel.id) {
            const index = messages.findIndex(m => m.id === message.id);
            if (index !== -1) {
                messages[index] = message;
                renderMessages();
            }
        }
    });
    
    // 메시지 삭제
    socket.on('message_deleted', (data) => {
        console.log('메시지 삭제됨:', data.message_id);
        
        const index = messages.findIndex(m => m.id === data.message_id);
        if (index !== -1) {
            messages.splice(index, 1);
            renderMessages();
        }
    });
    
    // 타이핑 중 표시
    socket.on('user_typing', (data) => {
        if (data.is_typing) {
            showTypingIndicator(data.username);
        } else {
            hideTypingIndicator();
        }
    });
    
    // 새 채널 생성 알림
    socket.on('channel_created', (channel) => {
        console.log('새 채널 생성됨:', channel);
        if (!channels.find(c => c.id === channel.id)) {
            channels.push(channel);
            renderChannels();
        }
    });
}

// ============================================
// 타이핑 표시
// ============================================
function showTypingIndicator(username) {
    if (elements.typingIndicator) {
        elements.typingIndicator.textContent = `${username}님이 입력 중...`;
        elements.typingIndicator.style.display = 'block';
    }
}

function hideTypingIndicator() {
    if (elements.typingIndicator) {
        elements.typingIndicator.style.display = 'none';
    }
}

function handleTyping() {
    if (!currentChannel) return;
    
    // 타이핑 시작 알림
    socket.emit('typing', {
        channel_id: currentChannel.id,
        user_id: currentUser.id,
        username: currentUser.display_name || currentUser.username,
        is_typing: true
    });
    
    // 타이핑 멈춤 타이머
    if (typingTimeout) {
        clearTimeout(typingTimeout);
    }
    
    typingTimeout = setTimeout(() => {
        socket.emit('typing', {
            channel_id: currentChannel.id,
            user_id: currentUser.id,
            username: currentUser.display_name || currentUser.username,
            is_typing: false
        });
    }, 2000);
}

// ============================================
// 이벤트 리스너 설정
// ============================================
function setupEventListeners() {
    elements.logoutBtn.addEventListener('click', handleLogout);
    elements.createChannelBtn.addEventListener('click', openCreateChannelModal);
    elements.confirmCreateChannel.addEventListener('click', handleCreateChannel);
    
    document.querySelectorAll('.modal-close, .btn-cancel').forEach(btn => {
        btn.addEventListener('click', closeModals);
    });
    
    elements.sendBtn.addEventListener('click', handleSendMessage);
    
    elements.messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // 타이핑 감지
    elements.messageInput.addEventListener('input', handleTyping);
}

// ============================================
// 데이터 로드
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
        
        // 첫 번째 채널 자동 선택
        if (channels.length > 0 && !currentChannel) {
            selectChannel(channels[0].id);
        }
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

async function loadMessages(channelId) {
    try {
        const response = await fetch(`${API_URL}/channels/${channelId}/messages`);
        messages = await response.json();
        renderMessages();
    } catch (error) {
        console.error('메시지 로드 에러:', error);
    }
}

// ============================================
// 렌더링
// ============================================
function renderChannels() {
    elements.channelList.innerHTML = channels.map(channel => `
        <div class="channel-item ${currentChannel && currentChannel.id === channel.id ? 'active' : ''}" 
             onclick="selectChannel(${channel.id})">
            <span class="channel-hash">#</span>
            <span class="channel-name">${escapeHtml(channel.name)}</span>
        </div>
    `).join('');
}

function renderUsers() {
    elements.userList.innerHTML = users.map(user => `
        <div class="user-item ${user.is_online ? 'online' : 'offline'}">
            <span class="user-status"></span>
            <span class="user-name">${escapeHtml(user.display_name || user.username)}</span>
        </div>
    `).join('');
}

function renderMessages() {
    if (messages.length === 0) {
        elements.messageArea.innerHTML = `
            <div class="welcome-message">
                <h2>👋 채널에 오신 것을 환영합니다!</h2>
                <p>첫 메시지를 보내보세요.</p>
            </div>
        `;
        return;
    }
    
    elements.messageArea.innerHTML = messages.map(msg => {
        const timestamp = new Date(msg.created_at).toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        return `
            <div class="message ${msg.user_id === currentUser.id ? 'own-message' : ''}">
                <div class="message-avatar">
                    ${(msg.display_name || msg.username).charAt(0).toUpperCase()}
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-author">${escapeHtml(msg.display_name || msg.username)}</span>
                        <span class="message-time">${timestamp}</span>
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
    
    elements.messageArea.scrollTop = elements.messageArea.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// 채널 관리
// ============================================
async function selectChannel(channelId) {
    // 이전 채널에서 퇴장
    if (currentChannel) {
        socket.emit('leave_channel', { channel_id: currentChannel.id });
    }
    
    currentChannel = channels.find(c => c.id === channelId);
    if (!currentChannel) return;
    
    // 새 채널에 입장
    socket.emit('join_channel', { channel_id: currentChannel.id });
    
    elements.currentChannelName.textContent = `# ${currentChannel.name}`;
    elements.currentChannelDesc.textContent = currentChannel.description || '';
    elements.messageInput.disabled = false;
    elements.sendBtn.disabled = false;
    
    renderChannels();
    await loadMessages(channelId);
}

function openCreateChannelModal() {
    elements.createChannelModal.classList.remove('hidden');
}

function closeModals() {
    elements.createChannelModal.classList.add('hidden');
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
        
        elements.channelNameInput.value = '';
        elements.channelDescInput.value = '';
        closeModals();
        
        // Socket.IO로 알림은 자동으로 전달됨
        // 새 채널 선택
        await loadChannels();
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
    
    // Socket.IO로 실시간 전송
    socket.emit('send_message', {
        channel_id: currentChannel.id,
        user_id: currentUser.id,
        content: content
    });
    
    elements.messageInput.value = '';
    
    // 타이핑 표시 숨김
    socket.emit('typing', {
        channel_id: currentChannel.id,
        user_id: currentUser.id,
        username: currentUser.display_name || currentUser.username,
        is_typing: false
    });
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
        
        // Socket.IO가 자동으로 업데이트 알림
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
        
        // Socket.IO가 자동으로 삭제 알림
    } catch (error) {
        console.error('메시지 삭제 에러:', error);
    }
}

// ============================================
// 로그아웃
// ============================================
function handleLogout() {
    if (confirm('로그아웃하시겠습니까?')) {
        // Socket 연결 해제
        if (socket) {
            socket.disconnect();
        }
        
        localStorage.removeItem('currentUser');
        window.location.href = 'login.html';
    }
}

// ============================================
// 앱 시작
// ============================================
document.addEventListener('DOMContentLoaded', init);