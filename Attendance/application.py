from datetime import timedelta, date

def get_weekdays(start_date: date, end_date: date):
    current_date = start_date
    weekdays = []

    while current_date <= end_date:
        if current_date.weekday() < 7:  # 0 = Monday, ..., 4 = Friday
            weekdays.append(current_date)
        current_date += timedelta(days=1)

    return weekdays

def get_weekday(level):
    if level == 0:
        return "Monday"
    elif level == 1:
        return "Tuesday"
    elif level == 2:
        return "Wednesday"
    elif level == 3:
        return "Thursday"
    elif level == 4:
        return "Friday"
    elif level == 5:
        return "Saturday"
    else:
        return "Sunday"

def get_student_current_lessons(student_id):
    lessons = []
    return lessons

def get_student_current_present(student_id):
    percentage = 0
    return percentage

