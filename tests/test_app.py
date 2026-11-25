import os
import tempfile
from pathlib import Path

os.environ['DATABASE_PATH'] = str(Path(tempfile.gettempdir()) / 'search_ai_pro_test_suite.db')
os.environ['FLASK_SECRET_KEY'] = 'test-only-secret'
from app import app, init_db  # noqa: E402


def test_login_required():
    with app.test_client() as c:
        assert c.get('/api/chats').status_code == 401


def test_register_settings_and_private_chats():
    init_db()
    with app.test_client() as c:
        c.get('/')
        with c.session_transaction() as s:
            token = s['csrf']
        email = 'test-' + os.urandom(6).hex() + '@example.com'
        r = c.post('/api/register', json={'email': email, 'password': 'strong-password-123'}, headers={'X-CSRF-Token': token})
        assert r.status_code == 201
        assert c.get('/api/me').json['authenticated']
        r = c.post('/api/chats', json={}, headers={'X-CSRF-Token': token})
        assert r.status_code == 201
        chat_id = r.json['id']
        assert c.get('/api/chats/' + str(chat_id)).status_code == 200
        assert c.patch('/api/chats/' + str(chat_id), json={'title': 'Renamed'}, headers={'X-CSRF-Token': token}).status_code == 200
        assert c.get('/api/chats?q=Renamed').json[0]['title'] == 'Renamed'
        assert c.get('/api/usage').status_code == 200
        assert c.get('/api/admin/stats').status_code == 403
        assert c.get('/api/chats/' + str(chat_id) + '/export.pdf').status_code == 200
        assert c.post('/api/logout', headers={'X-CSRF-Token': token}).status_code == 200
        assert c.get('/api/chats/' + str(chat_id)).status_code == 401
