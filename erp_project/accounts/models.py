from django.db import models


class AppUser(models.Model):
    """
    Temporary, self-contained user record.

    This exists ONLY because the real user/auth system will eventually be
    provided by an external website via API. Once that API is wired in,
    `external_id` is what will link this record (or replace it) to the
    user coming from that system. Until then, this model + the session
    based "login as" flow in views.py is a stand-in so we can build and
    test role-based behavior right now.

    ROLE_CHOICES intentionally starts with just 'admin'. Add new roles
    here one at a time as they're built (e.g. 'developer', 'qa') rather
    than adding all of them up front.
    """

    ROLE_CHOICES = [
        ('admin',     'Administrator'),
        ('developer', 'Developer'),
        ('qa',        'QA'),
        ('business_analyst',  'Business Analyst'),
    ]

    name        = models.CharField(max_length=150)
    role        = models.CharField(max_length=30, choices=ROLE_CHOICES)
    external_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID of this user on the external site, once that API integration exists.")
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"