"""
Seed script to populate the database with demo data.
Run: python seed.py
"""

import os
from datetime import date, timedelta, time
from dotenv import load_dotenv

load_dotenv()

from app import app
from models import db, User, Barber, Service, Appointment, LoyaltyCard, Notification, TimeBlock


def seed():
    with app.app_context():
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()

        print("Seeding database...")

        # ---- BARBER USERS ----
        tito_user = User(name='Tito Ramírez', email='tito@demo.com', role='barber')
        tito_user.set_password('1234')

        maca_user = User(name='Maca González', email='maca@demo.com', role='barber')
        maca_user.set_password('1234')

        joaco_user = User(name='Joaco Pérez', email='joaco@demo.com', role='barber')
        joaco_user.set_password('1234')

        eze_user = User(name='Eze Morales', email='eze@demo.com', role='barber')
        eze_user.set_password('1234')

        admin_user = User(name='Admin', email='admin@demo.com', role='admin')
        admin_user.set_password('1234')

        db.session.add_all([tito_user, maca_user, joaco_user, eze_user, admin_user])
        db.session.flush()

        # ---- BARBER PROFILES ----
        tito = Barber(
            user_id=tito_user.id,
            level='Fundador',
            years=12,
            specialties='Clásico, Degradé, Barba',
            avatar_color='#E8302A',
            rating=5.0,
            avatar_initials='TR'
        )
        maca = Barber(
            user_id=maca_user.id,
            level='Senior',
            years=7,
            specialties='Degradé, Keratina, Coloración',
            avatar_color='#2D2D2D',
            rating=4.9,
            avatar_initials='MG'
        )
        joaco = Barber(
            user_id=joaco_user.id,
            level='Senior',
            years=5,
            specialties='Moderno, Texturas, Diseño',
            avatar_color='#556B2F',
            rating=4.8,
            avatar_initials='JP'
        )
        eze = Barber(
            user_id=eze_user.id,
            level='Junior',
            years=2,
            specialties='Corte básico, Barba',
            avatar_color='#888888',
            rating=4.6,
            avatar_initials='EM'
        )
        db.session.add_all([tito, maca, joaco, eze])
        db.session.flush()

        # ---- CLIENT USERS ----
        lucas = User(name='Lucas Fernández', email='lucas@demo.com', role='client')
        lucas.set_password('1234')

        sofia = User(name='Sofía Martínez', email='sofia@demo.com', role='client')
        sofia.set_password('1234')

        martin = User(name='Martín López', email='martin@demo.com', role='client')
        martin.set_password('1234')

        camila = User(name='Camila Torres', email='camila@demo.com', role='client')
        camila.set_password('1234')

        nicolas = User(name='Nicolás García', email='nicolas@demo.com', role='client')
        nicolas.set_password('1234')

        valentina = User(name='Valentina Ruiz', email='valentina@demo.com', role='client')
        valentina.set_password('1234')

        db.session.add_all([lucas, sofia, martin, camila, nicolas, valentina])
        db.session.flush()

        # ---- SERVICES ----
        corte = Service(name='Corte', duration_minutes=30, price=8000, description='Corte clásico a tijera o máquina')
        corte_barba = Service(name='Corte + Barba', duration_minutes=45, price=12000, description='Corte completo más arreglo de barba')
        barba = Service(name='Barba', duration_minutes=20, price=5000, description='Arreglo y perfilado de barba')
        keratina = Service(name='Keratina', duration_minutes=60, price=15000, description='Tratamiento de keratina para alisado')
        degrade = Service(name='Degradé', duration_minutes=30, price=9000, description='Degradé moderno con diseño personalizado')

        db.session.add_all([corte, corte_barba, barba, keratina, degrade])
        db.session.flush()

        # ---- APPOINTMENTS ----
        today = date.today()
        # Monday of current week
        monday = today - timedelta(days=today.weekday())

        appointments = []

        # Lucas — next confirmed appointment (tomorrow or this week)
        next_date = today + timedelta(days=1)
        if next_date.weekday() == 6:  # skip Sunday
            next_date += timedelta(days=1)

        lucas_next = Appointment(
            client_id=lucas.id,
            barber_id=tito.id,
            service_id=corte_barba.id,
            date=next_date,
            time_slot='15:30',
            status='confirmed',
            notes='Dejame el degradé bien marcado'
        )
        appointments.append(lucas_next)

        # Past appointments for Lucas (completed) — for loyalty
        for i, offset in enumerate([7, 14, 21, 28]):
            past_date = today - timedelta(days=offset)
            if past_date.weekday() == 6:
                past_date -= timedelta(days=1)
            slot = ['10:00', '11:00', '14:00', '16:30'][i]
            svc = [corte_barba, corte, degrade, corte_barba][i]
            appt = Appointment(
                client_id=lucas.id,
                barber_id=tito.id,
                service_id=svc.id,
                date=past_date,
                time_slot=slot,
                status='completed'
            )
            appointments.append(appt)

        # This week's appointments for all barbers
        week_data = [
            # (client, barber, service, day_offset, time, status)
            (sofia, tito, corte, 0, '10:00', 'completed'),
            (martin, tito, barba, 0, '11:30', 'completed'),
            (camila, tito, degrade, 0, '14:00', 'confirmed'),
            (nicolas, tito, corte_barba, 1, '09:30', 'confirmed'),
            (valentina, tito, corte, 1, '11:00', 'confirmed'),
            (sofia, maca, keratina, 0, '10:00', 'completed'),
            (martin, maca, corte, 0, '14:30', 'confirmed'),
            (camila, maca, corte_barba, 2, '10:00', 'confirmed'),
            (nicolas, joaco, degrade, 0, '09:00', 'completed'),
            (valentina, joaco, corte, 0, '13:00', 'confirmed'),
            (sofia, joaco, barba, 1, '15:00', 'confirmed'),
            (lucas, eze, corte, 2, '10:30', 'confirmed'),
            (martin, eze, barba, 3, '11:00', 'confirmed'),
            (camila, eze, corte, 4, '14:00', 'confirmed'),
        ]

        for client, barber, service, day_offset, slot, status in week_data:
            appt_date = monday + timedelta(days=day_offset)
            if appt_date.weekday() == 6:
                continue
            appt = Appointment(
                client_id=client.id,
                barber_id=barber.id,
                service_id=service.id,
                date=appt_date,
                time_slot=slot,
                status=status
            )
            appointments.append(appt)

        db.session.add_all(appointments)
        db.session.flush()

        # ---- LOYALTY CARDS ----
        lucas_loyalty = LoyaltyCard(client_id=lucas.id, total_cuts=4, free_cuts_redeemed=1)
        sofia_loyalty = LoyaltyCard(client_id=sofia.id, total_cuts=8, free_cuts_redeemed=1)
        martin_loyalty = LoyaltyCard(client_id=martin.id, total_cuts=3, free_cuts_redeemed=0)
        camila_loyalty = LoyaltyCard(client_id=camila.id, total_cuts=6, free_cuts_redeemed=1)
        nicolas_loyalty = LoyaltyCard(client_id=nicolas.id, total_cuts=2, free_cuts_redeemed=0)
        valentina_loyalty = LoyaltyCard(client_id=valentina.id, total_cuts=5, free_cuts_redeemed=0)

        db.session.add_all([
            lucas_loyalty, sofia_loyalty, martin_loyalty,
            camila_loyalty, nicolas_loyalty, valentina_loyalty
        ])

        # ---- NOTIFICATIONS for Lucas ----
        notifs = [
            Notification(
                user_id=lucas.id,
                message=f'Tu turno con Tito Ramírez para Corte + Barba el {next_date.strftime("%d/%m/%Y")} a las 15:30 fue confirmado.',
                read=False
            ),
            Notification(
                user_id=lucas.id,
                message='Tu corte del {} con Tito Ramírez fue completado. ¡Gracias!'.format(
                    (today - timedelta(days=7)).strftime('%d/%m/%Y')
                ),
                read=True
            ),
            Notification(
                user_id=lucas.id,
                message='¡Estás a 2 cortes de obtener uno gratis! Seguí acumulando con el Programa Fidelidad.',
                read=False
            ),
            Notification(
                user_id=lucas.id,
                message='Tu turno fue reagendado correctamente.',
                read=True
            ),
        ]
        db.session.add_all(notifs)

        db.session.commit()
        print("✓ Database seeded successfully!")
        print("\nDemo credentials:")
        print("  Cliente:  lucas@demo.com / 1234")
        print("  Barbero:  tito@demo.com / 1234")
        print("  Admin:    admin@demo.com / 1234")
        print("\nOther barbers: maca@demo.com, joaco@demo.com, eze@demo.com (all: 1234)")
        print("Other clients: sofia@demo.com, martin@demo.com, camila@demo.com (all: 1234)")


if __name__ == '__main__':
    seed()
