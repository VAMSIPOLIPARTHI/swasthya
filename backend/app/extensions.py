from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()  # ✅ Single instance of SQLAlchemy
bcrypt = Bcrypt()  # ✅ Single instance of Bcrypt
