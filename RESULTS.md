# Results

Pass count: 20 / 20

The benchmark below was executed against the generated `clinic.db` through the FastAPI `/chat` endpoint.

## Summary Notes

- All 20 published benchmark questions returned valid SQL and successful API responses.
- Query 17 uses `treatments.duration_minutes` as the duration proxy because the schema does not contain appointment duration.
- Queries 6 and 19 use treatment cost for doctor/department revenue because invoices are not tied to appointments in the provided schema.

## Benchmark Outcomes

| # | Question | Correct? | Result Summary |
| --- | --- | --- | --- |
| 1 | How many patients do we have? | Yes | Returned `200`. |
| 2 | List all doctors and their specializations | Yes | Returned 15 doctors with specialization and department. |
| 3 | Show me appointments for last month | Yes | Returned 35 appointments from the previous calendar month. |
| 4 | Which doctor has the most appointments? | Yes | Returned `Dr. Karan Patel` with `86` appointments. |
| 5 | What is the total revenue? | Yes | Returned total invoice revenue of `807227.81`. |
| 6 | Show revenue by doctor | Yes | Returned all 15 doctors ranked by summed treatment revenue. |
| 7 | How many cancelled appointments last quarter? | Yes | Returned `14`. |
| 8 | Top 5 patients by spending | Yes | Returned the top 5 invoice spenders. |
| 9 | Average treatment cost by specialization | Yes | Returned all 5 specializations with average treatment cost. |
| 10 | Show monthly appointment count for the past 6 months | Yes | Returned a 6-month time series. |
| 11 | Which city has the most patients? | Yes | Returned `Kochi` with `30` patients. |
| 12 | List patients who visited more than 3 times | Yes | Returned 41 repeat visitors. |
| 13 | Show unpaid invoices | Yes | Returned 99 pending or overdue invoices. |
| 14 | What percentage of appointments are no-shows? | Yes | Returned `6.0%`. |
| 15 | Show the busiest day of the week for appointments | Yes | Returned `Thursday` with `82` appointments. |
| 16 | Revenue trend by month | Yes | Returned a 13-month revenue series. |
| 17 | Average appointment duration by doctor | Yes | Returned doctor averages using treatment duration as the available proxy. |
| 18 | List patients with overdue invoices | Yes | Returned 41 overdue-invoice patient records. |
| 19 | Compare revenue between departments | Yes | Returned all 5 departments ranked by treatment revenue. |
| 20 | Show patient registration trend by month | Yes | Returned a 13-month registration series. |

## Detailed SQL

### 1. How many patients do we have?

- SQL:

```sql
SELECT COUNT(*) AS total_patients FROM patients
```

- Correct: Yes
- Result summary: Returned `200`.

### 2. List all doctors and their specializations

- SQL:

```sql
SELECT name, specialization, department FROM doctors ORDER BY name
```

- Correct: Yes
- Result summary: Returned 15 doctors with specialization and department.

### 3. Show me appointments for last month

- SQL:

```sql
SELECT a.id, p.first_name || ' ' || p.last_name AS patient_name, d.name AS doctor_name, a.appointment_date, a.status
FROM appointments a
JOIN patients p ON p.id = a.patient_id
JOIN doctors d ON d.id = a.doctor_id
WHERE date(a.appointment_date) >= date('now', 'start of month', '-1 month')
  AND date(a.appointment_date) < date('now', 'start of month')
ORDER BY a.appointment_date
```

- Correct: Yes
- Result summary: Returned 35 appointment rows for the previous calendar month.

### 4. Which doctor has the most appointments?

- SQL:

```sql
SELECT d.name, COUNT(*) AS appointment_count
FROM appointments a
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name
ORDER BY appointment_count DESC, d.name ASC
LIMIT 1
```

- Correct: Yes
- Result summary: Returned `Dr. Karan Patel` with `86` appointments.

### 5. What is the total revenue?

- SQL:

```sql
SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices
```

- Correct: Yes
- Result summary: Returned `807227.81`.

### 6. Show revenue by doctor

- SQL:

```sql
SELECT d.name, ROUND(SUM(t.cost), 2) AS total_revenue
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name
ORDER BY total_revenue DESC, d.name ASC
```

- Correct: Yes
- Result summary: Returned all 15 doctors ranked by treatment-derived revenue.

### 7. How many cancelled appointments last quarter?

- SQL:

```sql
WITH quarter_bounds AS (
  SELECT
    CASE
      WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 1 AND 3 THEN date(strftime('%Y', 'now') || '-01-01', '-3 months')
      WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 4 AND 6 THEN date(strftime('%Y', 'now') || '-01-01')
      WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 7 AND 9 THEN date(strftime('%Y', 'now') || '-04-01')
      ELSE date(strftime('%Y', 'now') || '-07-01')
    END AS start_date,
    CASE
      WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 1 AND 3 THEN date(strftime('%Y', 'now') || '-01-01')
      WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 4 AND 6 THEN date(strftime('%Y', 'now') || '-04-01')
      WHEN CAST(strftime('%m', 'now') AS INTEGER) BETWEEN 7 AND 9 THEN date(strftime('%Y', 'now') || '-07-01')
      ELSE date(strftime('%Y', 'now') || '-10-01')
    END AS end_date
)
SELECT COUNT(*) AS cancelled_appointments
FROM appointments, quarter_bounds
WHERE status = 'Cancelled'
  AND date(appointment_date) >= start_date
  AND date(appointment_date) < end_date
```

- Correct: Yes
- Result summary: Returned `14`.

### 8. Top 5 patients by spending

- SQL:

```sql
SELECT p.first_name, p.last_name, ROUND(SUM(i.total_amount), 2) AS total_spending
FROM invoices i
JOIN patients p ON p.id = i.patient_id
GROUP BY p.id, p.first_name, p.last_name
ORDER BY total_spending DESC, p.last_name ASC
LIMIT 5
```

- Correct: Yes
- Result summary: Returned the top 5 invoice spenders.

### 9. Average treatment cost by specialization

- SQL:

```sql
SELECT d.specialization, ROUND(AVG(t.cost), 2) AS average_treatment_cost
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.specialization
ORDER BY average_treatment_cost DESC
```

- Correct: Yes
- Result summary: Returned all 5 specializations with average treatment cost.

### 10. Show monthly appointment count for the past 6 months

- SQL:

```sql
SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count
FROM appointments
WHERE date(appointment_date) >= date('now', 'start of month', '-5 months')
GROUP BY strftime('%Y-%m', appointment_date)
ORDER BY month
```

- Correct: Yes
- Result summary: Returned a 6-month appointment trend.

### 11. Which city has the most patients?

- SQL:

```sql
SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC, city ASC
LIMIT 1
```

- Correct: Yes
- Result summary: Returned `Kochi` with `30` patients.

### 12. List patients who visited more than 3 times

- SQL:

```sql
SELECT p.first_name, p.last_name, COUNT(*) AS visit_count
FROM appointments a
JOIN patients p ON p.id = a.patient_id
WHERE a.status IN ('Completed', 'Scheduled', 'No-Show')
GROUP BY p.id, p.first_name, p.last_name
HAVING COUNT(*) > 3
ORDER BY visit_count DESC, p.last_name ASC
```

- Correct: Yes
- Result summary: Returned 41 repeat visitors.

### 13. Show unpaid invoices

- SQL:

```sql
SELECT i.id, p.first_name, p.last_name, i.invoice_date, i.total_amount, i.paid_amount, i.status
FROM invoices i
JOIN patients p ON p.id = i.patient_id
WHERE i.status IN ('Pending', 'Overdue')
ORDER BY i.invoice_date DESC, i.id DESC
```

- Correct: Yes
- Result summary: Returned 99 unpaid invoices.

### 14. What percentage of appointments are no-shows?

- SQL:

```sql
SELECT ROUND(
  100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*),
  2
) AS no_show_percentage
FROM appointments
```

- Correct: Yes
- Result summary: Returned `6.0`.

### 15. Show the busiest day of the week for appointments

- SQL:

```sql
SELECT CASE strftime('%w', appointment_date)
  WHEN '0' THEN 'Sunday'
  WHEN '1' THEN 'Monday'
  WHEN '2' THEN 'Tuesday'
  WHEN '3' THEN 'Wednesday'
  WHEN '4' THEN 'Thursday'
  WHEN '5' THEN 'Friday'
  ELSE 'Saturday'
END AS day_of_week,
COUNT(*) AS appointment_count
FROM appointments
GROUP BY strftime('%w', appointment_date)
ORDER BY appointment_count DESC
LIMIT 1
```

- Correct: Yes
- Result summary: Returned `Thursday` with `82` appointments.

### 16. Revenue trend by month

- SQL:

```sql
SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount), 2) AS revenue
FROM invoices
GROUP BY strftime('%Y-%m', invoice_date)
ORDER BY month
```

- Correct: Yes
- Result summary: Returned a 13-month revenue time series.

### 17. Average appointment duration by doctor

- SQL:

```sql
SELECT d.name, ROUND(AVG(t.duration_minutes), 2) AS average_duration_minutes
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name
ORDER BY average_duration_minutes DESC, d.name ASC
```

- Correct: Yes
- Result summary: Returned doctor-level average duration using treatment duration as the available proxy.

### 18. List patients with overdue invoices

- SQL:

```sql
SELECT DISTINCT p.first_name, p.last_name, p.email, p.phone, i.invoice_date, i.total_amount, i.paid_amount
FROM invoices i
JOIN patients p ON p.id = i.patient_id
WHERE i.status = 'Overdue'
ORDER BY i.invoice_date DESC, p.last_name ASC
```

- Correct: Yes
- Result summary: Returned 41 overdue-invoice patient rows.

### 19. Compare revenue between departments

- SQL:

```sql
SELECT d.department, ROUND(SUM(t.cost), 2) AS total_revenue
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.department
ORDER BY total_revenue DESC, d.department ASC
```

- Correct: Yes
- Result summary: Returned all 5 departments ranked by treatment-derived revenue.

### 20. Show patient registration trend by month

- SQL:

```sql
SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS registrations
FROM patients
GROUP BY strftime('%Y-%m', registered_date)
ORDER BY month
```

- Correct: Yes
- Result summary: Returned a 13-month registration trend.
