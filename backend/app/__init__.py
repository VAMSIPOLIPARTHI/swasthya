import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session

# Initialize SQLAlchemy (db will be bound to the app later)
db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    # Configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///telemedicine.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "your_secret_key"
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(os.path.abspath(os.path.dirname(__file__)), "flask_session")

    # Initialize extensions
    db.init_app(app)
    Session(app)

    # Import and setup routes after app and db are defined
    from .routes import setup_routes
    setup_routes(app, db)  # Pass app and db to setup_routes

    # Create database tables
    with app.app_context():
        db.create_all()

    return app

# Create the app instance at module level for Flask CLI
app = create_app()