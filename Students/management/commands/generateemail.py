import random
import string

def generate_unique_email(fname, mname, sname, used_emails):
    patterns = [
        f"{fname.lower()}.{mname.lower()}@gmail.com",
        f"{sname.lower()}.{fname.lower()}@gmail.com",
        f"{fname.lower()}.{sname.lower()}@gmail.com",
        f"{fname.lower()}{random.randint(10, 9999)}@gmail.com",
        f"{fname.lower()}{mname.lower()}{random.randint(10, 9999)}@gmail.com",
        f"{fname.lower()}{random.choice(string.ascii_lowercase)}{sname.lower()}@gmail.com",
    ]
    
    # Shuffle patterns to randomize choice
    random.shuffle(patterns)
    
    for email in patterns:
        if email not in used_emails:
            used_emails.add(email)
            return email
    
    # Fallback in case of collision
    while True:
        email = f"{fname.lower()}{random.randint(1, 99999)}@gmail.com"
        if email not in used_emails:
            used_emails.add(email)
            return email