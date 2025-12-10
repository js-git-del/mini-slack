from flask import Flask, jsonify, request
from flask_cors import CORS
import pymysql
from datetime import datetime

app = Flask(__name__)
CORS(app)

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

# ============================================
# 홈
# ============================================
@app.route('/')
def home():
    return jsonify({
        "message": "미니 슬랙 API",
        "version": "1.0.0",
        "endpoints": {
            "login": "/api/login",
            "users": "/api/users",
            "channels": "/api/channels",
            "messages": "/api/channels/:id/messages"
        }
    })

# ============================================
# 사용자 API
# ============================================

# 로그인 (새로 추가!)
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or 'username' not in data or 'email' not in data:
        return jsonify({"error": "username과 email은 필수입니다"}), 400
    
    username = data['username']
    email = data['email']
    
    conn = get_db()
    cursor = conn.cursor()
    
    # username과 email이 둘 다 일치하는 사용자 조회
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
    return jsonify(users), 200

# 사용자 생성 (간단 버전 - 비밀번호 없음)
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
    
    # created_by는 요청에서 받거나 기본값 사용
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
    
    # 메시지와 작성자 정보를 JOIN
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

# 메시지 전송
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
    
    return jsonify(new_message), 201

# 메시지 수정
@app.route('/api/messages/<int:message_id>', methods=['PUT'])
def update_message(message_id):
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({"error": "content는 필수입니다"}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM messages WHERE id = %s', (message_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "메시지를 찾을 수 없습니다"}), 404
    
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
    
    return jsonify(updated_message), 200

# 메시지 삭제
@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def delete_message(message_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM messages WHERE id = %s', (message_id,))
    message = cursor.fetchone()
    
    if not message:
        conn.close()
        return jsonify({"error": "메시지를 찾을 수 없습니다"}), 404
    
    cursor.execute('DELETE FROM messages WHERE id = %s', (message_id,))
    conn.commit()
    conn.close()
    
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
    
    try:
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
    except pymysql.IntegrityError:
        conn.close()
        return jsonify({"error": "이미 이 메시지에 같은 반응을 했습니다"}), 400

# 메시지의 반응 목록 조회
@app.route('/api/messages/<int:message_id>/reactions', methods=['GET'])
def get_reactions(message_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.*, u.username 
        FROM reactions r
        JOIN users u ON r.user_id = u.id
        WHERE r.message_id = %s
    ''', (message_id,))
    reactions = cursor.fetchall()
    conn.close()
    return jsonify(reactions), 200

# 반응 삭제
@app.route('/api/reactions/<int:reaction_id>', methods=['DELETE'])
def delete_reaction(reaction_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM reactions WHERE id = %s', (reaction_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "반응이 삭제되었습니다"}), 200

if __name__ == '__main__':
    print("="*50)
    print("💬 미니 슬랙 API 서버 시작")
    print("📍 URL: http://localhost:5000")
    print("🗄️ Database: MariaDB (api_test)")
    print("="*50)
    app.run(debug=True, host='0.0.0.0', port=5000)