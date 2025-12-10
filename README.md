# 미니 슬랙 (WebSocket 버전)

실시간 메시징 기능이 추가된 슬랙 클론 프로젝트입니다.

## ✨ 주요 기능

### 기본 기능
- 사용자 로그인/회원가입
- 채널 생성 및 관리
- 실시간 메시지 전송
- 메시지 수정/삭제

### 🚀 WebSocket 기능 (NEW!)
- ✅ **실시간 메시지 전송**: 새로고침 없이 즉시 메시지 표시
- ✅ **온라인 사용자 표시**: 실시간 사용자 상태 업데이트
- ✅ **타이핑 표시**: 다른 사용자가 입력 중일 때 표시
- ✅ **실시간 채널 업데이트**: 새 채널 생성 시 모든 사용자에게 알림
- ✅ **메시지 수정/삭제 동기화**: 모든 사용자에게 실시간 반영
- ✅ **자동 재연결**: 연결이 끊어져도 자동으로 재연결

## 🛠 기술 스택

### 백엔드
- Python 3.x
- Flask
- **Flask-SocketIO** (WebSocket 지원)
- PyMySQL
- MariaDB/MySQL

### 프론트엔드
- HTML5
- CSS3
- Vanilla JavaScript
- **Socket.IO Client** (WebSocket 클라이언트)

## 📦 설치 방법

### 1. 백엔드 설정

```bash
cd backend

# 가상환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

**requirements.txt:**
```
Flask==3.0.0
flask-cors==4.0.0
flask-socketio==5.3.6
python-socketio==5.10.0
PyMySQL==1.1.0
```

### 2. 데이터베이스 설정

```sql
-- 데이터베이스 생성
CREATE DATABASE api_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE api_test;

-- 사용자 테이블
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'offline',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 채널 테이블
CREATE TABLE channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_private BOOLEAN DEFAULT FALSE,
    created_by INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 메시지 테이블
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    is_edited BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 반응 테이블 (선택사항)
CREATE TABLE reactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    user_id INT NOT NULL,
    emoji VARCHAR(10) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 3. 백엔드 실행

```bash
cd backend
python app.py
```

서버가 http://localhost:5000 에서 실행됩니다.

### 4. 프론트엔드 실행

```bash
cd frontend
npm install
npm start
```

프론트엔드가 http://localhost:3000 에서 실행됩니다.

## 🔌 WebSocket 이벤트

### 클라이언트 → 서버

| 이벤트 | 설명 | 데이터 |
|--------|------|--------|
| `connect` | 소켓 연결 | - |
| `user_online` | 사용자 온라인 상태 | `{user_id}` |
| `join_channel` | 채널 입장 | `{channel_id}` |
| `leave_channel` | 채널 퇴장 | `{channel_id}` |
| `send_message` | 메시지 전송 | `{channel_id, user_id, content}` |
| `typing` | 타이핑 중 | `{channel_id, user_id, username, is_typing}` |

### 서버 → 클라이언트

| 이벤트 | 설명 | 데이터 |
|--------|------|--------|
| `connected` | 연결 완료 | `{sid}` |
| `user_status_changed` | 사용자 상태 변경 | `{user_id, status, user}` |
| `online_users` | 온라인 사용자 목록 | `{user_ids}` |
| `new_message` | 새 메시지 | `{message object}` |
| `message_updated` | 메시지 수정 | `{message object}` |
| `message_deleted` | 메시지 삭제 | `{message_id}` |
| `user_typing` | 타이핑 중 표시 | `{user_id, username, is_typing}` |
| `channel_created` | 새 채널 생성 | `{channel object}` |

## 📱 사용법

1. **회원가입/로그인**
   - 브라우저에서 http://localhost:3000 접속
   - 사용자 이름과 이메일로 로그인

2. **채널 생성**
   - "+ 채널 생성" 버튼 클릭
   - 채널 이름과 설명 입력

3. **실시간 채팅**
   - 채널 선택
   - 메시지 입력 후 전송
   - 다른 사용자의 메시지가 실시간으로 표시됨

4. **타이핑 표시**
   - 메시지를 입력하면 다른 사용자에게 타이핑 중 표시

5. **온라인 상태**
   - 오른쪽 사이드바에서 온라인 사용자 확인

## 🔧 설정

### 백엔드 설정 (app.py)

```python
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Admin123!@#',
    'database': 'api_test',
    'charset': 'utf8mb4'
}

# Socket.IO CORS 설정
socketio = SocketIO(app, cors_allowed_origins="*")
```

### 프론트엔드 설정 (app.js)

```javascript
const API_URL = 'http://localhost:5000/api';
const SOCKET_URL = 'http://localhost:5000';

// Socket.IO 옵션
socket = io(SOCKET_URL, {
    transports: ['websocket', 'polling']
});
```

## 🐛 문제 해결

### WebSocket 연결 실패
```
- CORS 설정 확인
- 백엔드가 실행 중인지 확인
- 포트 충돌 확인 (5000번 포트)
```

### 메시지가 실시간으로 표시되지 않음
```
- 브라우저 콘솔에서 Socket 연결 상태 확인
- 채널에 join 했는지 확인
- 네트워크 탭에서 WebSocket 연결 확인
```

### 타이핑 표시가 작동하지 않음
```
- 타이핑 이벤트가 발생하는지 확인
- 다른 사용자가 같은 채널에 있는지 확인
```

## 📈 향후 개선 사항

- [ ] 파일 업로드 기능
- [ ] 이미지 미리보기
- [ ] 읽음/안읽음 표시
- [ ] 멘션(@) 기능
- [ ] 스레드(답글) 기능
- [ ] 이모지 반응
- [ ] 음성/영상 통화
- [ ] 푸시 알림

## 📄 라이선스

MIT License

## 👥 기여

이슈와 PR은 언제나 환영합니다!