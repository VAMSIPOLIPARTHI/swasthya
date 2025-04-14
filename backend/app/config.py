import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'telemedicin_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI', 'sqlite:///tel.db')
   
    SQLALCHEMY_TRACK_MODIFICATIONS = False
@app.route('/download_db') 
def download_db():
    db_directory = '.'  # Or the actual directory where teleme.db is
    db_filename = 'teleme.db'
    return send_from_directory(db_directory, db_filename, as_attachment=True)