import csv

def check_doctor_login(doctor_id, password):
    with open("/home/user/telemedicine/backend/database/doctors.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["ID"] == doctor_id and row["password"] == password:
                return True
    return False
