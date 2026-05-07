"""
Railway release script — runs before gunicorn starts.
Creates tables and seeds demo data if the database is empty.
"""
from app import app
from models import db, User

with app.app_context():
    db.create_all()
    if not User.query.first():
        print("Database is empty — seeding demo data...")
        from seed import seed
        seed()
    else:
        print("Database already has data — skipping seed.")
