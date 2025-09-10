🏥 Telemedicine Platform

A Flask-based telemedicine platform that connects patients, doctors, and administrators, making healthcare more accessible, affordable, and AI-driven. The system integrates appointment booking, medical report management, AI-powered anemia detection, and NLP-based report summarization to deliver smarter healthcare services.

🚀** Features**
👨‍⚕️ **Patients**

Secure signup/login (with password hashing using Flask-Bcrypt).

Book and manage appointments with doctors.

Upload, download, and view lab reports.

Search for basic medications for common diseases.

Get AI-powered anemia detection from blood smear images.

Access AI-based medical report summarization for easy understanding.

👩‍⚕️ **Doctors**

Manage profiles with images and contact info.

View and reply to patient queries.

Access and update patient records.

Manage appointments.

🛠️** Admin**

Add, update, or remove doctors.

Monitor patients, appointments, and reports.

🤖 **AI Integrations**

Anemia Detection → TensorFlow CNN model for blood smear analysis.

Medical Report Summarization → NLP with Hugging Face T5 Transformer.
**
🗄️ **Data Management****

Database → SQLite for patients, appointments, and medical records.

Doctors & Medications → Managed using CSV files.

Lab Reports → Uploaded files stored securely, retrievable anytime.

**🛠️ Tech Stack**

**Backend**: Flask, FastAPI (for AI services)

**Database**: SQLite + CSV-based doctor/medicine data

**Frontend**: HTML, CSS, JavaScript, Jinja2

**Security**: Flask-Bcrypt (password hashing), Flask-Session

**AI/ML**: TensorFlow, Hugging Face Transformers (T5), XGBoost

**Data Handling:** Pandas, NumPy

**Image Processing**: Pillow (PIL)

⚡ **Installation & Setup**

Clone the repo

git clone https://github.com/your-username/telemedicine.git
cd telemedicine/backend


Create & activate virtual environment

python3 -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows


Install dependencies

pip install -r requirements.txt


Run the application

flask run


Open in browser → http://127.0.0.1:5000/

📌 **Future Enhancements
**
Add real-time video consultations with WebRTC.

Support for multiple languages in the patient dashboard.

Expand AI for disease prediction using medical history.

Mobile app integration (Android/iOS).
