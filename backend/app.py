from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import pymysql
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Socket.IO 설정
socketio = SocketIO(app, cors_allowed_origins="*")

# MariaDB 연결 설정
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Admin123!@#',
    'database': 'api_test',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    return pymysql.connect(**DB_CONFIG)

# 온라인 사용자 추적
online_users = {}  # {user_id: socket_id}

# datetime을 JSON 직렬화 가능한 형태로 변환
def serialize_datetime(obj):
    """datetime 객체를 문자열로 변환"""
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    return obj

def serialize_dict(data):
    """딕셔너리의 모든 datetime 객체를 문자열로 변환"""
    if isinstance(data, dict):
        return {key: serialize_datetime(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [serialize_dict(item) for item in data]
    return data

# ============================================
# Socket.IO 이벤트 핸들러
# ============================================

@socketio.on('connect')
def handle_connect():
    print(f'클라이언트 연결됨: {request.sid}')
    emit('connected', {'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'클라이언트 연결 해제됨: {request.sid}')
    
    # 온라인 사용자 목록에서 제거
    user_id_to_remove = None
    for user_id, sid in online_users.items():
        if sid == request.sid:
            user_id_to_remove = user_id
            break
    
    if user_id_to_remove:
        del online_users[user_id_to_remove]
        # 모든 클라이언트에게 사용자 오프라인 알림
        emit('user_status_changed', {
            'user_id': user_id_to_remove,
            'status': 'offline'
        }, broadcast=True)

@socketio.on('user_online')
def handle_user_online(data):
    """사용자 온라인 상태 알림"""
    user_id = data.get('user_id')
    if user_id:
        online_users[user_id] = request.sid
        
        # 데이터베이스에서 사용자 정보 가져오기
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, display_name FROM users WHERE id = %s', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # 모든 클라이언트에게 사용자 온라인 알림
            emit('user_status_changed', {
                'user_id': user_id,
                'status': 'online',
                'user': user
            }, broadcast=True)
            
            # 현재 온라인 사용자 목록 전송
            emit('online_users', {'user_ids': list(online_users.keys())})

@socketio.on('join_channel')
def handle_join_channel(data):
    """채널 입장"""
    channel_id = data.get('channel_id')
    if channel_id:
        join_room(f'channel_{channel_id}')
        print(f'사용자가 채널 {channel_id}에 입장했습니다')
        emit('joined_channel', {'channel_id': channel_id})

@socketio.on('leave_channel')
def handle_leave_channel(data):
    """채널 퇴장"""
    channel_id = data.get('channel_id')
    if channel_id:
        leave_room(f'channel_{channel_id}')
        print(f'사용자가 채널 {channel_id}에서 퇴장했습니다')

@socketio.on('send_message')
def handle_send_message(data):
    """실시간 메시지 전송"""
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    content = data.get('content')
    
    if not all([channel_id, user_id, content]):
        emit('error', {'message': '필수 데이터가 누락되었습니다'})
        return
    
    try:
        # 데이터베이스에 메시지 저장
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO messages (channel_id, user_id, content) VALUES (%s, %s, %s)',
            (channel_id, user_id, content)
        )
        conn.commit()
        
        message_id = cursor.lastrowid
        
        # 저장된 메시지 정보 가져오기 (사용자 정보 포함)
        cursor.execute('''
            SELECT m.*, u.username, u.display_name 
            FROM messages m
            JOIN users u ON m.user_id = u.id
            WHERE m.id = %s
        ''', (message_id,))
        
        new_message = cursor.fetchone()
        conn.close()
        
        # datetime 직렬화
        new_message = serialize_dict(new_message)
        
        # 같은 채널의 모든 사용자에게 메시지 브로드캐스트
        emit('new_message', new_message, room=f'channel_{channel_id}')
        
    except Exception as e:
        print(f'메시지 전송 에러: {e}')
        emit('error', {'message': '메시지 전송에 실패했습니다'})

@socketio.on('typing')
def handle_typing(data):
    """타이핑 중 알림"""
    channel_id = data.get('channel_id')
    user_id = data.get('user_id')
    username = data.get('username')
    is_typing = data.get('is_typing', True)
    
    if channel_id:
        # 본인을 제외한 같은 채널의 사용자들에게 알림
        emit('user_typing', {
            'user_id': user_id,
            'username': username,
            'is_typing': is_typing
        }, room=f'channel_{channel_id}', include_self=False)

@socketio.on('message_updated')
def handle_message_updated(data):
    """메시지 수정 알림"""
    channel_id = data.get('channel_id')
    message = data.get('message')
    
    if channel_id and message:
        message = serialize_dict(message)
        emit('message_updated', message, room=f'channel_{channel_id}')

@socketio.on('message_deleted')
def handle_message_deleted(data):
    """메시지 삭제 알림"""
    channel_id = data.get('channel_id')
    message_id = data.get('message_id')
    
    if channel_id and message_id:
        emit('message_deleted', {'message_id': message_id}, room=f'channel_{channel_id}')

@socketio.on('new_channel')
def handle_new_channel(data):
    """새 채널 생성 알림"""
    channel = data.get('channel')
    if channel:
        channel = serialize_dict(channel)
        emit('channel_created', channel, broadcast=True)

# ============================================
# 홈
# ============================================
@app.route('/')
def home():
    return jsonify({
        "message": "미니 슬랙 API with WebSocket",
        "version": "2.0.0",
        "endpoints": {
            "login": "/api/login",
            "users": "/api/users",
            "channels": "/api/channels",
            "messages": "/api/channels/:id/messages"
        },
        "websocket": "Socket.IO enabled"
    })

# ============================================
# 사용자 API
# ============================================

# 로그인
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'email' not in data:
        return jsonify({"error": "username과 email은 필수입니다"}), 400
    
    username = data['username']
    email = data['email']
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT id, username, email, display_name, status FROM users WHERE username = %s AND email = %s', 
        (username, email)
    )
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({"error": "사용자 이름 또는 이메일이 일치하지 않습니다"}), 404
    
    return jsonify(user), 200

# 사용자 목록 조회
@app.route('/api/users', methods=['GET'])
def get_users():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, email, display_name, status FROM users')
    users = cursor.fetchall()
    conn.close()
    
    # 온라인 상태 정보 추가
    for user in users:
        user['is_online'] = user['id'] in online_users
    
    return jsonify(users), 200

# 사용자 생성
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    if not data or 'username' not in data or 'email' not in data:
        return jsonify({"error": "username, email은 필수입니다"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'INSERT INTO users (username, email, display_name, status) VALUES (%s, %s, %s, %s)',
            (data['username'], data['email'], data.get('display_name', data['username']), 'online')
        )
        conn.commit()
        
        user_id = cursor.lastrowid
        cursor.execute('SELECT id, username, email, display_name, status FROM users WHERE id = %s', (user_id,))
        new_user = cursor.fetchone()
        conn.close()
        
        return jsonify(new_user), 201
    except pymysql.IntegrityError:
        conn.close()
        return jsonify({"error": "이미 존재하는 username 또는 email입니다"}), 400

# ============================================
# 채널 API
# ============================================

# 채널 목록 조회
@app.route('/api/channels', methods=['GET'])
def get_channels():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, u.username as creator_name 
        FROM channels c 
        LEFT JOIN users u ON c.created_by = u.id
        ORDER BY c.created_at DESC
    ''')
    channels = cursor.fetchall()
    conn.close()
    return jsonify(channels), 200

# 채널 생성
@app.route('/api/channels', methods=['POST'])
def create_channel():
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({"error": "name은 필수입니다"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    created_by = data.get('created_by', 1)
    
    cursor.execute(
        'INSERT INTO channels (name, description, is_private, created_by) VALUES (%s, %s, %s, %s)',
        (data['name'], data.get('description', ''), data.get('is_private', False), created_by)
    )
    conn.commit()
    
    channel_id = cursor.lastrowid
    cursor.execute('SELECT * FROM channels WHERE id = %s', (channel_id,))
    new_channel = cursor.fetchone()
    conn.close()
    
    # datetime 직렬화
    new_channel = serialize_dict(new_channel)
    
    # 웹소켓으로 새 채널 생성 알림
    socketio.emit('channel_created', new_channel)
    
    return jsonify(new_channel), 201

# 특정 채널 조회
@app.route('/api/channels/<int:channel_id>', methods=['GET'])
def get_channel(channel_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM channels WHERE id = %s', (channel_id,))
    channel = cursor.fetchone()
    conn.close()
    
    if channel:
        return jsonify(channel), 200
    return jsonify({"error": "채널을 찾을 수 없습니다"}), 404

# 채널 삭제
@app.route('/api/channels/<int:channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM channels WHERE id = %s', (channel_id,))
    channel = cursor.fetchone()
    
    if not channel:
        conn.close()
        return jsonify({"error": "채널을 찾을 수 없습니다"}), 404
    
    cursor.execute('DELETE FROM channels WHERE id = %s', (channel_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "채널이 삭제되었습니다", "deleted_channel": channel}), 200

# ============================================
# 메시지 API
# ============================================

# 채널의 메시지 목록 조회
@app.route('/api/channels/<int:channel_id>/messages', methods=['GET'])
def get_messages(channel_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT m.*, u.username, u.display_name 
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.channel_id = %s
        ORDER BY m.created_at ASC
    ''', (channel_id,))
    
    messages = cursor.fetchall()
    conn.close()
    return jsonify(messages), 200

# 메시지 전송 (REST API - 웹소켓과 병행)
@app.route('/api/channels/<int:channel_id>/messages', methods=['POST'])
def send_message(channel_id):
    data = request.get_json()
    
    if not data or 'content' not in data or 'user_id' not in data:
        return jsonify({"error": "content, user_id는 필수입니다"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO messages (channel_id, user_id, content) VALUES (%s, %s, %s)',
        (channel_id, data['user_id'], data['content'])
    )
    conn.commit()
    
    message_id = cursor.lastrowid
    cursor.execute('''
        SELECT m.*, u.username, u.display_name 
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.id = %s
    ''', (message_id,))
    new_message = cursor.fetchone()
    conn.close()
    
    # datetime 직렬화
    new_message = serialize_dict(new_message)
    
    # 웹소켓으로 실시간 전송
    socketio.emit('new_message', new_message, room=f'channel_{channel_id}')
    
    return jsonify(new_message), 201

# 메시지 수정
@app.route('/api/messages/<int:message_id>', methods=['PUT'])
def update_message(message_id):
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({"error": "content는 필수입니다"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT channel_id FROM messages WHERE id = %s', (message_id,))
    message = cursor.fetchone()
    
    if not message:
        conn.close()
        return jsonify({"error": "메시지를 찾을 수 없습니다"}), 404
    
    channel_id = message['channel_id']
    
    cursor.execute(
        'UPDATE messages SET content = %s, is_edited = TRUE WHERE id = %s',
        (data['content'], message_id)
    )
    conn.commit()
    
    cursor.execute('''
        SELECT m.*, u.username, u.display_name 
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.id = %s
    ''', (message_id,))
    updated_message = cursor.fetchone()
    conn.close()
    
    # datetime 직렬화
    updated_message = serialize_dict(updated_message)
    
    # 웹소켓으로 수정 알림
    socketio.emit('message_updated', updated_message, room=f'channel_{channel_id}')
    
    return jsonify(updated_message), 200

# 메시지 삭제
@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT channel_id FROM messages WHERE id = %s', (message_id,))
    message = cursor.fetchone()
    
    if not message:
        conn.close()
        return jsonify({"error": "메시지를 찾을 수 없습니다"}), 404
    
    channel_id = message['channel_id']
    
    cursor.execute('DELETE FROM messages WHERE id = %s', (message_id,))
    conn.commit()
    conn.close()
    
    # 웹소켓으로 삭제 알림
    socketio.emit('message_deleted', {'message_id': message_id}, room=f'channel_{channel_id}')
    
    return jsonify({"message": "메시지가 삭제되었습니다"}), 200

# ============================================
# 반응(Reactions) API
# ============================================

# 메시지에 반응 추가
@app.route('/api/messages/<int:message_id>/reactions', methods=['POST'])
def add_reaction(message_id):
    data = request.get_json()
    
    if not data or 'user_id' not in data or 'emoji' not in data:
        return jsonify({"error": "user_id, emoji는 필수입니다"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT INTO reactions (message_id, user_id, emoji) VALUES (%s, %s, %s)',
        (message_id, data['user_id'], data['emoji'])
    )
    conn.commit()
    
    reaction_id = cursor.lastrowid
    cursor.execute('SELECT * FROM reactions WHERE id = %s', (reaction_id,))
    new_reaction = cursor.fetchone()
    conn.close()
    
    return jsonify(new_reaction), 201

# 메시지의 반응 목록
@app.route('/api/messages/<int:message_id>/reactions', methods=['GET'])
def get_reactions(message_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM reactions WHERE message_id = %s', (message_id,))
    reactions = cursor.fetchall()
    conn.close()
    
    return jsonify(reactions), 200

if __name__ == '__main__':
    # Flask-SocketIO를 사용할 때는 socketio.run() 사용
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)