import os
import random
import requests
import tempfile
from django.core.management.base import BaseCommand #type: ignore
from django.core.files import File #type: ignore
from django.utils import timezone #type: ignore

from Core.models import Branch, Department
from Staff.models import Staff
from Core.application import generate_password
from Core.models import User, UserProfile, Group

class Command(BaseCommand):
    help = "Generate random staff records with unique names, IDs, phones, and matching-gender images."

    def handle(self, *args, **kwargs):
        # ===============================
        # SETTINGS
        # ===============================
        total_staff_to_create = random.randint(40, 65)

        # Name pools
        male_first_names = [
            "James", "Peter", "John", "David", "Michael", "Daniel", "Samuel", "Joseph", "George", "Paul",
            "Anthony", "Brian", "Kevin", "Robert", "Stephen", "Kennedy", "Francis", "Dennis", "Martin", "Simon"
        ]

        female_first_names = [
            "Mary", "Grace", "Anne", "Jane", "Susan", "Lucy", "Esther", "Hannah", "Elizabeth", "Margaret",
            "Victoria", "Sarah", "Rebecca", "Naomi", "Clara", "Linda", "Eunice", "Agnes", "Caroline", "Mercy"
        ]

        male_middle_names = [
            "Mwangi", "Njoroge", "Otieno", "Kamau", "Maina", "Omondi", "Kipkorir", "Kimutai", "Langat", "Korir",
            "Kosgei", "Cheruiyot", "Mutua", "Kimani", "Njuguna", "Wafula", "Oduor", "Were", "Barasa", "Muli"
        ]

        female_middle_names = [
            "Wanjiku", "Atieno", "Chebet", "Cherono", "Chepchumba", "Wairimu", "Nyambura", "Mutisya", "Eunice",
            "Nafula", "Achieng", "Anyango", "Naliaka", "Nanjala", "Wambui", "Mwende", "Makena", "Kanini", "Syombua", "Nyawira"
        ]

        # Surnames (gender-neutral or traditionally male-based)
        surnames = [
            "Kamau", "Otieno", "Kariuki", "Mutiso", "Kiptoo", "Onyango", "Njuguna", "Barasa",
            "Cheruiyot", "James", "Victor", "Koech", "Kiprotich", "Rono", "Langat", "Korir", "Ochieng", "Okoth", "Ouma", "Wafula", "Mwangi", "Maina"
        ]

        # Related objects
        branches = list(Branch.objects.all())
        departments = list(Department.objects.all())

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

        # ===============================
        # STAFF CREATION
        # ===============================
        Staff.objects.all().delete()
        User
        for i in range(1, total_staff_to_create + 1):
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

            passport_path = download_passport(gender, i)

            staff = Staff.objects.create(
                regno=f"JI/{i:03}/STF/EDU",
                fname=fname,
                mname=mname,
                sname=sname,
                gender=gender,
                nat_id=generate_nat_id(),
                phone=generate_phone(),
                email=f"{fname.lower()}.{sname.lower()}@jiedu.com",
                branch=random.choice(branches),
                department=random.choice(departments),
                weekly_hours=random.randint(15, 30),
                dob=timezone.now().replace(year=1980 + random.randint(0, 25)),
                state="Active"
            )

            # Open the downloaded image as a Django File so ImageField saves it correctly
            with open(passport_path, "rb") as img_file:
                staff.passport.save(
                    f"{staff.regno}.jpg",
                    File(img_file),
                    save=True
                )


            # Generate a unique username
            username = staff.regno or staff.email.split('@')[0]

            # Generate a secure password
            password = generate_password()

            # Create the user
            user = User.objects.create_user(
                username=username, password=password,
                first_name=staff.fname, last_name=staff.sname,
                email=staff.email, is_active=True
            )
            user.save()

            userprofile = UserProfile.objects.create(
                user = user, picture = staff.passport,
                phone = staff.phone, branch = staff.branch
            )
            userprofile.save()

            staff.user = userprofile
            staff.save()

            # Assign user to closest matching group (e.g., "Staff" or "Class Tutor")
            group = Group.objects.filter(name__icontains="Lecturer").first()
            if group:
                user.groups.add(group)


        print(f"✅ Created {total_staff_to_create} unique staff records with passports, random nat_ids, and random phones.")
