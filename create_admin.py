import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracker.settings')
django.setup()

from django.contrib.auth.models import User

email = 'help.pricetag@gmail.com'
password = 'pricetag@12345'

try:
    if not User.objects.filter(email=email).exists():
        print(f"Creating superuser: {email}")
        User.objects.create_superuser(username=email, email=email, password=password)
        print("Superuser created successfully!")
    else:
        print(f"User {email} already exists.")
        u = User.objects.get(email=email)
        if not u.is_superuser:
            print("Updating user to superuser...")
            u.is_superuser = True
            u.is_staff = True
            u.save()
            print("User updated to superuser.")
        else:
            print("User is already a superuser.")
            
except Exception as e:
    print(f"Error: {e}")
