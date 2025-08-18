import os
import random
import requests
import tempfile
from django.core.management.base import BaseCommand #type: ignore
from django.core.files import File #type: ignore
from django.utils import timezone #type: ignore
from datetime import date

from Core.models import Branch, AcademicYear, Intake, Sponsor, Course
from Students.models import Application, Student

from .schools import *
from .addresses import *
from .names import *
from .generateemail import *

class Command(BaseCommand):
    help = "Generate random students records with unique names, IDs, phones, and matching-gender images."

    def handle(self, *args, **kwargs):
        # ===============================
        # SETTINGS
        # ===============================
        total_students_to_create = 1

        religions = ["Christianity", "Islam", "Hinduism", "Traditional"]
        exams = ["KCPE", "KCSE", "Certificate", "Diploma"]
        
        # Related objects
        branches = list(Branch.objects.all())
        year = AcademicYear.objects.order_by("?").first()
        sponsor = Sponsor.objects.order_by("?").first()
        intakes = list(Intake.objects.all())
        courses = list(Course.objects.all())

        # Track used name combinations, nat_ids, and phones
        used_names = set()
        used_nat_ids = set()
        used_phones = set()

        # ===============================
        # Helper: Generate nat_id
        # ===============================
        def generate_nat_id():
            while True:
                nat_id = str(random.randint(10**7, 10**8 - 1))  # 8 digits
                if len(set(nat_id)) > 1 and nat_id not in used_nat_ids:  # not all same digit & unique
                    used_nat_ids.add(nat_id)
                    return nat_id

        # ===============================
        # Helper: Generate phone number
        # ===============================
        def generate_phone():
            while True:
                phone = "7" + str(random.randint(10**7, 10**8 - 1))  # 9 digits, starts with 7
                if len(set(phone)) > 1 and phone not in used_phones:  # not all same digit & unique
                    used_phones.add(phone)
                    return phone

        # === Helper: download image based on gender ===
        def download_passport(gender, index):
            url = f"https://randomuser.me/api/portraits/{'men' if gender == 'Male' else 'women'}/{random.randint(0, 99)}.jpg"
            img_data = requests.get(url).content

            # Create a cross-platform temporary file path
            tmp_dir = tempfile.gettempdir()
            img_temp_path = os.path.join(tmp_dir, f"passport_{index}.jpg")

            with open(img_temp_path, "wb") as f:
                f.write(img_data)

            return img_temp_path
        
        def download_certificate(examtype, index):
            url = f"https://placehold.co/400x600?text={examtype}+Certificate+{index}"
            img_data = requests.get(url).content
            tmp_path = os.path.join(tempfile.gettempdir(), f"{examtype}_{index}.jpg")
            with open(tmp_path, "wb") as f:
                f.write(img_data)
            return tmp_path
        
        used_emails = set()

        # ===============================
        # STUDENT CREATION
        # ===============================
        Application.objects.all().delete()
        Student.objects.all().delete()
        for branch in branches:
            for course in courses:
                students_to_create = random.randint(20, 45)
                for i in range(1, students_to_create + 1):
                    gender = random.choice(["Male", "Female"])

                    # Ensure unique (fname, mname, sname)
                    while True:

                        if gender == "Male":
                            fname = random.choice(male_first_names)
                            mname = random.choice(male_middle_names)
                        else:
                            fname = random.choice(female_first_names)
                            mname = random.choice(female_middle_names)

                        sname = random.choice(surnames)
                        
                        if (fname, mname, sname) not in used_names:
                            used_names.add((fname, mname, sname))
                            break

                    # Guardian relationship logic
                    male_relationships = ["Father", "Uncle", "Brother"]
                    female_relationships = ["Mother", "Aunt", "Sister"]

                    if random.choice([True, False]):  # Randomly decide guardian gender
                        g_relationship = random.choice(male_relationships)
                        g_fname = random.choice(male_first_names)
                    else:
                        g_relationship = random.choice(female_relationships)
                        g_fname = random.choice(female_first_names)

                    g_lname = random.choice(surnames)

                    # Random DOB between 1985–2010
                    dob_year = random.randint(1985, 2010)
                    dob = date(dob_year, random.randint(1, 12), random.randint(1, 28))

                    # Exam type + school + grade logic
                    examtype = random.choice(exams)
                    current_year = date.today().year
                    if examtype == "KCPE":
                        prev_schoolname = random.choice(primary_schools)
                        examgrade = str(random.randint(290, 460))
                        examyear = dob.year + random.randint(13, 15)

                    elif examtype == "KCSE":
                        prev_schoolname = random.choice(secondary_schools)
                        examgrade = random.choice(["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+"])
                        examyear = dob.year + random.randint(17, 20)

                    else:  # Certificate/Diploma
                        prev_schoolname = random.choice(technical_schools)
                        examgrade = random.choice(["Credit", "Distinction", "Pass"])
                        examyear = current_year - random.randint(1, 5)

                    # Ensure examyear is not in the future
                    if examyear > current_year:
                        examyear = current_year
                        
                    passport_path = download_passport(gender, i)# Download certificate based on exam type
                    certificate_path = download_certificate(examtype, i)

                    application = Application.objects.create(
                        fname=fname,
                        mname=mname,
                        sname=sname,
                        gender=gender,
                        nat_id=generate_nat_id(),
                        phone=generate_phone(),
                        email=generate_unique_email(fname, mname, sname, used_emails),
                        branch=branch,
                        religion=random.choice(religions),
                        course=course,
                        phy_addr=random.choice(physical_addresses),
                        home_addr=random.choice(home_addresses),

                        guardian_fname=g_fname,
                        guardian_lname=g_lname,
                        guardian_email=generate_unique_email(g_fname, "", g_lname, used_emails),
                        guardian_phone=generate_phone(),
                        guardian_relationship=g_relationship,
                        
                        prev_schoolname=prev_schoolname,
                        examgrade=examgrade,
                        examtype=examtype,
                        examyear=examyear,

                        sponsor=sponsor,
                        year = year,
                        intake = random.choice(intakes),
                        dob=timezone.now().replace(year=1980 + random.randint(0, 25)),
                    )

                    # Open the downloaded image as a Django File so ImageField saves it correctly
                    with open(passport_path, "rb") as img_file:
                        application.passport.save(
                            f"{fname}_{mname[0]}_{sname}.jpg",
                            File(img_file),
                            save=True
                        )

                        # Save exam certificate image
                    with open(certificate_path, "rb") as cert_file:
                        application.previousexams.save(
                            f"{examtype}_{fname}_{sname}.jpg",
                            File(cert_file),
                            save=True
                        )


                    total_students_to_create += 1

        print(f"✅ Created {total_students_to_create} unique students records with passports, random nat_ids, and random phones.")