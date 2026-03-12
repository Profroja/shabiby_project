from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('driver', 'Driver'),
        ('conductor', 'Conductor'),
        ('pickup', 'Pickup (Delivery)'),
        ('branch_agent', 'Branch Agent'),
    ]
    
    mobile_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='branch_agent')
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.username
