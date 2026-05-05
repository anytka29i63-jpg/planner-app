from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Связующие таблицы "многие ко многим" для мероприятий
event_responsible = db.Table('event_responsible',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True)
)

event_controller = db.Table('event_controller',
    db.Column('event_id', db.Integer, db.ForeignKey('events.id'), primary_key=True),
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True)
)

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    participants_count = db.Column(db.Integer, default=0)
    participants_details = db.Column(db.Text, default='')
    status = db.Column(db.String(50), default='plan')
    color = db.Column(db.String(20), default='#ffffff')
    service = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    planned = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    responsible_employees = db.relationship('Employee', secondary=event_responsible, backref='responsible_events', lazy='joined')
    controller_employees = db.relationship('Employee', secondary=event_controller, backref='controller_events', lazy='joined')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'date': self.date,
            'time': self.time,
            'responsible': [emp.full_name for emp in self.responsible_employees],
            'controller': [emp.full_name for emp in self.controller_employees],
            'participants_count': self.participants_count,
            'participants_details': self.participants_details,
            'status': self.status,
            'color': self.color,
            'service': self.service,
            'category': self.category,
            'planned': self.planned
        }

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False, unique=True)
    position = db.Column(db.String(200), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'position': self.position,
            'department': self.department,
            'email': self.email,
            'phone': self.phone
        }

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(100), nullable=False, unique=True)
    full_name = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), default='staff')
    service_code = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'login': self.login,
            'full_name': self.full_name,
            'role': self.role,
            'service_code': self.service_code
        }

# ---------- Личные задачи (ежедневник) ----------
class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    icon = db.Column(db.String(50), default='bi bi-flag')
    status = db.Column(db.String(50), default='plan')
    created_date = db.Column(db.String(20), nullable=False)
    due_date = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'icon': self.icon,
            'status': self.status,
            'created_date': self.created_date,
            'due_date': self.due_date
        }

# ---------- Поручения ----------
class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    responsible_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    controller_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    created_date = db.Column(db.String(20), nullable=False)
    deadline = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(50), default='active')
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    author = db.relationship('User', foreign_keys=[author_id])
    responsible = db.relationship('Employee', foreign_keys=[responsible_id])
    controller = db.relationship('Employee', foreign_keys=[controller_id])
    
    def to_dict(self):
        return {
            'id': self.id,
            'author_id': self.author_id,
            'author_name': self.author.full_name if self.author else '',
            'responsible_id': self.responsible_id,
            'responsible_name': self.responsible.full_name if self.responsible else '',
            'controller_id': self.controller_id,
            'controller_name': self.controller.full_name if self.controller else '',
            'title': self.title,
            'description': self.description,
            'created_date': self.created_date,
            'deadline': self.deadline,
            'status': self.status,
            'is_completed': self.is_completed,
            'completed_at': self.completed_at
        }