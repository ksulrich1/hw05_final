# Generated by Django 2.2.19 on 2022-11-20 10:18

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('posts', '0007_folow'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Folow',
            new_name='Follow',
        ),
    ]
