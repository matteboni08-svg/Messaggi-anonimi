import os, secrets, sqlite3, random
from datetime import datetime, timezone
from flask import Flask, g, render_template, request, redirect, url_for, abort, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'app.db'))
SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

SCHEMA = '''
CREATE TABLE IF NOT EXISTS rooms (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  admin_token TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS participants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  room_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  message TEXT NOT NULL,
  token TEXT UNIQUE NOT NULL,
  assigned_from_id INTEGER,
  created_at TEXT NOT NULL,
  FOREIGN KEY(room_id) REFERENCES rooms(id),
  FOREIGN KEY(assigned_from_id) REFERENCES participants(id)
);
'''

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

@app.teardown_appcontext
def close_db(_error):
    conn = g.pop('db', None)
    if conn:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def make_code():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    for _ in range(50):
        code = ''.join(secrets.choice(alphabet) for _ in range(6))
        if not db().execute('SELECT 1 FROM rooms WHERE code=?', (code,)).fetchone():
            return code
    raise RuntimeError('Impossibile generare un codice stanza')


def room_by_code(code):
    return db().execute('SELECT * FROM rooms WHERE code=?', (code.upper(),)).fetchone()

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()[:80]
        if not title:
            flash('Inserisci un nome per il gruppo.')
            return redirect(url_for('home'))
        code = make_code()
        admin_token = secrets.token_urlsafe(24)
        db().execute(
            'INSERT INTO rooms(code,title,admin_token,status,created_at) VALUES(?,?,?,?,?)',
            (code, title, admin_token, 'open', now_iso())
        )
        db().commit()
        return redirect(url_for('admin_room', admin_token=admin_token))
    return render_template('home.html')

@app.route('/r/<code>', methods=['GET', 'POST'])
def join_room(code):
    room = room_by_code(code)
    if not room:
        abort(404)
    if request.method == 'POST':
        if room['status'] != 'open':
            flash('Il gruppo è già stato chiuso: non accetta più messaggi.')
            return redirect(url_for('join_room', code=code))
        name = request.form.get('name', '').strip()[:60]
        message = request.form.get('message', '').strip()[:2000]
        if not name or not message:
            flash('Inserisci sia il nome sia il messaggio.')
            return redirect(url_for('join_room', code=code))
        token = secrets.token_urlsafe(24)
        db().execute(
            'INSERT INTO participants(room_id,name,message,token,created_at) VALUES(?,?,?,?,?)',
            (room['id'], name, message, token, now_iso())
        )
        db().commit()
        return redirect(url_for('participant_page', token=token))
    return render_template('join.html', room=room)

@app.route('/p/<token>')
def participant_page(token):
    p = db().execute('''
        SELECT p.*, r.title, r.code, r.status
        FROM participants p JOIN rooms r ON r.id=p.room_id
        WHERE p.token=?
    ''', (token,)).fetchone()
    if not p:
        abort(404)
    assigned = None
    if p['status'] == 'drawn' and p['assigned_from_id']:
        assigned = db().execute(
            'SELECT message FROM participants WHERE id=?',
            (p['assigned_from_id'],)
        ).fetchone()
    return render_template('participant.html', p=p, assigned=assigned)

@app.route('/a/<admin_token>', methods=['GET', 'POST'])
def admin_room(admin_token):
    room = db().execute('SELECT * FROM rooms WHERE admin_token=?', (admin_token,)).fetchone()
    if not room:
        abort(404)

    if request.method == 'POST':
        action = request.form.get('action')
        participants = db().execute(
            'SELECT * FROM participants WHERE room_id=? ORDER BY id', (room['id'],)
        ).fetchall()

        if action == 'draw':
            if room['status'] != 'open':
                flash('Il sorteggio è già stato effettuato.')
            elif len(participants) < 2:
                flash('Servono almeno 2 partecipanti.')
            else:
                ids = [p['id'] for p in participants]
                shuffled = ids[:]
                # Generate a derangement (nobody receives their own message).
                for _ in range(10000):
                    random.SystemRandom().shuffle(shuffled)
                    if all(a != b for a, b in zip(ids, shuffled)):
                        break
                else:
                    flash('Non è stato possibile completare il sorteggio. Riprova.')
                    return redirect(url_for('admin_room', admin_token=admin_token))

                for recipient_id, sender_id in zip(ids, shuffled):
                    db().execute(
                        'UPDATE participants SET assigned_from_id=? WHERE id=?',
                        (sender_id, recipient_id)
                    )
                db().execute('UPDATE rooms SET status=? WHERE id=?', ('drawn', room['id']))
                db().commit()
                flash('Sorteggio completato. Ognuno può aprire il proprio link personale.')

        return redirect(url_for('admin_room', admin_token=admin_token))

    participants = db().execute(
        'SELECT id,name,token,created_at FROM participants WHERE room_id=? ORDER BY id',
        (room['id'],)
    ).fetchall()
    return render_template('admin.html', room=room, participants=participants)

@app.route('/health')
def health():
    return {'ok': True}

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))
else:
    init_db()
