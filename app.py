from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from models import db, Event, Employee, User, Task, Assignment
import pandas as pd
from datetime import datetime, timedelta
from functools import wraps
import io
import os
import sys
import re

app = Flask(__name__)

# ---------- Функция для экранирования спецсимволов в пароле ----------
def escape_url_password(url):
    """Заменяет спецсимволы в пароле на их URL-коды, например ! → %21"""
    if not url:
        return url
    # Ищем пароль между :// и @
    match = re.search(r'://([^:]+):([^@]+)@', url)
    if match:
        user = match.group(1)
        password = match.group(2)
        # URL-кодируем пароль (кроме уже закодированных %)
        encoded_password = ''
        for ch in password:
            if ch == '%':
                encoded_password += ch
            elif ch in '!@#$%^&*()[]{}|;:,<>/?`~ ':
                encoded_password += f'%{ord(ch):02X}'
            else:
                encoded_password += ch
        # Собираем строку заново
        return re.sub(r'://[^:]+:[^@]+@', f'://{user}:{encoded_password}@', url)
    return url

# ---------- Настройка базы данных и секретного ключа ----------
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Для совместимости со старыми форматами заменяем postgres:// → postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    # Экранируем спецсимволы в пароле
    database_url = escape_url_password(database_url)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    print(f"Подключение к PostgreSQL: {database_url[:30]}... (пароль скрыт)", file=sys.stderr)
else:
    # Локальная разработка – SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///planner.db'
    print("Используется SQLite", file=sys.stderr)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey-change-this-in-production')

db.init_app(app)

# ---------- Декораторы ----------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            return jsonify({'error': 'Доступ запрещён'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ---------- Контекстный процессор ----------
@app.context_processor
def inject_user():
    return {
        'user_role': session.get('user_role', ''),
        'user_full_name': session.get('user_full_name', '')
    }

# ---------- Инициализация БД и демо-данных ----------
with app.app_context():
    db.create_all()
    if Employee.query.count() == 0:
        sample_employees = [
            Employee(full_name='Иванов Иван Иванович', position='Зам. директора по УР', department='academic'),
            Employee(full_name='Петрова Анна Сергеевна', position='Методист', department='methodical'),
            Employee(full_name='Сидоров Дмитрий Петрович', position='Социальный педагог', department='social-ped'),
            Employee(full_name='Кузнецова Мария Ивановна', position='Руководитель БАС-центра', department='bas'),
            Employee(full_name='Ляпнева Наталья Михайловна', position='Старший методист', department='methodical'),
            Employee(full_name='Губарь Анна Сергеевна', position='Заместитель директора по ОР', department='organizational'),
            Employee(full_name='Кирсанова Татьяна Николаевна', position='Секретарь учебной части', department='organizational'),
            Employee(full_name='Зуева Анна Александровна', position='Руководитель ИКТ', department='ict'),
        ]
        for e in sample_employees:
            db.session.add(e)
        db.session.commit()
    
    if User.query.count() == 0:
        admin = User(login='admin', full_name='Администратор', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        ict_head = User(login='zueva', full_name='Зуева Анна Александровна', role='head', service_code='ict')
        ict_head.set_password('zueva123')
        db.session.add(ict_head)
        db.session.commit()
    
    if Event.query.count() == 0:
        today_str = datetime.now().strftime('%Y-%m-%d')
        sample_event = Event(
            title='День знаний',
            description='Торжественная линейка',
            date=today_str,
            time='10:00',
            participants_count=250,
            participants_details='Все группы 1-2 курсов',
            status='today',
            color='#e3f2fd',
            service='general',
            category='general',
            planned=True
        )
        ivanov = Employee.query.filter_by(full_name='Иванов Иван Иванович').first()
        if ivanov:
            sample_event.responsible_employees.append(ivanov)
        db.session.add(sample_event)
        db.session.commit()
        print("Демо-данные созданы", file=sys.stderr)

# ---------- Маршруты ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = User.query.filter_by(login=login, is_active=True).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_full_name'] = user.full_name
            session['user_role'] = user.role
            session['user_service_code'] = user.service_code
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user_id=session['user_id'])

@app.route('/all-events')
@login_required
def all_events():
    return render_template('all_events.html')

@app.route('/reports')
@login_required
def reports_page():
    return render_template('reports.html')

# ---------- API для мероприятий ----------
@app.route('/api/events')
@login_required
def get_events():
    filter_by = request.args.get('filter_by')
    value = request.args.get('value')
    if filter_by == 'category':
        events = Event.query.filter_by(category=value).order_by(Event.date, Event.time).all()
    elif filter_by == 'service':
        events = Event.query.filter_by(service=value).order_by(Event.date, Event.time).all()
    else:
        events = Event.query.all()
    return jsonify([e.to_dict() for e in events])

@app.route('/api/events/current-month')
@login_required
def get_current_month_events():
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    events = Event.query.all()
    filtered = []
    for ev in events:
        try:
            ev_date = datetime.strptime(ev.date, '%Y-%m-%d')
            if ev_date.month == current_month and ev_date.year == current_year:
                filtered.append(ev)
        except:
            pass
    return jsonify([e.to_dict() for e in filtered])

@app.route('/api/events/range')
@login_required
def get_events_by_range():
    range_type = request.args.get('range', 'today')
    today = datetime.now().date()
    if range_type == 'today':
        events = Event.query.filter(Event.date == today.strftime('%Y-%m-%d')).order_by(Event.time).all()
    else:
        current_month = today.month
        current_year = today.year
        events = Event.query.all()
        filtered = []
        for ev in events:
            try:
                ev_date = datetime.strptime(ev.date, '%Y-%m-%d').date()
                if ev_date.month == current_month and ev_date.year == current_year:
                    filtered.append(ev)
            except:
                pass
        events = filtered
    return jsonify([e.to_dict() for e in events])

@app.route('/api/event', methods=['POST'])
@login_required
def add_event():
    data = request.json
    planned = data.get('planned', True)
    event = Event(
        title=data['title'],
        description=data.get('description', ''),
        date=data['date'],
        time=data['time'],
        participants_count=int(data.get('participants_count', 0)),
        participants_details=data.get('participants_details', ''),
        status=data.get('status', 'plan'),
        color=data.get('color', '#ffffff'),
        service=data['service'],
        category=data['category'],
        planned=planned
    )
    responsible_ids = data.get('responsible_ids', [])
    for emp_id in responsible_ids:
        emp = Employee.query.get(emp_id)
        if emp:
            event.responsible_employees.append(emp)
    controller_ids = data.get('controller_ids', [])
    for emp_id in controller_ids:
        emp = Employee.query.get(emp_id)
        if emp:
            event.controller_employees.append(emp)
    db.session.add(event)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': event.id})

@app.route('/api/event/<int:id>', methods=['PUT'])
@login_required
def update_event(id):
    event = Event.query.get_or_404(id)
    data = request.json
    event.title = data.get('title', event.title)
    event.description = data.get('description', event.description)
    event.date = data.get('date', event.date)
    event.time = data.get('time', event.time)
    event.participants_count = int(data.get('participants_count', event.participants_count))
    event.participants_details = data.get('participants_details', event.participants_details)
    event.status = data.get('status', event.status)
    event.color = data.get('color', event.color)
    if 'service' in data:
        event.service = data['service']
    if 'category' in data:
        event.category = data['category']
    event.planned = data.get('planned', event.planned)
    responsible_ids = data.get('responsible_ids', [])
    event.responsible_employees = [Employee.query.get(emp_id) for emp_id in responsible_ids if Employee.query.get(emp_id)]
    controller_ids = data.get('controller_ids', [])
    event.controller_employees = [Employee.query.get(emp_id) for emp_id in controller_ids if Employee.query.get(emp_id)]
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/event/<int:id>', methods=['DELETE'])
@login_required
def delete_event(id):
    event = Event.query.get_or_404(id)
    db.session.delete(event)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/import', methods=['POST'])
@login_required
def import_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Пустой файл'}), 400
    try:
        df = pd.read_csv(file)
        required_cols = ['title', 'date', 'time', 'responsible', 'controller', 
                         'participants_count', 'participants_details', 'status', 'service', 'category']
        for col in required_cols:
            if col not in df.columns:
                return jsonify({'error': f'В CSV отсутствует колонка {col}'}), 400
        added = 0
        for _, row in df.iterrows():
            if pd.isna(row['title']):
                continue
            event = Event(
                title=str(row['title']),
                description=str(row.get('description', '')),
                date=str(row['date']),
                time=str(row['time']),
                participants_count=int(row['participants_count']) if pd.notna(row['participants_count']) else 0,
                participants_details=str(row.get('participants_details', '')),
                status=str(row['status']),
                service=str(row['service']),
                category=str(row['category']),
                planned=True
            )
            responsible_names = [name.strip() for name in str(row['responsible']).split(',') if name.strip()]
            for name in responsible_names:
                emp = Employee.query.filter_by(full_name=name).first()
                if not emp:
                    emp = Employee(full_name=name, position='', department='')
                    db.session.add(emp)
                    db.session.flush()
                event.responsible_employees.append(emp)
            controller_names = [name.strip() for name in str(row['controller']).split(',') if name.strip()]
            for name in controller_names:
                emp = Employee.query.filter_by(full_name=name).first()
                if not emp:
                    emp = Employee(full_name=name, position='', department='')
                    db.session.add(emp)
                    db.session.flush()
                event.controller_employees.append(emp)
            db.session.add(event)
            added += 1
        db.session.commit()
        return jsonify({'status': 'ok', 'added': added})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ---------- API для сотрудников ----------
@app.route('/api/employees')
@login_required
def get_employees():
    employees = Employee.query.order_by(Employee.full_name).all()
    return jsonify([e.to_dict() for e in employees])

@app.route('/api/employee', methods=['POST'])
@login_required
def add_employee():
    data = request.json
    if not data.get('full_name'):
        return jsonify({'error': 'Не указано ФИО'}), 400
    existing = Employee.query.filter_by(full_name=data['full_name']).first()
    if existing:
        return jsonify({'error': 'Сотрудник с таким ФИО уже существует'}), 400
    emp = Employee(
        full_name=data['full_name'],
        position=data.get('position', ''),
        department=data.get('department', ''),
        email=data.get('email', ''),
        phone=data.get('phone', '')
    )
    db.session.add(emp)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': emp.id})

@app.route('/api/employee/<int:id>', methods=['PUT'])
@login_required
def update_employee(id):
    emp = Employee.query.get_or_404(id)
    data = request.json
    emp.full_name = data.get('full_name', emp.full_name)
    emp.position = data.get('position', emp.position)
    emp.department = data.get('department', emp.department)
    emp.email = data.get('email', emp.email)
    emp.phone = data.get('phone', emp.phone)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/employee/<int:id>', methods=['DELETE'])
@login_required
def delete_employee(id):
    emp = Employee.query.get_or_404(id)
    db.session.delete(emp)
    db.session.commit()
    return jsonify({'status': 'ok'})

# ---------- Импорт для администратора ----------
@app.route('/api/import-employees', methods=['POST'])
@login_required
@admin_required
def import_employees():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Пустой файл'}), 400
    try:
        content = file.stream.read()
        import io
        try:
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        except:
            df = pd.read_csv(io.BytesIO(content), encoding='cp1251')
        if 'full_name' not in df.columns:
            return jsonify({'error': f'CSV должен содержать колонку full_name. Доступные: {", ".join(df.columns)}'}), 400
        added = 0
        skipped = 0
        for _, row in df.iterrows():
            full_name = str(row['full_name']).strip()
            if not full_name or pd.isna(row['full_name']):
                continue
            existing = Employee.query.filter_by(full_name=full_name).first()
            if existing:
                skipped += 1
                continue
            emp = Employee(
                full_name=full_name,
                position=str(row.get('position', '')) if pd.notna(row.get('position')) else '',
                department=str(row.get('department', '')) if pd.notna(row.get('department')) else '',
                email=str(row.get('email', '')) if pd.notna(row.get('email')) else '',
                phone=str(row.get('phone', '')) if pd.notna(row.get('phone')) else ''
            )
            db.session.add(emp)
            added += 1
        db.session.commit()
        return jsonify({'status': 'ok', 'added': added, 'skipped': skipped})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/import-users', methods=['POST'])
@login_required
@admin_required
def import_users():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не загружен'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Пустой файл'}), 400
    try:
        content = file.stream.read()
        import io
        try:
            df = pd.read_csv(io.BytesIO(content), encoding='utf-8')
        except:
            df = pd.read_csv(io.BytesIO(content), encoding='cp1251')
        required_cols = ['login', 'full_name', 'role', 'service_code', 'password']
        for col in required_cols:
            if col not in df.columns:
                return jsonify({'error': f'CSV должен содержать колонку {col}. Доступные: {", ".join(df.columns)}'}), 400
        added = 0
        skipped = 0
        for _, row in df.iterrows():
            login = str(row['login']).strip()
            full_name = str(row['full_name']).strip()
            password = str(row['password']).strip()
            if not login or not full_name or not password:
                continue
            existing = User.query.filter_by(login=login).first()
            if existing:
                skipped += 1
                continue
            user = User(
                login=login,
                full_name=full_name,
                role=str(row.get('role', 'staff')).strip(),
                service_code=str(row.get('service_code', '')).strip() if pd.notna(row.get('service_code')) else None,
                is_active=True
            )
            user.set_password(password)
            db.session.add(user)
            added += 1
        db.session.commit()
        return jsonify({'status': 'ok', 'added': added, 'skipped': skipped})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ---------- Управление пользователями (только администратор) ----------
@app.route('/api/admin/users')
@login_required
@admin_required
def admin_get_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])

@app.route('/api/admin/user', methods=['POST'])
@login_required
@admin_required
def admin_add_user():
    data = request.json
    if not data.get('login') or not data.get('full_name') or not data.get('password'):
        return jsonify({'error': 'Логин, ФИО и пароль обязательны'}), 400
    existing = User.query.filter_by(login=data['login']).first()
    if existing:
        return jsonify({'error': 'Пользователь с таким логином уже существует'}), 400
    user = User(
        login=data['login'],
        full_name=data['full_name'],
        role=data.get('role', 'staff'),
        service_code=data.get('service_code', '') or None,
        is_active=True
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': user.id})

@app.route('/api/admin/user/<int:id>', methods=['PUT'])
@login_required
@admin_required
def admin_update_user(id):
    user = User.query.get_or_404(id)
    data = request.json
    user.login = data.get('login', user.login)
    user.full_name = data.get('full_name', user.full_name)
    user.role = data.get('role', user.role)
    user.service_code = data.get('service_code', user.service_code) or None
    if 'password' in data and data['password']:
        user.set_password(data['password'])
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/admin/user/<int:id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_user(id):
    if id == session['user_id']:
        return jsonify({'error': 'Нельзя удалить самого себя'}), 400
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'ok'})

# ---------- Дашборд пользователя ----------
@app.route('/api/user/dashboard')
@login_required
def user_dashboard():
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
    
    if 'date' in request.args:
        target_date = request.args.get('date')
        start_str = target_date
        end_str = target_date
    else:
        period = request.args.get('period', 'today')
        today = datetime.now().date()
        if period == 'today':
            start_date = today
            end_date = today
        elif period == 'month':
            start_date = today.replace(day=1)
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        else:  # year
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
    
    service_events = []
    if user.service_code and user.service_code.strip():
        service_events = Event.query.filter(
            Event.service == user.service_code,
            Event.date >= start_str,
            Event.date <= end_str
        ).order_by(Event.date, Event.time).all()
    
    all_events = Event.query.filter(
        Event.date >= start_str,
        Event.date <= end_str
    ).order_by(Event.date, Event.time).all()
    
    responsible_events = []
    controller_events = []
    for ev in all_events:
        resp_list = ev.to_dict().get('responsible', [])
        contr_list = ev.to_dict().get('controller', [])
        if user.full_name in resp_list:
            responsible_events.append(ev)
        if user.full_name in contr_list:
            controller_events.append(ev)
    
    return jsonify({
        'user': user.to_dict(),
        'service_events': [e.to_dict() for e in service_events],
        'responsible_events': [e.to_dict() for e in responsible_events],
        'controller_events': [e.to_dict() for e in controller_events]
    })

# ---------- API для задач (личный ежедневник) ----------
@app.route('/api/tasks')
@login_required
def get_tasks():
    tasks = Task.query.filter_by(user_id=session['user_id']).order_by(Task.created_date.desc()).all()
    return jsonify([t.to_dict() for t in tasks])

@app.route('/api/task', methods=['POST'])
@login_required
def add_task():
    data = request.json
    task = Task(
        user_id=session['user_id'],
        title=data['title'],
        description=data.get('description', ''),
        icon=data.get('icon', 'bi bi-flag'),
        status=data.get('status', 'plan'),
        created_date=data.get('created_date', datetime.now().strftime('%Y-%m-%d')),
        due_date=data.get('due_date', '')
    )
    db.session.add(task)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': task.id})

@app.route('/api/task/<int:id>', methods=['PUT'])
@login_required
def update_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != session['user_id']:
        return jsonify({'error': 'Доступ запрещён'}), 403
    data = request.json
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.icon = data.get('icon', task.icon)
    task.status = data.get('status', task.status)
    task.due_date = data.get('due_date', task.due_date)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/task/<int:id>', methods=['DELETE'])
@login_required
def delete_task(id):
    task = Task.query.get_or_404(id)
    if task.user_id != session['user_id']:
        return jsonify({'error': 'Доступ запрещён'}), 403
    db.session.delete(task)
    db.session.commit()
    return jsonify({'status': 'ok'})

# ---------- API для поручений ----------
@app.route('/api/assignments')
@login_required
def get_assignments():
    user_id = session['user_id']
    assignments = Assignment.query.filter(
        (Assignment.author_id == user_id) |
        (Assignment.responsible_id == user_id) |
        (Assignment.controller_id == user_id)
    ).order_by(Assignment.deadline).all()
    return jsonify([a.to_dict() for a in assignments])

@app.route('/api/assignment', methods=['POST'])
@login_required
def add_assignment():
    data = request.json
    assignment = Assignment(
        author_id=session['user_id'],
        responsible_id=data['responsible_id'],
        controller_id=data.get('controller_id'),
        title=data['title'],
        description=data.get('description', ''),
        created_date=datetime.now().strftime('%Y-%m-%d'),
        deadline=data['deadline'],
        status='active',
        is_completed=False
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': assignment.id})

@app.route('/api/assignment/<int:id>', methods=['PUT'])
@login_required
def update_assignment(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.author_id != session['user_id']:
        return jsonify({'error': 'Доступ запрещён'}), 403
    data = request.json
    assignment.title = data.get('title', assignment.title)
    assignment.description = data.get('description', assignment.description)
    assignment.responsible_id = data.get('responsible_id', assignment.responsible_id)
    assignment.controller_id = data.get('controller_id', assignment.controller_id)
    assignment.deadline = data.get('deadline', assignment.deadline)
    if 'is_completed' in data:
        assignment.is_completed = data['is_completed']
        assignment.status = 'completed' if data['is_completed'] else 'active'
        if data['is_completed']:
            assignment.completed_at = datetime.now().strftime('%Y-%m-%d')
        else:
            assignment.completed_at = None
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/assignment/<int:id>', methods=['DELETE'])
@login_required
def delete_assignment(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.author_id != session['user_id']:
        return jsonify({'error': 'Доступ запрещён'}), 403
    db.session.delete(assignment)
    db.session.commit()
    return jsonify({'status': 'ok'})

# ---------- Отчёты (мероприятия) ----------
@app.route('/api/reports', methods=['POST'])
@login_required
def run_report():
    data = request.json
    report_type = data.get('report_type')
    filters = data.get('filters', {})
    query = Event.query
    
    if report_type == 'status' and filters.get('status'):
        query = query.filter(Event.status == filters['status'])
    elif report_type == 'responsible' and filters.get('responsible'):
        query = query.filter(Event.responsible_employees.any(full_name=filters['responsible']))
    elif report_type == 'controller' and filters.get('controller'):
        query = query.filter(Event.controller_employees.any(full_name=filters['controller']))
    elif report_type == 'date_interval':
        if filters.get('date_from'):
            query = query.filter(Event.date >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(Event.date <= filters['date_to'])
    elif report_type == 'category' and filters.get('category'):
        query = query.filter(Event.category == filters['category'])
    elif report_type == 'service' and filters.get('service'):
        query = query.filter(Event.service == filters['service'])
    elif report_type == 'custom':
        if filters.get('title'):
            query = query.filter(Event.title.contains(filters['title']))
        if filters.get('date_from'):
            query = query.filter(Event.date >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(Event.date <= filters['date_to'])
        if filters.get('status'):
            query = query.filter(Event.status == filters['status'])
        if filters.get('responsible'):
            query = query.filter(Event.responsible_employees.any(full_name=filters['responsible']))
        if filters.get('controller'):
            query = query.filter(Event.controller_employees.any(full_name=filters['controller']))
        if filters.get('category'):
            query = query.filter(Event.category == filters['category'])
    events = query.order_by(Event.date, Event.time).all()
    return jsonify([e.to_dict() for e in events])

@app.route('/api/reports/export', methods=['POST'])
@login_required
def export_report():
    data = request.json
    report_type = data.get('report_type')
    filters = data.get('filters', {})
    query = Event.query
    
    if report_type == 'status' and filters.get('status'):
        query = query.filter(Event.status == filters['status'])
    elif report_type == 'responsible' and filters.get('responsible'):
        query = query.filter(Event.responsible_employees.any(full_name=filters['responsible']))
    elif report_type == 'controller' and filters.get('controller'):
        query = query.filter(Event.controller_employees.any(full_name=filters['controller']))
    elif report_type == 'date_interval':
        if filters.get('date_from'):
            query = query.filter(Event.date >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(Event.date <= filters['date_to'])
    elif report_type == 'category' and filters.get('category'):
        query = query.filter(Event.category == filters['category'])
    elif report_type == 'service' and filters.get('service'):
        query = query.filter(Event.service == filters['service'])
    elif report_type == 'custom':
        if filters.get('title'):
            query = query.filter(Event.title.contains(filters['title']))
        if filters.get('date_from'):
            query = query.filter(Event.date >= filters['date_from'])
        if filters.get('date_to'):
            query = query.filter(Event.date <= filters['date_to'])
        if filters.get('status'):
            query = query.filter(Event.status == filters['status'])
        if filters.get('responsible'):
            query = query.filter(Event.responsible_employees.any(full_name=filters['responsible']))
        if filters.get('controller'):
            query = query.filter(Event.controller_employees.any(full_name=filters['controller']))
        if filters.get('category'):
            query = query.filter(Event.category == filters['category'])
    events = query.order_by(Event.date, Event.time).all()
    
    service_names = {
        'general': 'Общетехникумовская', 'career': 'Профориентация', 'admin': 'Административно-хозяйственная',
        'social-ped': 'Социально-педагогическая', 'methodical': 'Учебно-методический отдел', 'bas': 'БАС-центр',
        'external': 'Внешние мероприятия', 'council': 'Совет руководства', 'ict': 'Отдел ИКТ',
        'academic': 'Учебная служба', 'physical': 'Физическая культура', 'organizational': 'Организационная работа'
    }
    category_names = {
        'general': 'Общетехникумовские', 'career': 'Профориентация', 'external': 'Внешние мероприятия',
        'research': 'НИС / Конкурсы / Олимпиады'
    }
    status_names = {
        'plan': 'Запланировано', 'done': 'Завершено', 'postponed': 'Перенесено',
        'today': 'Сегодня', 'cancelled': 'Отменено'
    }
    data_rows = []
    for ev in events:
        row = {
            'ID': ev.id,
            'Название': ev.title,
            'Дата': ev.date,
            'Время': ev.time,
            'Ответственные': ', '.join([emp.full_name for emp in ev.responsible_employees]),
            'Контролирующие': ', '.join([emp.full_name for emp in ev.controller_employees]),
            'Статус': status_names.get(ev.status, ev.status),
            'Служба': service_names.get(ev.service, ev.service),
            'Категория': category_names.get(ev.category, ev.category),
            'Кол-во участников': ev.participants_count,
            'Участники (детали)': ev.participants_details,
            'Плановость': 'Плановое' if ev.planned else 'Внеплановое'
        }
        data_rows.append(row)
    
    df = pd.DataFrame(data_rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Отчёт', index=False)
    output.seek(0)
    return send_file(output, download_name='report.xlsx', as_attachment=True)

# ---------- Отчёты по поручениям ----------
@app.route('/api/assignments-report', methods=['POST'])
@login_required
def assignments_report():
    data = request.json
    status_filter = data.get('status', 'all')
    responsible_filter = data.get('responsible_id')
    deadline_from = data.get('deadline_from')
    deadline_to = data.get('deadline_to')
    
    query = Assignment.query
    if status_filter != 'all':
        if status_filter == 'completed':
            query = query.filter_by(is_completed=True)
        elif status_filter == 'active':
            query = query.filter_by(is_completed=False)
    if responsible_filter:
        query = query.filter_by(responsible_id=responsible_filter)
    if deadline_from:
        query = query.filter(Assignment.deadline >= deadline_from)
    if deadline_to:
        query = query.filter(Assignment.deadline <= deadline_to)
    
    assignments = query.order_by(Assignment.deadline).all()
    return jsonify([a.to_dict() for a in assignments])

@app.route('/api/assignments-report/export', methods=['POST'])
@login_required
def export_assignments_report():
    data = request.json
    status_filter = data.get('status', 'all')
    responsible_filter = data.get('responsible_id')
    deadline_from = data.get('deadline_from')
    deadline_to = data.get('deadline_to')
    
    query = Assignment.query
    if status_filter != 'all':
        if status_filter == 'completed':
            query = query.filter_by(is_completed=True)
        elif status_filter == 'active':
            query = query.filter_by(is_completed=False)
    if responsible_filter:
        query = query.filter_by(responsible_id=responsible_filter)
    if deadline_from:
        query = query.filter(Assignment.deadline >= deadline_from)
    if deadline_to:
        query = query.filter(Assignment.deadline <= deadline_to)
    
    assignments = query.order_by(Assignment.deadline).all()
    data_rows = []
    for a in assignments:
        row = {
            'ID': a.id,
            'Поручение': a.title,
            'Ответственный': a.responsible.full_name if a.responsible else '',
            'Контролирующий': a.controller.full_name if a.controller else '',
            'Создано': a.created_date,
            'Срок': a.deadline,
            'Статус': 'Выполнено' if a.is_completed else 'Активно',
            'Дата выполнения': a.completed_at or ''
        }
        data_rows.append(row)
    df = pd.DataFrame(data_rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Поручения', index=False)
    output.seek(0)
    return send_file(output, download_name='assignments_report.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
