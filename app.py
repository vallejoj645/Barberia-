from flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hashfrom flask import Flask, render_template, redirect, url_for, request, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-barberia-2026')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///barberia.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Fix postgres:// -> postgresql://
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

from models import db, User, Barber, Service, Appointment, LoyaltyCard, Notification, TimeBlock

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor iniciá sesión para continuar.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---- Context Processors ----

@app.context_processor
def inject_now():
    now = datetime.now()
    days_es = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
    months_es = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
    day_name = days_es[now.weekday()]
    month_name = months_es[now.month - 1]
    date_str = f"{day_name} {now.day} {month_name} · {now.strftime('%H:%M')}"
    return dict(now=now, now_date_str=date_str)

@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, read=False).count()
        return dict(unread_notifications=unread_count)
    return dict(unread_notifications=0)


# ---- Helpers ----

def barber_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if current_user.role not in ('barber', 'admin'):
            flash('Acceso restringido a barberos.', 'error')
            return redirect(url_for('client_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def format_price(amount):
    return f"${amount:,}".replace(',', '.')


def get_week_dates(reference_date=None):
    """Returns list of dates for the week (Mon-Sun) containing reference_date."""
    if reference_date is None:
        reference_date = date.today()
    start = reference_date - timedelta(days=reference_date.weekday())
    return [start + timedelta(days=i) for i in range(7)]


def get_available_slots(barber_id, target_date):
    """Returns list of available HH:MM time slots for a barber on a given date."""
    # Working hours 09:00-20:00, slots every 30 min
    all_slots = []
    start_h, start_m = 9, 0
    end_h, end_m = 20, 0
    current_h, current_m = start_h, start_m
    while (current_h, current_m) < (end_h, end_m):
        all_slots.append(f"{current_h:02d}:{current_m:02d}")
        current_m += 30
        if current_m >= 60:
            current_m = 0
            current_h += 1

    # Get booked slots
    booked = Appointment.query.filter_by(
        barber_id=barber_id,
        date=target_date
    ).filter(Appointment.status.in_(['pending', 'confirmed'])).all()
    booked_times = set()
    for appt in booked:
        booked_times.add(appt.time_slot)
        # Also block slot based on service duration
        h, m = int(appt.time_slot[:2]), int(appt.time_slot[3:])
        duration = appt.service.duration_minutes if appt.service else 30
        total_minutes = h * 60 + m
        for offset in range(30, duration, 30):
            blocked_total = total_minutes + offset
            bh, bm = divmod(blocked_total, 60)
            booked_times.add(f"{bh:02d}:{bm:02d}")

    # Get time blocks
    blocks = TimeBlock.query.filter_by(barber_id=barber_id, date=target_date).all()
    for block in blocks:
        sh, sm = int(block.start_time[:2]), int(block.start_time[3:])
        eh, em = int(block.end_time[:2]), int(block.end_time[3:])
        start_total = sh * 60 + sm
        end_total = eh * 60 + em
        slot_time = start_total
        while slot_time < end_total:
            sh2, sm2 = divmod(slot_time, 60)
            booked_times.add(f"{sh2:02d}:{sm2:02d}")
            slot_time += 30

    available = [s for s in all_slots if s not in booked_times]
    return available


MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
              'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
MONTHS_ES_UPPER = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC']
DAYS_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
DAYS_ES_SHORT = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def format_date_es(d):
    """Returns e.g. 'Mar 28 ABR · 2026'"""
    day_name = DAYS_ES_SHORT[d.weekday()]
    month = MONTHS_ES_UPPER[d.month - 1]
    return f"{day_name} {d.day} {month} · {d.year}"


app.jinja_env.globals['format_date_es'] = format_date_es
app.jinja_env.globals['format_price'] = format_price


# ---- Auth Routes ----

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role in ('barber', 'admin'):
            return redirect(url_for('barber_agenda'))
        return redirect(url_for('client_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role in ('barber', 'admin'):
                return redirect(url_for('barber_agenda'))
            return redirect(url_for('client_dashboard'))
        flash('Email o contraseña incorrectos.', 'error')
    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ---- Client Routes ----

@app.route('/client/')
@login_required
def client_dashboard():
    today = date.today()
    # Next upcoming appointment
    next_appt = Appointment.query.filter(
        Appointment.client_id == current_user.id,
        Appointment.date >= today,
        Appointment.status.in_(['pending', 'confirmed'])
    ).order_by(Appointment.date, Appointment.time_slot).first()

    # Loyalty card
    loyalty = LoyaltyCard.query.filter_by(client_id=current_user.id).first()

    # Regular barber (most visited)
    from sqlalchemy import func
    regular_barber_result = db.session.query(
        Appointment.barber_id,
        func.count(Appointment.id).label('visit_count')
    ).filter(
        Appointment.client_id == current_user.id,
        Appointment.status == 'completed'
    ).group_by(Appointment.barber_id).order_by(func.count(Appointment.id).desc()).first()

    regular_barber = None
    visit_count = 0
    if regular_barber_result:
        regular_barber = Barber.query.get(regular_barber_result.barber_id)
        visit_count = regular_barber_result.visit_count
    else:
        # If no completed appointments, try the next appointment's barber
        if next_appt:
            regular_barber = next_appt.barber
            visit_count = 1

    # Recent history
    recent_history = Appointment.query.filter(
        Appointment.client_id == current_user.id,
        Appointment.status == 'completed'
    ).order_by(Appointment.date.desc(), Appointment.time_slot.desc()).limit(5).all()

    return render_template('client/dashboard.html',
                           next_appt=next_appt,
                           loyalty=loyalty,
                           regular_barber=regular_barber,
                           visit_count=visit_count,
                           recent_history=recent_history,
                           today=today,
                           MONTHS_ES_UPPER=MONTHS_ES_UPPER,
                           DAYS_ES_SHORT=DAYS_ES_SHORT)


@app.route('/client/book', methods=['GET', 'POST'])
@login_required
def client_book():
    barbers = Barber.query.join(User).all()
    services = Service.query.all()
    step = request.args.get('step', '1')

    if request.method == 'POST':
        # Create the appointment
        barber_id = request.form.get('barber_id')
        service_id = request.form.get('service_id')
        appt_date_str = request.form.get('date')
        time_slot = request.form.get('time_slot')
        notes = request.form.get('notes', '')

        try:
            appt_date = datetime.strptime(appt_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Fecha inválida.', 'error')
            return redirect(url_for('client_book'))

        # Validate slot availability
        available = get_available_slots(int(barber_id), appt_date)
        if time_slot not in available:
            flash('El turno seleccionado ya no está disponible. Por favor elegí otro.', 'error')
            return redirect(url_for('client_book'))

        appt = Appointment(
            client_id=current_user.id,
            barber_id=int(barber_id),
            service_id=int(service_id),
            date=appt_date,
            time_slot=time_slot,
            status='confirmed',
            notes=notes
        )
        db.session.add(appt)

        # Update loyalty card
        loyalty = LoyaltyCard.query.filter_by(client_id=current_user.id).first()
        if not loyalty:
            loyalty = LoyaltyCard(client_id=current_user.id, total_cuts=0, free_cuts_redeemed=0)
            db.session.add(loyalty)

        # Add notification
        barber = Barber.query.get(int(barber_id))
        service = Service.query.get(int(service_id))
        notif = Notification(
            user_id=current_user.id,
            message=f"Tu turno con {barber.name} para {service.name} el {appt_date.strftime('%d/%m/%Y')} a las {time_slot} fue confirmado."
        )
        db.session.add(notif)
        db.session.commit()

        flash('¡Turno reservado con éxito!', 'success')
        return redirect(url_for('client_appointments'))

    return render_template('client/book.html',
                           barbers=barbers,
                           services=services,
                           step=step,
                           today=date.today())


@app.route('/client/appointments')
@login_required
def client_appointments():
    today = date.today()
    upcoming = Appointment.query.filter(
        Appointment.client_id == current_user.id,
        Appointment.date >= today,
        Appointment.status.in_(['pending', 'confirmed'])
    ).order_by(Appointment.date, Appointment.time_slot).all()

    past = Appointment.query.filter(
        Appointment.client_id == current_user.id,
        db.or_(
            Appointment.date < today,
            Appointment.status.in_(['completed', 'cancelled'])
        )
    ).order_by(Appointment.date.desc(), Appointment.time_slot.desc()).all()

    return render_template('client/appointments.html',
                           upcoming=upcoming,
                           past=past,
                           today=today,
                           MONTHS_ES_UPPER=MONTHS_ES_UPPER,
                           DAYS_ES_SHORT=DAYS_ES_SHORT)


@app.route('/client/loyalty')
@login_required
def client_loyalty():
    loyalty = LoyaltyCard.query.filter_by(client_id=current_user.id).first()
    if not loyalty:
        loyalty = LoyaltyCard(client_id=current_user.id, total_cuts=0, free_cuts_redeemed=0)
        db.session.add(loyalty)
        db.session.commit()

    # History of all completed appointments
    completed_appts = Appointment.query.filter_by(
        client_id=current_user.id,
        status='completed'
    ).order_by(Appointment.date.desc()).all()

    return render_template('client/loyalty.html',
                           loyalty=loyalty,
                           completed_appts=completed_appts,
                           MONTHS_ES_UPPER=MONTHS_ES_UPPER)


@app.route('/client/notifications')
@login_required
def client_notifications():
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(
        Notification.created_at.desc()
    ).all()
    # Mark all as read
    Notification.query.filter_by(user_id=current_user.id, read=False).update({'read': True})
    db.session.commit()
    return render_template('client/notifications.html', notifications=notifications)


@app.route('/client/appointments/<int:appt_id>/cancel', methods=['POST'])
@login_required
def client_cancel_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.client_id != current_user.id:
        flash('No tenés permiso para cancelar este turno.', 'error')
        return redirect(url_for('client_appointments'))
    if appt.status in ('pending', 'confirmed'):
        appt.status = 'cancelled'
        notif = Notification(
            user_id=current_user.id,
            message=f"Tu turno del {appt.date.strftime('%d/%m/%Y')} a las {appt.time_slot} fue cancelado."
        )
        db.session.add(notif)
        db.session.commit()
        flash('Turno cancelado.', 'success')
    else:
        flash('No se puede cancelar este turno.', 'error')
    return redirect(url_for('client_appointments'))


@app.route('/client/appointments/<int:appt_id>/reschedule', methods=['POST'])
@login_required
def client_reschedule_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.client_id != current_user.id:
        flash('No tenés permiso para reagendar este turno.', 'error')
        return redirect(url_for('client_appointments'))

    new_date_str = request.form.get('new_date')
    new_time = request.form.get('new_time')

    try:
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Fecha inválida.', 'error')
        return redirect(url_for('client_appointments'))

    available = get_available_slots(appt.barber_id, new_date)
    if new_time not in available:
        flash('El horario seleccionado no está disponible.', 'error')
        return redirect(url_for('client_appointments'))

    appt.date = new_date
    appt.time_slot = new_time
    appt.status = 'confirmed'
    notif = Notification(
        user_id=current_user.id,
        message=f"Tu turno fue reagendado para el {new_date.strftime('%d/%m/%Y')} a las {new_time}."
    )
    db.session.add(notif)
    db.session.commit()
    flash('Turno reagendado con éxito.', 'success')
    return redirect(url_for('client_appointments'))


# ---- Barber Routes ----

@app.route('/barber/')
@barber_required
def barber_agenda():
    return redirect(url_for('barber_agenda_view'))


@app.route('/barber/agenda')
@barber_required
def barber_agenda_view():
    view = request.args.get('view', 'week')
    barber_id = request.args.get('barber_id', type=int)
    date_str = request.args.get('date')

    today = date.today()
    if date_str:
        try:
            ref_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            ref_date = today
    else:
        ref_date = today

    all_barbers = Barber.query.join(User).all()

    if barber_id is None:
        # If user is a barber, show their agenda; otherwise show first barber
        if current_user.role == 'barber' and current_user.barber_profile:
            barber_id = current_user.barber_profile.id
        elif all_barbers:
            barber_id = all_barbers[0].id

    selected_barber = Barber.query.get(barber_id) if barber_id else None

    if view == 'day':
        # Day view
        appointments = Appointment.query.filter_by(
            barber_id=barber_id,
            date=ref_date
        ).order_by(Appointment.time_slot).all()

        time_slots = []
        h, m = 9, 0
        while (h, m) < (20, 0):
            time_slots.append(f"{h:02d}:{m:02d}")
            m += 30
            if m >= 60:
                m = 0
                h += 1

        appt_by_slot = {}
        for appt in appointments:
            appt_by_slot[appt.time_slot] = appt

        # Stats
        total = len(appointments)
        completed = sum(1 for a in appointments if a.status == 'completed')
        revenue = sum(a.service.price for a in appointments if a.status == 'completed')
        next_appt = next((a for a in appointments if a.status in ('pending', 'confirmed')), None)

        prev_day = ref_date - timedelta(days=1)
        next_day = ref_date + timedelta(days=1)
        return render_template('barber/agenda.html',
                               view='day',
                               ref_date=ref_date,
                               today=today,
                               all_barbers=all_barbers,
                               selected_barber=selected_barber,
                               barber_id=barber_id,
                               appointments=appointments,
                               appt_by_slot=appt_by_slot,
                               time_slots=time_slots,
                               total=total,
                               completed=completed,
                               revenue=revenue,
                               next_appt=next_appt,
                               prev_day_date=prev_day.isoformat(),
                               next_day_date=next_day.isoformat(),
                               minutes_until=None,
                               MONTHS_ES_UPPER=MONTHS_ES_UPPER,
                               DAYS_ES_SHORT=DAYS_ES_SHORT,
                               DAYS_ES=DAYS_ES)
    else:
        # Week view
        week_dates = get_week_dates(ref_date)

        # Get all appointments for the week for all barbers (or selected barber)
        week_start = week_dates[0]
        week_end = week_dates[6]

        query = Appointment.query.filter(
            Appointment.date >= week_start,
            Appointment.date <= week_end
        )
        if barber_id:
            query = query.filter_by(barber_id=barber_id)
        week_appointments = query.order_by(Appointment.time_slot).all()

        # Build grid: {date: {time_slot: appointment}}
        appt_grid = {}
        for d in week_dates:
            appt_grid[d] = {}
        for appt in week_appointments:
            if appt.date in appt_grid:
                appt_grid[appt.date][appt.time_slot] = appt

        time_slots = []
        h, m = 9, 0
        while (h, m) < (20, 0):
            time_slots.append(f"{h:02d}:{m:02d}")
            m += 30
            if m >= 60:
                m = 0
                h += 1

        # Stats for today
        today_appts = [a for a in week_appointments if a.date == today]
        total = len(today_appts)
        completed = sum(1 for a in today_appts if a.status == 'completed')
        revenue = sum(a.service.price for a in today_appts if a.status == 'completed')

        now_time = datetime.now()
        next_appt = None
        for appt in week_appointments:
            if appt.date == today and appt.status in ('pending', 'confirmed'):
                appt_dt = datetime.combine(appt.date, datetime.strptime(appt.time_slot, '%H:%M').time())
                if appt_dt > now_time:
                    next_appt = appt
                    break

        # Minutes until next appointment
        minutes_until = None
        if next_appt:
            appt_dt = datetime.combine(next_appt.date, datetime.strptime(next_appt.time_slot, '%H:%M').time())
            diff = appt_dt - now_time
            minutes_until = int(diff.total_seconds() / 60)

        prev_week = week_dates[0] - timedelta(days=7)
        next_week = week_dates[6] + timedelta(days=1)
        return render_template('barber/agenda.html',
                               view='week',
                               ref_date=ref_date,
                               today=today,
                               week_dates=week_dates,
                               all_barbers=all_barbers,
                               selected_barber=selected_barber,
                               barber_id=barber_id,
                               appt_grid=appt_grid,
                               time_slots=time_slots,
                               total=total,
                               completed=completed,
                               revenue=revenue,
                               next_appt=next_appt,
                               minutes_until=minutes_until,
                               prev_week_date=prev_week.isoformat(),
                               next_week_date=next_week.isoformat(),
                               prev_day_date=ref_date.isoformat(),
                               next_day_date=ref_date.isoformat(),
                               MONTHS_ES_UPPER=MONTHS_ES_UPPER,
                               DAYS_ES_SHORT=DAYS_ES_SHORT,
                               DAYS_ES=DAYS_ES)


@app.route('/barber/clients')
@barber_required
def barber_clients():
    search = request.args.get('q', '').strip()
    query = User.query.filter_by(role='client')
    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    clients = query.order_by(User.name).all()

    # Enrich with stats
    client_stats = []
    for client in clients:
        total_appts = Appointment.query.filter_by(client_id=client.id).count()
        completed_appts = Appointment.query.filter_by(client_id=client.id, status='completed').count()
        last_appt = Appointment.query.filter_by(
            client_id=client.id, status='completed'
        ).order_by(Appointment.date.desc()).first()
        loyalty = LoyaltyCard.query.filter_by(client_id=client.id).first()
        client_stats.append({
            'user': client,
            'total': total_appts,
            'completed': completed_appts,
            'last_appt': last_appt,
            'loyalty': loyalty
        })

    return render_template('barber/clients.html',
                           client_stats=client_stats,
                           search=search,
                           MONTHS_ES_UPPER=MONTHS_ES_UPPER)


@app.route('/barber/clients/<int:client_id>')
@barber_required
def barber_client_detail(client_id):
    client = User.query.get_or_404(client_id)
    appointments = Appointment.query.filter_by(client_id=client_id).order_by(
        Appointment.date.desc(), Appointment.time_slot.desc()
    ).all()
    loyalty = LoyaltyCard.query.filter_by(client_id=client_id).first()
    return render_template('barber/client_detail.html',
                           client=client,
                           appointments=appointments,
                           loyalty=loyalty,
                           MONTHS_ES_UPPER=MONTHS_ES_UPPER,
                           DAYS_ES_SHORT=DAYS_ES_SHORT)


@app.route('/barber/revenue')
@barber_required
def barber_revenue():
    today = date.today()
    # This week
    week_dates = get_week_dates(today)
    week_start = week_dates[0]
    week_end = week_dates[6]

    # This month
    month_start = today.replace(day=1)

    barber_id = request.args.get('barber_id', type=int)
    all_barbers = Barber.query.join(User).all()

    base_query = Appointment.query.filter_by(status='completed')
    if barber_id:
        base_query = base_query.filter_by(barber_id=barber_id)

    # Today revenue
    today_appts = base_query.filter_by(date=today).all()
    today_revenue = sum(a.service.price for a in today_appts)
    today_count = len(today_appts)

    # Week revenue
    week_appts = base_query.filter(
        Appointment.date >= week_start,
        Appointment.date <= week_end
    ).all()
    week_revenue = sum(a.service.price for a in week_appts)
    week_count = len(week_appts)

    # Month revenue
    month_appts = base_query.filter(Appointment.date >= month_start).all()
    month_revenue = sum(a.service.price for a in month_appts)
    month_count = len(month_appts)

    # By service breakdown
    service_stats = {}
    for appt in month_appts:
        svc = appt.service.name
        if svc not in service_stats:
            service_stats[svc] = {'count': 0, 'revenue': 0}
        service_stats[svc]['count'] += 1
        service_stats[svc]['revenue'] += appt.service.price

    # By barber breakdown
    barber_stats = {}
    if not barber_id:
        all_month = Appointment.query.filter(
            Appointment.status == 'completed',
            Appointment.date >= month_start
        ).all()
        for appt in all_month:
            bname = appt.barber.name
            if bname not in barber_stats:
                barber_stats[bname] = {'count': 0, 'revenue': 0, 'barber': appt.barber}
            barber_stats[bname]['count'] += 1
            barber_stats[bname]['revenue'] += appt.service.price

    # Daily breakdown for the week
    daily_stats = []
    for d in week_dates:
        day_appts = [a for a in week_appts if a.date == d]
        daily_stats.append({
            'date': d,
            'count': len(day_appts),
            'revenue': sum(a.service.price for a in day_appts)
        })

    return render_template('barber/revenue.html',
                           today=today,
                           today_revenue=today_revenue,
                           today_count=today_count,
                           week_revenue=week_revenue,
                           week_count=week_count,
                           month_revenue=month_revenue,
                           month_count=month_count,
                           service_stats=service_stats,
                           barber_stats=barber_stats,
                           daily_stats=daily_stats,
                           all_barbers=all_barbers,
                           barber_id=barber_id,
                           format_price=format_price,
                           DAYS_ES_SHORT=DAYS_ES_SHORT,
                           MONTHS_ES_UPPER=MONTHS_ES_UPPER)


@app.route('/barber/services', methods=['GET', 'POST'])
@barber_required
def barber_services():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'create':
            name = request.form.get('name', '').strip()
            duration = int(request.form.get('duration_minutes', 30))
            price = int(request.form.get('price', 0))
            description = request.form.get('description', '').strip()
            if name:
                svc = Service(name=name, duration_minutes=duration, price=price, description=description)
                db.session.add(svc)
                db.session.commit()
                flash('Servicio creado.', 'success')
        elif action == 'edit':
            svc_id = int(request.form.get('service_id'))
            svc = Service.query.get_or_404(svc_id)
            svc.name = request.form.get('name', svc.name).strip()
            svc.duration_minutes = int(request.form.get('duration_minutes', svc.duration_minutes))
            svc.price = int(request.form.get('price', svc.price))
            svc.description = request.form.get('description', svc.description).strip()
            db.session.commit()
            flash('Servicio actualizado.', 'success')
        elif action == 'delete':
            svc_id = int(request.form.get('service_id'))
            svc = Service.query.get_or_404(svc_id)
            db.session.delete(svc)
            db.session.commit()
            flash('Servicio eliminado.', 'success')
        return redirect(url_for('barber_services'))

    services = Service.query.order_by(Service.name).all()
    return render_template('barber/services.html', services=services)


@app.route('/barber/block', methods=['POST'])
@barber_required
def barber_block():
    barber_id = request.form.get('barber_id', type=int)
    if not barber_id and current_user.barber_profile:
        barber_id = current_user.barber_profile.id
    date_str = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')
    reason = request.form.get('reason', '')

    try:
        block_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Fecha inválida.', 'error')
        return redirect(url_for('barber_agenda_view'))

    block = TimeBlock(
        barber_id=barber_id,
        date=block_date,
        start_time=start_time,
        end_time=end_time,
        reason=reason
    )
    db.session.add(block)
    db.session.commit()
    flash('Bloqueo creado.', 'success')
    return redirect(url_for('barber_agenda_view', barber_id=barber_id))


@app.route('/barber/appointments/<int:appt_id>/complete', methods=['POST'])
@barber_required
def barber_complete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.status == 'confirmed':
        appt.status = 'completed'
        # Update loyalty card
        loyalty = LoyaltyCard.query.filter_by(client_id=appt.client_id).first()
        if not loyalty:
            loyalty = LoyaltyCard(client_id=appt.client_id, total_cuts=0, free_cuts_redeemed=0)
            db.session.add(loyalty)
        loyalty.total_cuts += 1
        # Notify client
        notif = Notification(
            user_id=appt.client_id,
            message=f"Tu corte del {appt.date.strftime('%d/%m/%Y')} con {appt.barber.name} fue completado. ¡Gracias!"
        )
        db.session.add(notif)
        db.session.commit()
        flash('Turno marcado como completado.', 'success')
    return redirect(request.referrer or url_for('barber_agenda_view'))


# ---- API Routes ----

@app.route('/api/available-slots')
@login_required
def api_available_slots():
    barber_id = request.args.get('barber_id', type=int)
    date_str = request.args.get('date')
    if not barber_id or not date_str:
        return jsonify({'error': 'Missing parameters'}), 400
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    slots = get_available_slots(barber_id, target_date)
    return jsonify({'slots': slots, 'date': date_str, 'barber_id': barber_id})


@app.route('/api/appointments', methods=['POST'])
@login_required
def api_create_appointment():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    barber_id = data.get('barber_id')
    service_id = data.get('service_id')
    date_str = data.get('date')
    time_slot = data.get('time_slot')
    notes = data.get('notes', '')

    if not all([barber_id, service_id, date_str, time_slot]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        appt_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    available = get_available_slots(int(barber_id), appt_date)
    if time_slot not in available:
        return jsonify({'error': 'Time slot not available'}), 409

    appt = Appointment(
        client_id=current_user.id,
        barber_id=int(barber_id),
        service_id=int(service_id),
        date=appt_date,
        time_slot=time_slot,
        status='confirmed',
        notes=notes
    )
    db.session.add(appt)
    db.session.commit()

    return jsonify({
        'id': appt.id,
        'date': date_str,
        'time_slot': time_slot,
        'status': appt.status
    }), 201


@app.route('/api/appointments/<int:appt_id>')
@login_required
def api_get_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if appt.client_id != current_user.id and current_user.role not in ('barber', 'admin'):
        return jsonify({'error': 'Forbidden'}), 403
    return jsonify({
        'id': appt.id,
        'date': appt.date.isoformat(),
        'time_slot': appt.time_slot,
        'status': appt.status,
        'service': appt.service.name,
        'barber': appt.barber.name,
        'client': appt.client.name,
        'notes': appt.notes
    })


def auto_seed():
    """Seed the database if it's empty (first deploy)."""
    if User.query.first():
        return
    print("Database is empty — running auto-seed...")
    from seed import seed
    seed()


with app.app_context():
    db.create_all()
    auto_seed()


if __name__ == '__main__':
    app.run(debug=True)
