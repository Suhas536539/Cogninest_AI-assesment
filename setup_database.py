from __future__ import annotations

import random
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "clinic.db"
RANDOM_SEED = 42


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Krish",
    "Ishaan", "Kabir", "Rohan", "Rahul", "Ananya", "Diya", "Aisha", "Ira",
    "Meera", "Saanvi", "Kiara", "Myra", "Naina", "Priya", "Sneha", "Riya",
    "John", "Jane", "Michael", "Emily", "David", "Olivia", "Daniel", "Sophia",
]

LAST_NAMES = [
    "Sharma", "Patel", "Gupta", "Singh", "Kumar", "Verma", "Mehta", "Reddy",
    "Nair", "Iyer", "Brown", "Miller", "Wilson", "Moore", "Taylor", "Anderson",
    "Thomas", "Jackson", "White", "Harris",
]

DOCTOR_NAMES = [
    "Dr. Aditi Rao", "Dr. Neha Kapoor", "Dr. Vikram Mehta",
    "Dr. Anil Nair", "Dr. Pooja Shah", "Dr. Rohan Iyer",
    "Dr. Kavya Menon", "Dr. Sameer Jain", "Dr. Priyanka Singh",
    "Dr. Arjun Das", "Dr. Nisha Verma", "Dr. Karan Patel",
    "Dr. Mehul Joshi", "Dr. Sneha Reddy", "Dr. Tania Dsouza",
]

SPECIALIZATION_MAP = {
    "Dermatology": "Skin Care",
    "Cardiology": "Heart Care",
    "Orthopedics": "Bone & Joint",
    "General": "Primary Care",
    "Pediatrics": "Child Care",
}

CITIES = [
    "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Kochi",
]

APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
INVOICE_STATUSES = ["Paid", "Pending", "Overdue"]

TREATMENTS = {
    "Dermatology": [
        ("Skin Consultation", 300, 20),
        ("Acne Treatment", 850, 30),
        ("Laser Therapy", 2800, 45),
    ],
    "Cardiology": [
        ("ECG Review", 500, 20),
        ("Cardiac Consultation", 1200, 35),
        ("Stress Test", 3200, 60),
    ],
    "Orthopedics": [
        ("Fracture Follow-up", 900, 25),
        ("Physio Assessment", 650, 30),
        ("Joint Injection", 2200, 40),
    ],
    "General": [
        ("General Checkup", 250, 15),
        ("Blood Pressure Review", 180, 10),
        ("Health Screening", 1500, 50),
    ],
    "Pediatrics": [
        ("Child Wellness Visit", 400, 20),
        ("Vaccination Review", 700, 15),
        ("Growth Assessment", 950, 25),
    ],
}


def random_date_within(days: int) -> date:
    return date.today() - timedelta(days=random.randint(0, days))


def random_datetime_within(days: int) -> datetime:
    base = datetime.now() - timedelta(days=random.randint(0, days))
    return base.replace(
        hour=random.randint(8, 18),
        minute=random.choice([0, 15, 30, 45]),
        second=0,
        microsecond=0,
    )


def maybe_null(value: str, probability: float) -> str | None:
    return None if random.random() < probability else value


def create_schema(cursor: sqlite3.Cursor) -> None:
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;

        DROP TABLE IF EXISTS treatments;
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS patients;

        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT,
            city TEXT,
            registered_date DATE
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            department TEXT,
            phone TEXT
        );

        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATETIME,
            status TEXT,
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        );

        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            treatment_name TEXT,
            cost REAL,
            duration_minutes INTEGER,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        );

        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            invoice_date DATE,
            total_amount REAL,
            paid_amount REAL,
            status TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE INDEX idx_appointments_date ON appointments(appointment_date);
        CREATE INDEX idx_appointments_patient ON appointments(patient_id);
        CREATE INDEX idx_appointments_doctor ON appointments(doctor_id);
        CREATE INDEX idx_treatments_appointment ON treatments(appointment_id);
        CREATE INDEX idx_invoices_patient ON invoices(patient_id);
        """
    )


def insert_doctors(cursor: sqlite3.Cursor) -> list[tuple[int, str, str]]:
    specializations = list(SPECIALIZATION_MAP.items())
    doctor_rows = []
    for index, doctor_name in enumerate(DOCTOR_NAMES):
        specialization, department = specializations[index % len(specializations)]
        doctor_rows.append(
            (
                doctor_name,
                specialization,
                department,
                f"+91-98{random.randint(10000000, 99999999)}",
            )
        )

    cursor.executemany(
        "INSERT INTO doctors (name, specialization, department, phone) VALUES (?, ?, ?, ?)",
        doctor_rows,
    )

    rows = cursor.execute("SELECT id, name, specialization FROM doctors ORDER BY id").fetchall()
    return [(row[0], row[1], row[2]) for row in rows]


def insert_patients(cursor: sqlite3.Cursor) -> list[int]:
    patient_rows = []
    for _ in range(200):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        registered = random_date_within(365)
        dob = registered - timedelta(days=random.randint(18 * 365, 80 * 365))
        phone = maybe_null(f"+91-9{random.randint(100000000, 999999999)}", 0.12)
        email_local = f"{first_name}.{last_name}.{random.randint(1, 999)}".lower()
        email = maybe_null(f"{email_local}@example.com", 0.15)
        patient_rows.append(
            (
                first_name,
                last_name,
                email,
                phone,
                dob.isoformat(),
                random.choice(["M", "F"]),
                random.choice(CITIES),
                registered.isoformat(),
            )
        )

    cursor.executemany(
        """
        INSERT INTO patients (
            first_name, last_name, email, phone, date_of_birth, gender, city, registered_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        patient_rows,
    )

    return [row[0] for row in cursor.execute("SELECT id FROM patients ORDER BY id").fetchall()]


def insert_appointments(cursor: sqlite3.Cursor, patient_ids: list[int], doctors: list[tuple[int, str, str]]) -> list[tuple[int, int, int, str]]:
    heavy_patients = random.sample(patient_ids, 35)
    heavy_doctors = [doctor_id for doctor_id, _, _ in random.sample(doctors, 5)]
    patient_weights = [6 if pid in heavy_patients else 1 for pid in patient_ids]
    doctor_weights = [5 if doc_id in heavy_doctors else 1 for doc_id, _, _ in doctors]
    statuses = (["Completed"] * 350) + (["Scheduled"] * 75) + (["Cancelled"] * 45) + (["No-Show"] * 30)
    random.shuffle(statuses)

    appointment_rows = []
    for index in range(500):
        patient_id = random.choices(patient_ids, weights=patient_weights, k=1)[0]
        doctor = random.choices(doctors, weights=doctor_weights, k=1)[0]
        status = statuses[index]
        notes = maybe_null(
            random.choice(
                [
                    "Follow-up visit",
                    "Needs lab review",
                    "Recurring symptoms",
                    "Routine consultation",
                    "Requested callback",
                ]
            ),
            0.25,
        )
        appointment_rows.append(
            (
                patient_id,
                doctor[0],
                random_datetime_within(365).isoformat(sep=" "),
                status,
                notes,
            )
        )

    cursor.executemany(
        """
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        appointment_rows,
    )

    rows = cursor.execute(
        "SELECT id, patient_id, doctor_id, status FROM appointments ORDER BY id"
    ).fetchall()
    return [(row[0], row[1], row[2], row[3]) for row in rows]


def insert_treatments(cursor: sqlite3.Cursor, appointments: list[tuple[int, int, int, str]], doctors: list[tuple[int, str, str]]) -> int:
    doctor_specialization = {doctor_id: specialization for doctor_id, _, specialization in doctors}
    completed = [appointment for appointment in appointments if appointment[3] == "Completed"]
    selected = random.sample(completed, k=min(350, len(completed)))

    rows = []
    for appointment_id, _, doctor_id, _ in selected:
        specialization = doctor_specialization[doctor_id]
        treatment_name, base_cost, duration = random.choice(TREATMENTS[specialization])
        rows.append(
            (
                appointment_id,
                treatment_name,
                round(min(5000, max(50, random.gauss(base_cost, base_cost * 0.18))), 2),
                max(10, int(random.gauss(duration, duration * 0.2))),
            )
        )

    cursor.executemany(
        """
        INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes)
        VALUES (?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def insert_invoices(cursor: sqlite3.Cursor, patient_ids: list[int], appointments: list[tuple[int, int, int, str]]) -> int:
    patient_visit_counts: defaultdict[int, int] = defaultdict(int)
    for _, patient_id, _, _ in appointments:
        patient_visit_counts[patient_id] += 1

    weights = [max(1, patient_visit_counts.get(pid, 1)) for pid in patient_ids]
    rows = []
    for _ in range(300):
        patient_id = random.choices(patient_ids, weights=weights, k=1)[0]
        invoice_date = random_date_within(365).isoformat()
        total_amount = round(random.uniform(50, 5000), 2)
        status = random.choices(INVOICE_STATUSES, weights=[62, 24, 14], k=1)[0]
        if status == "Paid":
            paid_amount = total_amount
        elif status == "Pending":
            paid_amount = round(random.uniform(total_amount * 0.2, total_amount * 0.9), 2)
        else:
            paid_amount = round(random.uniform(0, total_amount * 0.5), 2)
        rows.append((patient_id, invoice_date, total_amount, paid_amount, status))

    cursor.executemany(
        """
        INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    return len(rows)


def main() -> None:
    random.seed(RANDOM_SEED)
    if DB_PATH.exists():
        DB_PATH.unlink()

    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.cursor()
        create_schema(cursor)
        doctors = insert_doctors(cursor)
        patient_ids = insert_patients(cursor)
        appointments = insert_appointments(cursor, patient_ids, doctors)
        treatment_count = insert_treatments(cursor, appointments, doctors)
        invoice_count = insert_invoices(cursor, patient_ids, appointments)
        connection.commit()

    print(
        f"Created {len(patient_ids)} patients, {len(doctors)} doctors, "
        f"{len(appointments)} appointments, {treatment_count} treatments, {invoice_count} invoices."
    )


if __name__ == "__main__":
    main()
