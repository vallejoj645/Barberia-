from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')  # client/barber/admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    barber_profile = db.relationship('Barber', backref='user', uselist=False)
    appointments_as_client = db.relationship('Appointment', foreign_keys='Appointment.client_id', backref='client')
    loyalty_card = db.relationship('LoyaltyCard', backref='client', uselist=False)
    notifications = db.relationship('Notification', backref='user', order_by='Notification.created_at.desc()')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


class Barber(db.Model):
    __tablename__ = 'barbers'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    level = db.Column(db.String(20), nullable=False, default='Junior')  # Fundador/Senior/Junior
    years = db.Column(db.Integer, default=0)
    specialties = db.Column(db.String(255), default='')
    avatar_color = db.Column(db.String(20), default='#E8302A')
    rating = db.Column(db.Float, default=5.0)
    avatar_initials = db.Column(db.String(5), default='')

    # Relationships
    appointments = db.relationship('Appointment', foreign_keys='Appointment.barber_id', backref='barber')
    time_blocks = db.relationship('TimeBlock', backref='barber')

    @property
    def name(self):
        return self.user.name if self.user else ''

    def __repr__(self):
        return f'<Barber {self.name}>'


class Service(db.Model):
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    price = db.Column(db.Integer, nullable=False, default=0)
    description = db.Column(db.Text, default='')

    # Relationships
    appointments = db.relationship('Appointment', backref='service')

    def price_formatted(self):
        return f"${self.price:,}".replace(',', '.')

    def __repr__(self):
        return f'<Service {self.name}>'


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    barber_id = db.Column(db.Integer, db.ForeignKey('barbers.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(5), nullable=False)  # "HH:MM"
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending/confirmed/completed/cancelled
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Appointment {self.date} {self.time_slot}>'


class LoyaltyCard(db.Model):
    __tablename__ = 'loyalty_cards'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_cuts = db.Column(db.Integer, default=0)
    free_cuts_redeemed = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<LoyaltyCard client={self.client_id} cuts={self.total_cuts}>'


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Notification user={self.user_id}>'


class TimeBlock(db.Model):
    __tablename__ = 'time_blocks'
    id = db.Column(db.Integer, primary_key=True)
    barber_id = db.Column(db.Integer, db.ForeignKey('barbers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(5), nullable=False)  # "HH:MM"
    end_time = db.Column(db.String(5), nullable=False)    # "HH:MM"
    reason = db.Column(db.String(255), default='')

    def __repr__(self):
        return f'<TimeBlock barber={self.barber_id} {self.date} {self.start_time}-{self.end_time}>'
