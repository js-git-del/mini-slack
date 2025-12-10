# 웹소켓 & API 학습 가이드

## 🎯 학습 목표
1. 웹소켓이 **어떻게** 작동하는지 이해
2. REST API와 웹소켓의 **차이점** 이해
3. **직접 구현하면서** 체득하기

---

## 📚 1단계: 기본 개념 이해 (30분)

### REST API vs WebSocket

```
REST API (HTTP):
클라이언트 → [요청] → 서버
클라이언트 ← [응답] ← 서버
(끝! 연결 종료)

WebSocket:
클라이언트 ↔ [계속 연결 유지] ↔ 서버
실시간 양방향 통신 가능!
```

### 실제 예시

#### REST API로 채팅 (비효율적)
```javascript
// 3초마다 서버에 새 메시지 있는지 물어봄 (polling)
setInterval(async () => {
    const response = await fetch('/api/messages');
    const messages = await response.json();
    // 새 메시지 확인...
}, 3000);
```
❌ 문제점: 3초 지연 + 불필요한 요청 많음

#### WebSocket으로 채팅 (효율적)
```javascript
// 서버가 새 메시지 있으면 바로 보내줌
socket.on('new_message', (message) => {
    // 즉시 표시!
});
```
✅ 장점: 즉시 수신 + 필요할 때만 통신

---

## 🔧 2단계: 핵심 코드 이해 (1시간)

### 백엔드 핵심 3가지

#### 1. Socket.IO 초기화
```python
# app.py
from flask_socketio import SocketIO, emit

socketio = SocketIO(app, cors_allowed_origins="*")
```
→ 이것만 하면 웹소켓 서버 완성!

#### 2. 이벤트 받기 (@socketio.on)
```python
@socketio.on('send_message')  # 클라이언트가 'send_message' 보내면
def handle_send_message(data):  # 이 함수 실행
    print(f"받은 메시지: {data}")
```

#### 3. 이벤트 보내기 (emit)
```python
# 특정 클라이언트에게만
emit('new_message', {'content': '안녕'})

# 모든 클라이언트에게
emit('new_message', {'content': '안녕'}, broadcast=True)

# 특정 Room(채널)에게만
emit('new_message', {'content': '안녕'}, room='channel_1')
```

### 프론트엔드 핵심 3가지

#### 1. 연결
```javascript
const socket = io('http://localhost:5000');
```

#### 2. 이벤트 받기
```javascript
socket.on('new_message', (message) => {
    console.log('받음:', message);
    // 화면에 표시
});
```

#### 3. 이벤트 보내기
```javascript
socket.emit('send_message', {
    content: '안녕하세요'
});
```

---

## 💡 3단계: Room 개념 (중요!)

### Room이 뭔가요?
→ **그룹 채팅방**이라고 생각하면 됨

```python
# 사용자를 특정 채널(Room)에 넣기
join_room('channel_1')

# 그 채널에 있는 사람들에게만 메시지 보내기
emit('new_message', data, room='channel_1')
```

### 실제 동작
```
채널1 Room
├─ 사용자A (socket_id: abc)
└─ 사용자B (socket_id: def)

채널2 Room
└─ 사용자C (socket_id: xyz)

emit('new_message', msg, room='채널1')
→ 사용자A, B만 받음 (C는 못 받음)
```

---

## 🎓 4단계: 실제 흐름 따라가기

### 메시지 전송 완전 분해

#### Step 1: 사용자가 "안녕" 입력 후 전송 버튼 클릭

**프론트엔드 (app.js)**
```javascript
function handleSendMessage() {
    const content = "안녕";  // 입력한 내용
    
    // 서버에 보내기
    socket.emit('send_message', {
        channel_id: 1,
        user_id: 5,
        content: "안녕"
    });
}
```

#### Step 2: 서버가 받음

**백엔드 (app.py)**
```python
@socketio.on('send_message')
def handle_send_message(data):
    # data = {channel_id: 1, user_id: 5, content: "안녕"}
    
    channel_id = data['channel_id']  # 1
    user_id = data['user_id']        # 5
    content = data['content']        # "안녕"
```

#### Step 3: DB에 저장

```python
    # DB에 INSERT
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO messages (channel_id, user_id, content) VALUES (%s, %s, %s)',
        (1, 5, "안녕")
    )
    conn.commit()
    
    message_id = cursor.lastrowid  # 새로 생성된 메시지 ID (예: 42)
```

#### Step 4: 저장된 메시지 조회

```python
    # 방금 저장한 메시지 다시 가져오기 (사용자 정보 포함)
    cursor.execute('''
        SELECT m.*, u.username, u.display_name 
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.id = %s
    ''', (42,))
    
    new_message = cursor.fetchone()
    # {
    #   id: 42,
    #   channel_id: 1,
    #   user_id: 5,
    #   content: "안녕",
    #   username: "hong",
    #   display_name: "홍길동",
    #   created_at: datetime(2025, 12, 10, 10, 30, 0)
    # }
```

#### Step 5: datetime 직렬화

```python
    # datetime을 문자열로 변환 (JSON 직렬화 가능하게)
    new_message = serialize_dict(new_message)
    # {
    #   ...
    #   created_at: "2025-12-10 10:30:00"  # 문자열로 변환됨
    # }
```

#### Step 6: 같은 채널 사용자들에게 브로드캐스트

```python
    # channel_1에 있는 모든 사용자에게 전송
    emit('new_message', new_message, room='channel_1')
```

#### Step 7: 프론트엔드가 받음

**프론트엔드 (app.js)**
```javascript
socket.on('new_message', (message) => {
    // message = {
    //   id: 42,
    //   content: "안녕",
    //   username: "hong",
    //   display_name: "홍길동",
    //   ...
    // }
    
    // 1. 현재 채널 메시지인지 확인
    if (currentChannel.id === message.channel_id) {
        
        // 2. 중복 체크
        if (!messages.find(m => m.id === message.id)) {
            
            // 3. 배열에 추가
            messages.push(message);
            
            // 4. 화면에 표시
            renderMessages();
        }
    }
});
```

### 완성! 🎉

```
사용자 → socket.emit → 
서버 → DB 저장 → 
서버 → room 브로드캐스트 → 
모든 사용자 socket.on으로 받음 → 
화면 업데이트
```

---

## 🔍 5단계: 자주 헷갈리는 부분

### Q1. emit와 on의 차이?
```javascript
// emit = 보내기
socket.emit('이벤트명', 데이터);

// on = 받기
socket.on('이벤트명', (데이터) => {
    // 처리
});
```
→ 양쪽 다 emit/on 있어야 통신 가능!

### Q2. 왜 datetime 직렬화?
```python
# DB에서 가져온 데이터
message = {
    'created_at': datetime(2025, 12, 10)  # Python 객체
}

# JSON으로 변환 시도
json.dumps(message)  # ❌ 에러! datetime은 JSON 안 됨

# 해결: 문자열로 변환
message['created_at'] = "2025-12-10 10:30:00"
json.dumps(message)  # ✅ 성공!
```

### Q3. room은 언제 쓰나?
```python
# Room 없이 (모두에게)
emit('notice', '공지사항', broadcast=True)

# Room 사용 (특정 채널만)
emit('new_message', msg, room='channel_1')
```
→ 채널별로 메시지 격리할 때 필수!

### Q4. join_room은 언제?
```python
# 채널 선택할 때
@socketio.on('join_channel')
def handle_join_channel(data):
    join_room(f"channel_{data['channel_id']}")
```
→ 이거 안 하면 room으로 보낸 메시지 못 받음!

---

## 🏋️ 6단계: 직접 구현해보기

### 연습 1: 온라인 사용자 수 표시 (30분)

**목표**: 현재 접속자 수를 실시간으로 표시

**힌트:**
```python
# 백엔드
online_count = 0

@socketio.on('connect')
def handle_connect():
    global online_count
    online_count += 1
    emit('online_count', {'count': online_count}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global online_count
    online_count -= 1
    emit('online_count', {'count': online_count}, broadcast=True)
```

```javascript
// 프론트엔드
socket.on('online_count', (data) => {
    document.getElementById('onlineCount').textContent = data.count;
});
```

### 연습 2: 읽음 표시 기능 (1시간)

**목표**: 메시지를 누가 읽었는지 표시

**구현 순서:**
1. DB에 `message_reads` 테이블 추가
2. 메시지 볼 때 `message_read` 이벤트 발생
3. 서버가 DB에 저장 후 브로드캐스트
4. 프론트엔드에서 "✓✓" 표시

### 연습 3: 파일 업로드 기능 (2시간)

**목표**: 이미지 첨부 기능

**구현 순서:**
1. REST API로 파일 업로드 (`/api/upload`)
2. 서버가 파일 저장 후 URL 반환
3. WebSocket으로 메시지 전송 (URL 포함)
4. 프론트엔드에서 이미지 표시

---

## 🎯 7단계: 완전히 이해했는지 체크리스트

스스로 답할 수 있으면 이해한 것!

### 기본
- [ ] Socket.IO가 뭔지 설명할 수 있나?
- [ ] emit()과 on()의 차이를 설명할 수 있나?
- [ ] REST API와 WebSocket의 차이를 설명할 수 있나?

### 중급
- [ ] Room이 왜 필요한지 설명할 수 있나?
- [ ] join_room()을 안 하면 어떻게 되는가?
- [ ] broadcast=True와 room의 차이는?

### 고급
- [ ] 메시지 전송 흐름을 그림으로 그릴 수 있나?
- [ ] datetime 직렬화가 왜 필요한지 설명할 수 있나?
- [ ] 중복 메시지를 어떻게 방지하는가?

### 실전
- [ ] 코드 안 보고 간단한 채팅 앱을 만들 수 있나?
- [ ] 에러가 나면 어디서 문제인지 찾을 수 있나?
- [ ] 새 기능을 추가할 수 있나?

---

## 💪 반복 학습 방법

### 1일차: 읽고 이해
- 코드 한 줄씩 읽으면서 무슨 일 하는지 파악
- 모르는 거 구글링

### 2일차: 주석 달기
- 코드에 한글 주석 직접 달기
- "이 함수는 ~를 한다" 식으로

### 3일차: 기능 끄고 켜기
- `join_room()` 주석 처리하면 어떻게 되나?
- `serialize_dict()` 제거하면 에러 나나?
- 실험해보면서 각 부분의 역할 이해

### 4일차: 처음부터 다시 만들기
- 코드 안 보고 빈 파일에서 시작
- 막히면 힌트만 보고 계속
- 완성하면 원본이랑 비교

### 5일차: 기능 추가
- 읽음 표시, 파일 업로드 등
- 새 기능 추가하면서 구조 이해

---

## 🐛 자주 만나는 에러들

### 1. "Socket.IO 연결 안 됨"
```javascript
// ❌ 잘못된 URL
socket = io('localhost:5000');

// ✅ 올바른 URL (http:// 필수!)
socket = io('http://localhost:5000');
```

### 2. "메시지가 안 보임"
```python
# join_room() 했는지 확인!
@socketio.on('join_channel')
def handle_join_channel(data):
    join_room(f"channel_{data['channel_id']}")  # 이거 필수!
```

### 3. "datetime 에러"
```python
# serialize_dict() 호출 잊지 말기!
new_message = cursor.fetchone()
new_message = serialize_dict(new_message)  # 이거!
emit('new_message', new_message, room=...)
```

### 4. "메시지가 중복으로 보임"
```javascript
// 중복 체크 필수!
if (!messages.find(m => m.id === message.id)) {
    messages.push(message);
}
```

---

## 📝 마지막 조언

### 이해 vs 암기
```
❌ "이 코드는 외워야지"
✅ "이 코드가 왜 필요한지 이해해야지"
```

### 실패는 학습의 일부
```
에러 나면 → 구글링 → 이해 → 해결
이 과정이 진짜 실력 향상!
```

### 작게 시작하기
```
처음부터 완벽하게 만들려고 하지 말고
간단한 기능부터 하나씩 추가
```

---

## 🎉 다음 단계 학습 로드맵

1. ✅ **현재**: 기본 WebSocket + REST API
2. 📚 **다음**: JWT 인증 추가
3. 🔐 **그 다음**: Redis로 세션 관리
4. 🚀 **고급**: 메시지 큐 (Celery)
5. 📈 **전문가**: 수평 확장 (Load Balancer)

---

**화이팅! 반복하다 보면 손에 익습니다** 💪