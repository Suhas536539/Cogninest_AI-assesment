from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SeedExample:
    question: str
    sql: str
    notes: str


SEED_EXAMPLES = [
    SeedExample(
        question="How many patients do we have?",
        sql="SELECT COUNT(*) AS total_patients FROM patients",
        notes="Simple row count for the patients table.",
    ),
    SeedExample(
        question="List all doctors and their specializations",
        sql="SELECT name, specialization, department FROM doctors ORDER BY name",
        notes="Doctor directory ordered by name.",
    ),
    SeedExample(
        question="Show me appointments for last month",
        sql=(
            "SELECT a.id, p.first_name || ' ' || p.last_name AS patient_name, d.name AS doctor_name, "
            "a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE date(a.appointment_date) >= date('now', 'start of month', '-1 month') "
            "AND date(a.appointment_date) < date('now', 'start of month') "
            "ORDER BY a.appointment_date"
        ),
        notes="Appointment listing for the previous calendar month.",
    ),
    SeedExample(
        question="Which doctor has the most appointments?",
        sql=(
            "SELECT d.name, COUNT(*) AS appointment_count "
            "FROM appointments a "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY appointment_count DESC, d.name ASC "
            "LIMIT 1"
        ),
        notes="Doctor workload leaderboard.",
    ),
    SeedExample(
        question="What is the total revenue?",
        sql="SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices",
        notes="Invoice-based top-line revenue.",
    ),
    SeedExample(
        question="Show revenue by doctor",
        sql=(
            "SELECT d.name, ROUND(SUM(t.cost), 2) AS total_revenue "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY total_revenue DESC, d.name ASC"
        ),
        notes="Uses treatment cost as the most reliable doctor-level revenue proxy.",
    ),
    SeedExample(
        question="How many cancelled appointments last quarter?",
        sql=(
            "WITH quarter_bounds AS ( "
            "SELECT "
            "CASE "
            "WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 1 AND 3 THEN date(strftime('%Y', 'now') || '-01-01', '-3 months') "
            "WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 4 AND 6 THEN date(strftime('%Y', 'now') || '-01-01') "
            "WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 7 AND 9 THEN date(strftime('%Y', 'now') || '-04-01') "
            "ELSE date(strftime('%Y', 'now') || '-07-01') END AS start_date, "
            "CASE "
            "WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 1 AND 3 THEN date(strftime('%Y', 'now') || '-01-01') "
            "WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 4 AND 6 THEN date(strftime('%Y', 'now') || '-04-01') "
            "WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 7 AND 9 THEN date(strftime('%Y', 'now') || '-07-01') "
            "ELSE date(strftime('%Y', 'now') || '-10-01') END AS end_date ) "
            "SELECT COUNT(*) AS cancelled_appointments "
            "FROM appointments, quarter_bounds "
            "WHERE status = 'Cancelled' "
            "AND date(appointment_date) >= start_date "
            "AND date(appointment_date) < end_date"
        ),
        notes="Previous completed quarter only.",
    ),
    SeedExample(
        question="Top 5 patients by spending",
        sql=(
            "SELECT p.first_name, p.last_name, ROUND(SUM(i.total_amount), 2) AS total_spending "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "GROUP BY p.id, p.first_name, p.last_name "
            "ORDER BY total_spending DESC, p.last_name ASC "
            "LIMIT 5"
        ),
        notes="Invoice spend grouped by patient.",
    ),
    SeedExample(
        question="Average treatment cost by specialization",
        sql=(
            "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS average_treatment_cost "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.specialization "
            "ORDER BY average_treatment_cost DESC"
        ),
        notes="Treatment economics by clinical specialty.",
    ),
    SeedExample(
        question="Show monthly appointment count for the past 6 months",
        sql=(
            "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count "
            "FROM appointments "
            "WHERE date(appointment_date) >= date('now', 'start of month', '-5 months') "
            "GROUP BY strftime('%Y-%m', appointment_date) "
            "ORDER BY month"
        ),
        notes="Time-series appointment trend.",
    ),
    SeedExample(
        question="Which city has the most patients?",
        sql=(
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients "
            "GROUP BY city "
            "ORDER BY patient_count DESC, city ASC "
            "LIMIT 1"
        ),
        notes="Most represented patient city.",
    ),
    SeedExample(
        question="List patients who visited more than 3 times",
        sql=(
            "SELECT p.first_name, p.last_name, COUNT(*) AS visit_count "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "WHERE a.status IN ('Completed', 'Scheduled', 'No-Show') "
            "GROUP BY p.id, p.first_name, p.last_name "
            "HAVING COUNT(*) > 3 "
            "ORDER BY visit_count DESC, p.last_name ASC"
        ),
        notes="Repeat visitors using HAVING.",
    ),
    SeedExample(
        question="Show unpaid invoices",
        sql=(
            "SELECT i.id, p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount, i.status "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') "
            "ORDER BY i.invoice_date DESC, i.id DESC"
        ),
        notes="Open receivables only.",
    ),
    SeedExample(
        question="What percentage of appointments are no-shows?",
        sql=(
            "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) "
            "AS no_show_percentage "
            "FROM appointments"
        ),
        notes="Percent of all appointments.",
    ),
    SeedExample(
        question="Show the busiest day of the week for appointments",
        sql=(
            "SELECT CASE strftime('%w', appointment_date) "
            "WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' "
            "WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' "
            "ELSE 'Saturday' END AS day_of_week, COUNT(*) AS appointment_count "
            "FROM appointments "
            "GROUP BY strftime('%w', appointment_date) "
            "ORDER BY appointment_count DESC "
            "LIMIT 1"
        ),
        notes="Day-of-week aggregation using SQLite date functions.",
    ),
    SeedExample(
        question="Revenue trend by month",
        sql=(
            "SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount), 2) AS revenue "
            "FROM invoices "
            "GROUP BY strftime('%Y-%m', invoice_date) "
            "ORDER BY month"
        ),
        notes="Monthly invoice revenue time series.",
    ),
]


BENCHMARK_QUESTIONS = [
    "How many patients do we have?",
    "List all doctors and their specializations",
    "Show me appointments for last month",
    "Which doctor has the most appointments?",
    "What is the total revenue?",
    "Show revenue by doctor",
    "How many cancelled appointments last quarter?",
    "Top 5 patients by spending",
    "Average treatment cost by specialization",
    "Show monthly appointment count for the past 6 months",
    "Which city has the most patients?",
    "List patients who visited more than 3 times",
    "Show unpaid invoices",
    "What percentage of appointments are no-shows?",
    "Show the busiest day of the week for appointments",
    "Revenue trend by month",
    "Average appointment duration by doctor",
    "List patients with overdue invoices",
    "Compare revenue between departments",
    "Show patient registration trend by month",
]


def normalize_question(question: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in question).split()
    )


def translate_question(question: str) -> Optional[str]:
    q = normalize_question(question)

    if "how many patients" in q:
        return SEED_EXAMPLES[0].sql
    if "list all doctors" in q and "specialization" in q:
        return SEED_EXAMPLES[1].sql
    if "appointments" in q and "last month" in q:
        return SEED_EXAMPLES[2].sql
    if "doctor" in q and "most appointments" in q:
        return SEED_EXAMPLES[3].sql
    if "total revenue" in q:
        return SEED_EXAMPLES[4].sql
    if "revenue by doctor" in q:
        return SEED_EXAMPLES[5].sql
    if "cancelled appointments" in q and "last quarter" in q:
        return SEED_EXAMPLES[6].sql
    if "top 5 patients" in q and "spending" in q:
        return SEED_EXAMPLES[7].sql
    if "average treatment cost" in q and "specialization" in q:
        return SEED_EXAMPLES[8].sql
    if "monthly appointment count" in q and "past 6 months" in q:
        return SEED_EXAMPLES[9].sql
    if "city" in q and "most patients" in q:
        return SEED_EXAMPLES[10].sql
    if "visited more than 3 times" in q or ("patients" in q and "more than 3 times" in q):
        return SEED_EXAMPLES[11].sql
    if "unpaid invoices" in q:
        return SEED_EXAMPLES[12].sql
    if "percentage" in q and "no show" in q:
        return SEED_EXAMPLES[13].sql
    if "busiest day" in q and "appointments" in q:
        return SEED_EXAMPLES[14].sql
    if "revenue trend by month" in q:
        return (
            "SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount), 2) AS revenue "
            "FROM invoices GROUP BY strftime('%Y-%m', invoice_date) ORDER BY month"
        )
    if "average appointment duration by doctor" in q:
        return (
            "SELECT d.name, ROUND(AVG(t.duration_minutes), 2) AS average_duration_minutes "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name "
            "ORDER BY average_duration_minutes DESC, d.name ASC"
        )
    if "patients with overdue invoices" in q or ("overdue invoices" in q and "patients" in q):
        return (
            "SELECT DISTINCT p.first_name, p.last_name, p.email, p.phone, i.invoice_date, i.total_amount, i.paid_amount "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status = 'Overdue' "
            "ORDER BY i.invoice_date DESC, p.last_name ASC"
        )
    if "compare revenue between departments" in q or ("revenue" in q and "departments" in q):
        return (
            "SELECT d.department, ROUND(SUM(t.cost), 2) AS total_revenue "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.department "
            "ORDER BY total_revenue DESC, d.department ASC"
        )
    if "patient registration trend by month" in q or ("registration trend" in q and "month" in q):
        return (
            "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS registrations "
            "FROM patients "
            "GROUP BY strftime('%Y-%m', registered_date) "
            "ORDER BY month"
        )

    return None
