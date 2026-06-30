import sqlite3
import hashlib
import os
import uuid
from aiohttp import web
from datetime import datetime
import aiofiles  # pip install aiofiles

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user TEXT NOT NULL,
            to_user TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            delivered BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ----- Обработчики HTTP -----

async def register(request):
    data = await request.json()
    login = data.get('login')
    password = data.get('password')
    print(f"[REGISTER] login={login}")
    if not login or not password:
        return web.json_response({'status': 'error', 'message': 'Missing fields'}, status=400)
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users (login, password_hash) VALUES (?, ?)",
                  (login, hash_password(password)))
        conn.commit()
        conn.close()
        print(f"[REGISTER] Успех для {login}")
        return web.json_response({'status': 'ok'})
    except sqlite3.IntegrityError:
        print(f"[REGISTER] Логин {login} уже существует")
        return web.json_response({'status': 'error', 'message': 'Login already exists'}, status=409)
    except Exception as e:
        print(f"[REGISTER] Ошибка: {e}")
        return web.json_response({'status': 'error', 'message': str(e)}, status=500)

async def login(request):
    data = await request.json()
    login = data.get('login')
    password = data.get('password')
    print(f"[LOGIN] login={login}")
    if not login or not password:
        return web.json_response({'status': 'error', 'message': 'Missing fields'}, status=400)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE login=?", (login,))
    row = c.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        print(f"[LOGIN] Успех для {login}")
        return web.json_response({'status': 'ok'})
    else:
        print(f"[LOGIN] Неверные данные для {login}")
        return web.json_response({'status': 'error', 'message': 'Invalid credentials'}, status=401)

async def upload_file(request):
    """Принимает файл и сохраняет в uploads, возвращает URL."""
    reader = await request.multipart()
    field = await reader.next()
    if field.name != 'file':
        return web.json_response({'status': 'error', 'message': 'No file part'}, status=400)
    filename = field.filename
    if not filename:
        return web.json_response({'status': 'error', 'message': 'No filename'}, status=400)
    ext = os.path.splitext(filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    async with aiofiles.open(file_path, 'wb') as f:
        while True:
            chunk = await field.read_chunk()
            if not chunk:
                break
            await f.write(chunk)
    file_url = f"/uploads/{unique_name}"
    return web.json_response({'status': 'ok', 'url': file_url})

async def send_message(request):
    data = await request.json()
    from_user = data.get('from')
    to_user = data.get('to')
    content = data.get('content')
    file_url = data.get('file_url', None)
    if not all([from_user, to_user, content]):
        return web.json_response({'status': 'error', 'message': 'Missing fields'}, status=400)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    full_content = content
    if file_url:
        full_content += f"\n[Файл: {file_url}]"
    c.execute("INSERT INTO messages (from_user, to_user, content, timestamp, delivered) VALUES (?, ?, ?, ?, 0)",
              (from_user, to_user, full_content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return web.json_response({'status': 'ok'})

async def get_messages(request):
    """Возвращает НОВЫЕ (непрочитанные) сообщения для пользователя и помечает их доставленными."""
    user = request.query.get('user')
    if not user:
        return web.json_response({'status': 'error', 'message': 'Missing user'}, status=400)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, from_user, content, timestamp FROM messages WHERE to_user=? AND delivered=0", (user,))
    rows = c.fetchall()
    ids = [row[0] for row in rows]
    if ids:
        placeholders = ','.join(['?'] * len(ids))
        c.execute(f"UPDATE messages SET delivered=1 WHERE id IN ({placeholders})", ids)
        conn.commit()
    conn.close()
    messages = [{'from': r[1], 'content': r[2], 'timestamp': r[3]} for r in rows]
    return web.json_response({'status': 'ok', 'messages': messages})

async def get_history(request):
    """Возвращает ВСЮ историю переписки между двумя пользователями."""
    user = request.query.get('user')
    contact = request.query.get('contact')
    if not user or not contact:
        return web.json_response({'status': 'error', 'message': 'Missing user or contact'}, status=400)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT from_user, content, timestamp 
        FROM messages 
        WHERE (from_user=? AND to_user=?) OR (from_user=? AND to_user=?)
        ORDER BY timestamp ASC
    ''', (user, contact, contact, user))
    rows = c.fetchall()
    conn.close()
    history = [{'from': r[0], 'content': r[1], 'timestamp': r[2]} for r in rows]
    return web.json_response({'status': 'ok', 'history': history})

async def get_users(request):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT login FROM users")
    rows = c.fetchall()
    conn.close()
    users = [r[0] for r in rows]
    return web.json_response({'status': 'ok', 'users': users})

async def index(request):
    with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'r', encoding='utf-8') as f:
        html = f.read()
    return web.Response(
        text=html,
        content_type='text/html',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
    )

# ----- CORS middleware -----
async def cors_middleware(app, handler):
    async def middleware(request):
        if request.method == 'OPTIONS':
            response = web.Response()
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            return response
        response = await handler(request)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    return middleware

# ----- Создаём приложение и добавляем роуты -----
app = web.Application()
app.middlewares.append(cors_middleware)

app.router.add_post('/register', register)
app.router.add_post('/login', login)
app.router.add_post('/upload', upload_file)
app.router.add_post('/send', send_message)
app.router.add_get('/messages', get_messages)
app.router.add_get('/history', get_history)
app.router.add_get('/users', get_users)
app.router.add_get('/', index)
app.router.add_static('/uploads', UPLOAD_DIR)  # для раздачи файлов

if __name__ == '__main__':
    init_db()
    print("Carrier Pigeon Server v3.1 (с файлами и PWA) запущен на 0.0.0.0:8080")
    print("Откройте в браузере: http://localhost:8080")
    web.run_app(app, host='0.0.0.0', port=8080)