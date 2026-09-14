from datetime import date
from decimal import Decimal


OFFICIAL_WORKING_DAYS = Decimal("90")

def get_default_attendance_status(attendance_date):
    # Sunday
    if attendance_date.weekday() == 6:
        return "Weekend Holiday"

    # Second Saturday
    if attendance_date.weekday() == 5 and 8 <= attendance_date.day <= 14:
        return "Weekend Holiday"

    # All other days are normal working days
    return "Absent"


def calculate_attendance(attendance_records):
    """
    Calculate attendance using the college's 90-working-day rule.

    Present       = 1.0
    Half Day      = 0.5
    Absent        = 0
    Error         = 0
    Holiday       = excluded
    Weekend Holiday = excluded

    Extension days add to earned attendance but do not
    increase the official 90-day denominator.
    """

    present = 0
    half_day = 0
    absent = 0
    holiday = 0
    error = 0
    weekend_holiday = 0
    extension_days = 0

    earned_attendance = Decimal("0")

    for record in attendance_records:
        status = record.status

        if status == "Present":
            present += 1
            earned_attendance += Decimal("1")

        elif status == "Half Day":
            half_day += 1
            earned_attendance += Decimal("0.5")

        elif status == "Absent":
            absent += 1

        elif status == "Holiday":
            holiday += 1

        elif status == "Error":
            error += 1

        elif status == "Weekend Holiday":
            weekend_holiday += 1

        if record.is_extension_day:
            extension_days += 1

    working_days = (
        present
        + half_day
        + absent
        + error
        - extension_days
    )

    # Official denominator is always 90.
    percentage = (
        earned_attendance / OFFICIAL_WORKING_DAYS
    ) * Decimal("100")

    # Attendance can never exceed 100%.
    if percentage > Decimal("100"):
        percentage = Decimal("100")

    return {
        "present": present,
        "half_day": half_day,
        "absent": absent,
        "holiday": holiday,
        "error": error,
        "weekend_holiday": weekend_holiday,
        "working_days": working_days,
        "extension_days": extension_days,
        "earned_attendance": earned_attendance,
        "official_working_days": OFFICIAL_WORKING_DAYS,
        "percentage": percentage.quantize(Decimal("0.01")),
    }