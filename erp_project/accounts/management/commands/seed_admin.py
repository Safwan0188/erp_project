from django.core.management.base import BaseCommand
from accounts.models import AppUser


class Command(BaseCommand):
    help = 'Create a default Administrator AppUser so there is someone to "log in as" immediately.'

    def handle(self, *args, **kwargs):
        user, created = AppUser.objects.get_or_create(
            name='Admin',
            defaults={'role': 'admin', 'is_active': True}
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created default admin user: {user.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"Admin user already exists: {user.name}"))