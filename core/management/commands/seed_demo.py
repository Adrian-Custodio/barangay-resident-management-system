"""
Fills an empty database with fictional data for the public online demo.
Every name here is made up; nothing is taken from real barangay records.
Safe to re-run: existing rows are matched and updated, not duplicated.
"""
import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Profile
from core.models import Official
from residents.models import Resident

DEMO_USERS = [
    ("demo_admin", Profile.Role.ADMIN),
    ("demo_encoder", Profile.Role.ENCODER),
]

# (resident_id, first, middle, last, suffix, birth_date, sex, civil_status, purok)
RESIDENTS = [
    ("R-0001", "Juan", "Santos", "Dela Cruz", "Jr.", "1985-03-14", "M", "MARRIED", "Purok 1"),
    ("R-0002", "Maria", "Lopez", "Dela Cruz", "", "1988-07-02", "F", "MARRIED", "Purok 1"),
    ("R-0003", "Jose", "Ramos", "Bautista", "", "1972-11-23", "M", "WIDOWED", "Purok 2"),
    ("R-0004", "Ana", "Reyes", "Villanueva", "", "1999-01-30", "F", "SINGLE", "Purok 2"),
    ("R-0005", "Pedro", "Garcia", "Mendoza", "", "1965-05-09", "M", "MARRIED", "Purok 3"),
    ("R-0006", "Rosa", "Aquino", "Mendoza", "", "1968-09-17", "F", "MARRIED", "Purok 3"),
    ("R-0007", "Mark Anthony", "Cruz", "Navarro", "", "2001-12-05", "M", "SINGLE", "Purok 4"),
    ("R-0008", "Kristine", "Diaz", "Fernandez", "", "1995-04-21", "F", "SEPARATED", "Purok 4"),
    ("R-0009", "Ramon", "Torres", "Castillo", "Sr.", "1958-08-11", "M", "MARRIED", "Purok 5"),
    ("R-0010", "Liza", "Morales", "Santiago", "", "1992-02-14", "F", "SINGLE", "Purok 5"),
    ("R-0011", "Carlo", "Flores", "Domingo", "", "1990-06-28", "M", "MARRIED", "Purok 6"),
    ("R-0012", "Jenny", "Pascual", "Salazar", "", "2003-10-03", "F", "SINGLE", "Purok 6"),
]

# (name, position, category, display_order)
OFFICIALS = [
    ("Hon. Roberto M. Agustin", "Punong Barangay", Official.Category.ELECTED, 0),
    ("Hon. Teresa L. Ocampo", "Kagawad", Official.Category.ELECTED, 1),
    ("Hon. Nestor P. Lim", "Kagawad", Official.Category.ELECTED, 2),
    ("Hon. Gloria S. Rivera", "Kagawad", Official.Category.ELECTED, 3),
    ("Hon. Daniel C. Tan", "SK Chairperson", Official.Category.ELECTED, 4),
    ("Marites D. Robles", "Barangay Secretary", Official.Category.APPOINTED, 0),
    ("Edgar V. Soriano", "Barangay Treasurer", Official.Category.APPOINTED, 1),
]


class Command(BaseCommand):
    help = "Seed fictional demo users, residents, and officials."

    def handle(self, *args, **options):
        password = settings.DEMO_PASSWORD
        User = get_user_model()
        for username, role in DEMO_USERS:
            user, _ = User.objects.get_or_create(username=username)
            user.set_password(password)
            user.save()
            Profile.objects.update_or_create(user=user, defaults={"role": role})

        for rid, first, middle, last, suffix, born, sex, civil, purok in RESIDENTS:
            Resident.objects.update_or_create(
                resident_id=rid,
                defaults={
                    "first_name": first,
                    "middle_name": middle,
                    "last_name": last,
                    "suffix": suffix,
                    "birth_date": datetime.date.fromisoformat(born),
                    "sex": sex,
                    "civil_status": civil,
                    "address": f"{purok}, Barangay Demo",
                    "purok_or_sitio": purok,
                    "is_active": True,
                },
            )

        for name, position, category, order in OFFICIALS:
            Official.objects.update_or_create(
                name=name,
                defaults={"position": position, "category": category, "display_order": order},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(DEMO_USERS)} demo users, {len(RESIDENTS)} residents, "
            f"{len(OFFICIALS)} officials."
        ))
