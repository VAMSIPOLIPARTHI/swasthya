from flask import request, render_template, redirect, url_for, session, flash, send_file
from app.models import Patient, Appointment, LabReport, PatientRecord, Doctor, MedicationSearch, MedicalRecord, Record
from flask_bcrypt import Bcrypt
import csv
import os
import pandas as pd
from PIL import Image
import numpy as np
from datetime import datetime
import tensorflow as tf
from transformers import T5Tokenizer

# Force TensorFlow to use CPU only to avoid CUDA errors
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Disable GPU

bcrypt = Bcrypt()

# Base directory for relative paths (app directory)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
###
# Load models at startup with error handling
try:
    summarizer = tf.keras.models.load_model(os.path.join(BASE_DIR, "models", "tf_model.h5"))
    print("DEBUG: Successfully loaded custom Keras summarizer model")
    print("DEBUG: Model summary:")
    summarizer.summary(print_fn=lambda x: print(f"DEBUG: {x}"))
except Exception as e:
    print(f"DEBUG: Failed to load summarizer model: {e}")
    summarizer = None

if summarizer is not None:
    try:
        tokenizer = T5Tokenizer.from_pretrained("t5-small")
    except Exception as e:
        print(f"DEBUG: Failed to load tokenizer: {e}")
        tokenizer = None
else:
    tokenizer = None

try:
    anemia_model = tf.keras.models.load_model("/home/user/telemedicine/models/anemia_model (1).h5")
    print("DEBUG: Successfully loaded anemia model")
except Exception as e:
    print(f"DEBUG: Failed to load anemia model: {e}")
    anemia_model = None##

# Utility Functions
def read_doctors_csv(file_path):
    doctors = {}
    try:
        if not os.path.exists(file_path):
            print(f"ERROR: CSV file '{file_path}' not found!")
            return {}
        print(f"DEBUG: Reading CSV file from '{file_path}'")
        with open(file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if "ID" in row and "password" in row:
                    doctor_id = row["ID"].strip()
                    if doctor_id.isdigit():
                        doctors[int(doctor_id)] = {
                            "id": int(doctor_id),
                            "name": row["name"].strip(),
                            "password": row["password"].strip(),
                            "specialization": row["specialization"].strip(),
                            "rating": row["rating"].strip(),
                            "photo": row["photo"].strip(),
                            "symptom": row["symptom"].strip(),
                        }
        return doctors
    except Exception as e:
        print(f"ERROR: Failed to read CSV - {e}")
        return {}

def load_medications(file_path):
    try:
        medications_df = pd.read_csv(file_path)
        medications_dict = {}
        for _, row in medications_df.iterrows():
            disease = row["Disease"].lower()
            medication_info = f"{row['Name']}, {row['Dosage']}, {row['Use']} "
            if disease in medications_dict:
                medications_dict[disease].append(medication_info)
            else:
                medications_dict[disease] = [medication_info]
        return medications_dict
    except Exception as e:
        print(f"ERROR: Failed to load medications - {e}")
        return {}

def search_doctors(symptom):
    doctors = []
    csv_file = os.path.join(BASE_DIR, "..", "database", "doctors.csv")
    try:
        with open(csv_file, mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if symptom.lower() in row["specialization"].lower() or symptom.lower() in row["symptom"].lower():
                    doctors.append({
                        "id": row["ID"],
                        "name": row["name"],
                        "specialization": row["specialization"],
                        "rating": row["rating"],
                        "photo": row["photo"],
                        "contact": row.get("contact", "")
                    })
    except FileNotFoundError:
        print("Doctors database file not found.")
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return doctors

def preprocess_image(image):
    img = Image.open(image).resize((224, 224))
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

def get_doctor_name(doctor_id):
    doctor = Doctor.query.get(doctor_id)
    return doctor.name if doctor else "Unknown"

def summarize_text(content):
    if summarizer is None or tokenizer is None:
        print("DEBUG: Summarizer or tokenizer is None")
        return "Summarization model not available"
    try:
        print("DEBUG: Tokenizing input text")
        inputs = tokenizer(content, return_tensors="tf", max_length=512, truncation=True, padding=True)
        print(f"DEBUG: Input shape: {inputs['input_ids'].shape}")
        
        print("DEBUG: Running model prediction")
        outputs = summarizer(inputs['input_ids'])
        print(f"DEBUG: Model output shape: {outputs.shape}")
        
        if len(outputs.shape) == 3:  # [batch, seq_len, vocab_size] (logits)
            summary_ids = tf.argmax(outputs, axis=-1)
        elif len(outputs.shape) == 2:  # [batch, seq_len] (token IDs)
            summary_ids = outputs
        else:
            raise ValueError(f"Unexpected output shape: {outputs.shape}")
        
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        print(f"DEBUG: Generated summary: {summary}")
        return summary
    except Exception as e:
        print(f"DEBUG: Error during summarization: {e}")
        return f"Error generating summary: {str(e)}"

# Route Setup
def setup_routes(app, db):
    print("DEBUG: Setting up routes")
    bcrypt.init_app(app)
    medications_db = load_medications(os.path.join(BASE_DIR, "..", "database", "medications.csv"))

    @app.route("/")
    def home():
        return render_template("index.html")

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/services")
    def services():
        return render_template("services.html")

    @app.route("/contact")
    def contact():
        return render_template("contact.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            name = request.form["name"]
            user_id = request.form["user_id"]
            password = request.form["password"]
            age = request.form["age"]

            existing_user = Patient.query.filter_by(user_id=user_id).first()
            if existing_user:
                flash("User ID already exists. Choose another one.", "danger")
                return redirect(url_for("signup"))

            new_user = Patient(name=name, user_id=user_id, age=int(age))
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash("Signup successful! Please log in.", "success")
            return redirect(url_for("login_patient"))

        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login_patient():
        if request.method == "POST":
            user_id = request.form["user_id"]
            password = request.form["password"]

            user = Patient.query.filter_by(user_id=user_id).first()
            if user and user.check_password(password):
                session["patient_id"] = user.id
                print(f"DEBUG: Patient login successful - session patient_id set to {user.id}")
                flash("Login successful!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid credentials. Try again.", "danger")
        return render_template("login_patient.html")

    @app.route("/dashboard")
    def dashboard():
        print("DEBUG: Entering /dashboard route")
        if "patient_id" not in session:
            print("DEBUG: No patient_id in session, redirecting to login_patient")
            return redirect(url_for("login_patient"))
        
        patient_id = session["patient_id"]
        print(f"DEBUG: Session patient_id = {patient_id}, type = {type(patient_id)}")
        patient = Patient.query.get(patient_id)
        if not patient:
            print("DEBUG: Patient not found in database, clearing session")
            session.pop("patient_id", None)
            return redirect(url_for("login_patient"))
        
        print(f"DEBUG: Patient found - id={patient.id}, name={patient.name}")
        
        records = PatientRecord.query.filter_by(patient_id=patient_id).order_by(PatientRecord.uploaded_at.desc()).all()
        print(f"DEBUG: Found {len(records)} records for patient_id={patient_id}")
        for record in records:
            print(f"DEBUG: Record - id={record.id}, patient_id={record.patient_id}, file_path={record.file_path}, uploaded_by={record.uploaded_by}, uploaded_at={record.uploaded_at}")

        return render_template("dashboard.html", patient=patient, records=records)

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out.", "info")
        return redirect(url_for("home"))

    @app.route("/doctor_dashboard")
    def doctor_dashboard():
        print("DEBUG: Entering /doctor_dashboard route")
        if "doctor" not in session:
            print("DEBUG: No doctor in session, redirecting to login_doctor")
            flash("Please log in as a doctor first.", "danger")
            return redirect(url_for("login_doctor"))
        
        doctor_id = int(session["doctor"])
        doctors = read_doctors_csv(os.path.join(BASE_DIR, "..", "database", "doctors.csv"))
        doctor = doctors.get(doctor_id)

        if not doctor:
            print(f"DEBUG: No doctor found with id={doctor_id}")
            flash("Doctor not found.", "danger")
            return redirect(url_for("login_doctor"))

        appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()
        print(f"DEBUG: Retrieved {len(appointments)} appointments for doctor_id={doctor_id}")
        print(f"DEBUG: Doctor found - id={doctor_id}, name={doctor['name']}")
        return render_template(
            "doctor_dashboard.html",
            doctor=doctor,
            appointments=appointments
        )

    @app.route("/profile")
    def profile():
        print("DEBUG: Entering /profile route")
        if "doctor" not in session:
            print("DEBUG: No doctor in session, redirecting to login_doctor")
            return redirect(url_for("login_doctor"))
        
        doctors = read_doctors_csv(os.path.join(BASE_DIR, "..", "database", "doctors.csv"))
        doctor = doctors.get(int(session["doctor"]))
        if doctor:
            print(f"DEBUG: Doctor found - id={session['doctor']}, name={doctor['name']}")
            return render_template("profile.html", doctor=doctor)
        print("DEBUG: No doctor found, redirecting to login_doctor")
        return redirect(url_for("login_doctor"))

    @app.route("/video_call")
    def video_call():
        return render_template("video_call.html")

    @app.route("/view_bookings")
    def view_bookings():
        print("DEBUG: Entering /view_bookings route")
        if "patient_id" not in session:
            print("DEBUG: No patient_id in session, redirecting to login_patient")
            flash("Please log in to view bookings.", "danger")
            return redirect(url_for("login_patient"))
        
        patient_id = session["patient_id"]
        bookings = Appointment.query.filter_by(patient_id=patient_id).all()
        print(f"DEBUG: Total appointments for patient_id={patient_id}: {len(bookings)}")
        for b in bookings:
            print(f"DEBUG: Appointment ID={b.id}, patient_id={b.patient_id}, doctor_name={b.doctor_name}")
        return render_template("bookings.html", bookings=bookings)

    @app.route("/records")
    def records():
        return render_template("records.html")

    @app.route("/medication_search", methods=["GET", "POST"])
    def medication_search():
        if request.method == "POST":
            disease = request.form.get("disease", "").lower()
            medications = medications_db.get(disease, [])
            if not medications:
                flash("No medications found for this disease.", "info")
            return render_template("medication_search.html", medications=medications, disease=disease)
        return render_template("medication_search.html")

    @app.route("/summarize", methods=["GET", "POST"])
    def summarize():
        if summarizer is None or tokenizer is None:
            print("DEBUG: Summarizer or tokenizer is None, redirecting to dashboard")
            flash("Summarization model not available.", "danger")
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            if "medical_record" not in request.files:
                print("DEBUG: No file uploaded")
                flash("No file uploaded.", "danger")
                return redirect(request.url)
            file = request.files["medical_record"]
            if file.filename == "":
                print("DEBUG: No file selected")
                flash("No file selected.", "danger")
                return redirect(request.url)
            if file:
                print("DEBUG: Processing uploaded file")
                content = file.read().decode("utf-8")
                summary = summarize_text(content)
                print(f"DEBUG: Summary generated: {summary}")
                return render_template("summarize.html", summary=summary)
        return render_template("summarize.html")

    @app.route("/anemia_detection", methods=["GET", "POST"])
    def anemia_detection():
        print("DEBUG: Entering /anemia_detection route")
        if anemia_model is None:
            flash("Anemia detection model not available.", "danger")
            return redirect(url_for("dashboard"))
        
        if request.method == "POST":
            if "image" not in request.files:
                flash("No image uploaded.", "danger")
                return redirect(request.url)
            
            image = request.files["image"]
            if image.filename == "":
                flash("No image selected.", "danger")
                return redirect(request.url)
            
            if image:
                try:
                    img_array = preprocess_image(image)
                    prediction = anemia_model.predict(img_array)
                    probability = float(prediction[0][0])  # Ensure probability is a float
                    
                    # Define hemoglobin estimation logic
                    if probability > 0.5:
                        result = "Unhealthy - Possible anemia detected"
                        hb_level = round(13 - (5 * probability), 1)  # Estimate hb_level for anemia
                        if hb_level < 8:
                            hb_level = 8.0  # Minimum realistic hemoglobin level
                    else:
                        result = "Blood levels are normal, no anemia detected"
                        hb_level = round(13 + (2 * (1 - probability)), 1)  # Estimate hb_level for normal
                        if hb_level > 15:
                            hb_level = 15.0  # Maximum realistic hemoglobin level
                    
                    return render_template(
                        "anemia_detection.html",
                        result=result,
                        hb_level=hb_level,
                        probability=probability
                    )
                except Exception as e:
                    print(f"DEBUG: Error during anemia detection: {e}")
                    flash("An error occurred during anemia detection. Please try again.", "danger")
                    return redirect(request.url)
        
        return render_template("anemia_detection.html")

    @app.route("/appointment", methods=["GET", "POST"])
    def appointment():
        doctors = []
        if request.method == "POST":
            symptom = request.form["symptom"]
            doctors = search_doctors(symptom)
        return render_template("appointment.html", doctors=doctors)

    @app.route("/book_appointment", methods=["POST"])
    def book_appointment():
        print("DEBUG: Entering /book_appointment route")
        if "patient_id" not in session:
            flash("Please log in to book an appointment.", "danger")
            return redirect(url_for("login_patient"))

        doctor_id = request.form.get("doctor_id")
        appointment_date = request.form.get("date")
        appointment_time = request.form.get("time")

        print(f"DEBUG: Received: doctor_id={doctor_id}, date={appointment_date}, time={appointment_time}")

        if not all([doctor_id, appointment_date, appointment_time]):
            flash("All fields are required.", "danger")
            return redirect(url_for("appointment"))

        patient = Patient.query.get(session["patient_id"])
        doctors = read_doctors_csv(os.path.join(BASE_DIR, "..", "database", "doctors.csv"))
        doctor_id = int(doctor_id)
        doctor = doctors.get(doctor_id)

        if not doctor:
            flash("Invalid doctor selected.", "danger")
            return redirect(url_for("appointment"))

        new_appointment = Appointment(
            patient_id=patient.id,
            patient_name=patient.name,
            doctor_id=doctor_id,
            doctor_name=doctor["name"],
            date=appointment_date,
            time=appointment_time
        )
        db.session.add(new_appointment)
        db.session.commit()
        print(f"DEBUG: Appointment saved - patient_id={patient.id}, doctor_name={doctor['name']}, date={appointment_date}, time={appointment_time}")
        flash(f"Appointment booked successfully with Dr. {doctor['name']}!", "success")
        return redirect(url_for("success"))

    @app.route("/success")
    def success():
        return render_template("success.html")

    @app.route("/upload_lab_report", methods=["GET", "POST"])
    def upload_lab_report():
        if "patient_id" not in session:
            flash("Please log in to upload lab reports.", "danger")
            return redirect(url_for("login_patient"))

        doctors = read_doctors_csv(os.path.join(BASE_DIR, "..", "database", "doctors.csv"))

        if request.method == "POST":
            lab_report_file = request.files.get("lab_report_file")
            doctor_id = request.form.get("doctor_id")

            if not lab_report_file:
                flash("Lab report file is required.", "danger")
                return redirect(url_for("upload_lab_report"))

            if not doctor_id:
                flash("Please select a doctor.", "danger")
                return redirect(url_for("upload_lab_report"))

            doctor_id = int(doctor_id)
            if doctor_id not in doctors:
                flash("Invalid doctor selected.", "danger")
                return redirect(url_for("upload_lab_report"))

            upload_folder = os.path.join(BASE_DIR, "lab_reports")
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            filename = f"patient_{session['patient_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{lab_report_file.filename}"
            file_path = os.path.join(upload_folder, filename)
            lab_report_file.save(file_path)

            new_lab_report = LabReport(
                patient_id=session["patient_id"],
                file_path=file_path,
                doctor_id=doctor_id
            )
            db.session.add(new_lab_report)
            db.session.commit()

            flash("Lab report uploaded successfully!", "success")
            return redirect(url_for("dashboard"))

        return render_template("upload_lab_report.html", doctors=doctors.values())

    @app.route("/view_lab_reports")
    def view_lab_reports():
        if "doctor" not in session:
            flash("Please log in as a doctor to view lab reports.", "danger")
            return redirect(url_for("login_doctor"))

        doctor_id = int(session["doctor"])
        lab_reports = LabReport.query.filter_by(doctor_id=doctor_id).all()
        print(f"DEBUG: Found {len(lab_reports)} lab reports for doctor_id={doctor_id}")
        return render_template("view_lab_reports.html", lab_reports=lab_reports)

    @app.route("/reply_lab_report/<int:report_id>", methods=["GET", "POST"])
    def reply_lab_report(report_id):
        if "doctor" not in session:
            flash("Please log in as a doctor to reply to lab reports.", "danger")
            return redirect(url_for("login_doctor"))

        lab_report = LabReport.query.get_or_404(report_id)

        if request.method == "POST":
            reply_text = request.form.get("reply_text")

            if not reply_text:
                flash("Reply text is required.", "danger")
                return redirect(url_for("reply_lab_report", report_id=report_id))

            lab_report.doctor_reply = reply_text
            db.session.commit()

            flash("Reply submitted successfully!", "success")
            return redirect(url_for("view_lab_reports"))

        return render_template("reply_lab_report.html", lab_report=lab_report)

    @app.route("/view_lab_report_replies")
    def view_lab_report_replies():
        if "patient_id" not in session:
            flash("Please log in to view lab report replies.", "danger")
            return redirect(url_for("login_patient"))

        lab_reports = LabReport.query.filter_by(patient_id=session["patient_id"]).all()
        return render_template("view_lab_report_replies.html", lab_reports=lab_reports)

    @app.route("/download_lab_report/<int:report_id>")
    def download_lab_report(report_id):
        if "doctor" not in session:
            flash("Please log in as a doctor to download lab reports.", "danger")
            return redirect(url_for("login_doctor"))

        lab_report = LabReport.query.get_or_404(report_id)
        return send_file(lab_report.file_path, as_attachment=True)

    @app.route("/admin_dashboard")
    def admin_dashboard():
        print("DEBUG: Entering /admin_dashboard route")
        print(f"DEBUG: Current session={session}")
        if "admin" not in session:
            flash("Please log in as admin first.", "warning")
            print("DEBUG: No admin in session, redirecting to login_admin")
            return redirect(url_for("login_admin"))
        print(f"DEBUG: Admin logged in with ID={session['admin']}, rendering admin_dashboard.html")
        return render_template("admin_dashboard.html")

    @app.route("/login_admin", methods=["GET", "POST"])
    def login_admin():
        print("DEBUG: Entering /login_admin route")
        if request.method == "POST":
            admin_id = request.form.get("admin_id")
            password = request.form.get("password")
            print(f"DEBUG: Admin login attempt - admin_id={admin_id}")
            if admin_id == "101" and password == "admin123":
                session["admin"] = admin_id
                print(f"DEBUG: Admin login successful, session={session}")
                flash("Login successful!", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                print("DEBUG: Admin login failed - invalid credentials")
                flash("Invalid credentials, try again.", "danger")
        return render_template("login_admin.html")

    @app.route("/logout_admin")
    def logout_admin():
        session.pop("admin", None)
        flash("You have been logged out.", "info")
        return redirect(url_for("login_admin"))

    @app.route("/login_doctor", methods=["GET", "POST"])
    def login_doctor():
        print("DEBUG: Entering /login_doctor route")
        if request.method == "POST":
            print(f"DEBUG: Form data received - {request.form}")
            doctor_id = request.form.get("doctor_id", "").strip()
            password = request.form.get("doctor_password", "").strip()
            print(f"DEBUG: Doctor login attempt - doctor_id='{doctor_id}', password='{password}' (len={len(password)})")
            doctors = read_doctors_csv(os.path.join(BASE_DIR, "..", "database", "doctors.csv"))
            print(f"DEBUG: Available doctor IDs in CSV: {list(doctors.keys())}")
            if not doctor_id.isdigit():
                print(f"DEBUG: Doctor login failed - doctor_id '{doctor_id}' is not numeric")
                flash("Doctor ID must be numeric.", "danger")
                return render_template("login_doctor.html")
            doctor_id = int(doctor_id)
            doctor = doctors.get(doctor_id)
            if doctor:
                stored_password = doctor["password"].strip()
                print(f"DEBUG: Doctor found - id={doctor_id}, stored_password='{stored_password}' (len={len(stored_password)})")
                print(f"DEBUG: Comparing entered='{password}' with stored='{stored_password}'")
                if stored_password == password:
                    session["doctor"] = doctor_id
                    print(f"DEBUG: Doctor login successful, session={session}")
                    flash("Login successful!", "success")
                    return redirect(url_for("doctor_dashboard"))
                else:
                    print("DEBUG: Doctor login failed - password mismatch")
                    flash("Invalid credentials, try again.", "danger")
            else:
                print(f"DEBUG: Doctor login failed - no doctor found with id={doctor_id}")
                flash("Invalid credentials, try again.", "danger")
        return render_template("login_doctor.html")

    @app.route("/manage_doctors", methods=["GET", "POST"])
    def manage_doctors():
        if "admin" not in session:
            flash("Please log in as admin first.", "warning")
            return redirect(url_for("login_admin"))

        csv_path = os.path.join(BASE_DIR, "..", "database", "doctors.csv")
        doctors = read_doctors_csv(csv_path)

        if request.method == "POST":
            action = request.form.get("action")
            doctor_id = request.form.get("doctor_id")
            if action == "remove":
                updated_doctors = {k: v for k, v in doctors.items() if str(k) != doctor_id}
                with open(csv_path, "w", newline="") as csvfile:
                    fieldnames = ["ID", "name", "password", "specialization", "rating", "photo", "symptom"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for key, value in updated_doctors.items():
                        writer.writerow({
                            "ID": key,
                            "name": value["name"],
                            "password": value["password"],
                            "specialization": value["specialization"],
                            "rating": value["rating"],
                            "photo": value["photo"],
                            "symptom": value["symptom"]
                        })
                flash("Doctor removed successfully.", "success")
                return redirect(url_for("manage_doctors"))
            elif action == "add":
                new_id = request.form.get("new_id")
                new_name = request.form.get("new_name")
                new_password = request.form.get("new_password")
                new_specialization = request.form.get("new_specialization")
                new_rating = request.form.get("new_rating")
                new_photo = request.form.get("new_photo")
                new_symptom = request.form.get("new_symptom")
                if new_id and new_name and new_specialization and new_rating and new_symptom:
                    with open(csv_path, "a", newline="") as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([new_id, new_name, new_password, new_specialization, new_rating, new_photo, new_symptom])
                    flash("Doctor added successfully.", "success")
                    return redirect(url_for("manage_doctors"))
        return render_template("manage_doctors.html", doctors=doctors)

    @app.route("/manage_patients", methods=["GET", "POST"])
    def manage_patients():
        print("DEBUG: Entering /manage_patients route")
        if "admin" not in session:
            flash("Please log in as admin first.", "warning")
            return redirect(url_for("login_admin"))

        patients = Patient.query.all()
        patient_data = []
        for patient in patients:
            appointments = Appointment.query.filter_by(patient_id=patient.id).all()
            patient_data.append({
                "id": patient.id,
                "name": patient.name,
                "user_id": patient.user_id,
                "age": patient.age,
                "appointments": appointments
            })
        print(f"DEBUG: Retrieved {len(patients)} patients with appointments")

        if request.method == "POST":
            action = request.form.get("action")
            patient_id = request.form.get("patient_id")
            if action == "remove":
                patient = Patient.query.get(patient_id)
                if patient:
                    Appointment.query.filter_by(patient_id=patient_id).delete()
                    db.session.delete(patient)
                    db.session.commit()
                    flash("Patient and their appointments removed successfully.", "success")
                else:
                    flash("Patient not found.", "danger")
                return redirect(url_for("manage_patients"))
            elif action == "add":
                name = request.form.get("new_name")
                user_id = request.form.get("new_user_id")
                password = request.form.get("new_password")
                age = request.form.get("new_age")
                existing_user = Patient.query.filter_by(user_id=user_id).first()
                if existing_user:
                    flash("User ID already exists. Choose another one.", "danger")
                elif name and user_id and password and age:
                    new_patient = Patient(name=name, user_id=user_id, age=int(age))
                    new_patient.set_password(password)
                    db.session.add(new_patient)
                    db.session.commit()
                    flash("Patient added successfully.", "success")
                else:
                    flash("All fields are required.", "danger")
                return redirect(url_for("manage_patients"))
        return render_template("manage_patients.html", patients=patient_data)

    @app.route("/reply_to_patient/<int:appointment_id>", methods=["GET", "POST"])
    def reply_to_patient(appointment_id):
        if "doctor" not in session:
            flash("Please log in as a doctor to reply to patients.", "danger")
            return redirect(url_for("login_doctor"))

        appointment = Appointment.query.get_or_404(appointment_id)

        if request.method == "POST":
            message = request.form.get("message")

            if not message:
                flash("Reply message cannot be empty.", "danger")
                return redirect(url_for("reply_to_patient", appointment_id=appointment_id))

            appointment.doctor_reply = message
            db.session.commit()

            flash("Reply sent successfully!", "success")
            return redirect(url_for("doctor_dashboard"))

        return render_template("reply_to_patient.html", appointment=appointment)

    @app.route("/upload_records", methods=["GET", "POST"])
    def upload_records():
        if "doctor" not in session:
            flash("Please log in as a doctor to upload records.", "danger")
            return redirect(url_for("login_doctor"))

        if request.method == "POST":
            if "record_file" not in request.files:
                flash("No file uploaded.", "danger")
                return redirect(url_for("upload_records"))

            record_file = request.files["record_file"]

            if record_file.filename == "":
                flash("No file selected.", "danger")
                return redirect(url_for("upload_records"))

            patient_id = request.form.get("patient_id")
            if not patient_id:
                flash("Patient ID is required.", "danger")
                return redirect(url_for("upload_records"))

            patient = Patient.query.get(patient_id)
            if not patient:
                flash("Patient not found.", "danger")
                return redirect(url_for("upload_records"))

            upload_folder = os.path.join(BASE_DIR, "patient_records")
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            filename = f"patient_{patient_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{record_file.filename}"
            file_path = os.path.join(upload_folder, filename)
            record_file.save(file_path)

            new_record = PatientRecord(
                patient_id=int(patient_id),
                file_path=file_path,
                uploaded_by=int(session["doctor"]),
                uploaded_at=datetime.now()
            )
            db.session.add(new_record)
            db.session.commit()

            print(f"DEBUG: Record uploaded - patient_id={patient_id}, file_path={file_path}, uploaded_by={session['doctor']}")
            flash("Record uploaded successfully!", "success")
            return redirect(url_for("doctor_dashboard"))

        return render_template("upload_records.html")

    @app.route("/view_patient_records")
    def view_patient_records():
        if "patient_id" not in session:
            flash("Please log in to view your records.", "danger")
            return redirect(url_for("login_patient"))

        patient_id = session["patient_id"]
        print(f"DEBUG: Fetching records for patient_id={patient_id}")
        records = PatientRecord.query.filter_by(patient_id=patient_id).order_by(PatientRecord.uploaded_at.desc()).all()
        print(f"DEBUG: Found {len(records)} records for patient_id={patient_id}")
        for record in records:
            print(f"DEBUG: Record - id={record.id}, patient_id={record.patient_id}, file_path={record.file_path}, uploaded_by={record.uploaded_by}, uploaded_at={record.uploaded_at}")

        return render_template("view_patient_records.html", records=records)

    @app.route("/download_record/<int:record_id>")
    def download_record(record_id):
        if "patient_id" not in session:
            flash("Please log in to download records.", "danger")
            return redirect(url_for("login_patient"))

        record = PatientRecord.query.get_or_404(record_id)

        if record.patient_id != session["patient_id"]:
            flash("You are not authorized to access this record.", "danger")
            return redirect(url_for("view_patient_records"))

        return send_file(record.file_path, as_attachment=True)

    @app.route("/view_uploaded_records")
    def view_uploaded_records():
        if "doctor" not in session:
            flash("Please log in as a doctor to view uploaded records.", "danger")
            return redirect(url_for("login_doctor"))

        doctor_id = int(session["doctor"])
        records = PatientRecord.query.filter_by(uploaded_by=doctor_id).order_by(PatientRecord.uploaded_at.desc()).all()
        print(f"DEBUG: Found {len(records)} records uploaded by doctor_id={doctor_id}")
        for record in records:
            print(f"DEBUG: Uploaded Record - id={record.id}, patient_id={record.patient_id}, file_path={record.file_path}, uploaded_by={record.uploaded_by}")

        return render_template("view_uploaded_records.html", records=records)


    