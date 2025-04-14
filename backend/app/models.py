from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_bcrypt import Bcrypt
from datetime import datetime

bcrypt = Bcrypt()

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    photo = db.Column(db.String(255), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Doctor {self.id}: {self.name}>"

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), unique=True, nullable=False)  # Unique user ID
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)  # Store hashed password

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<Patient {self.id}: {self.name}>"

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    patient_name = db.Column(db.String(100), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    doctor_name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f'<Appointment {self.patient_name} with {self.doctor_name} on {self.date} at {self.time}>'

class MedicationSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    disease = db.Column(db.String(100), nullable=False)
    medications = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f"<MedicationSearch {self.id}: {self.patient_name}>"

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    summary = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"<MedicalRecord {self.id}: {self.patient_name}>"

class LabReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)  # Nullable for cases where no doctor is assigned
    doctor_reply = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)  # Add this line

    def __repr__(self):
        return f"<LabReport {self.id} for Patient {self.patient_id}>"

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
   
    def __repr__(self):
        return f"<Record {self.id} for Patient {self.patient_id}>"

class PatientRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)  # Unified, removed duplicate
    uploaded_by = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)  # Doctor who uploaded
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<PatientRecord {self.id} for Patient {self.patient_id}>"