# Generated by Django 5.1.1 on 2024-10-25 08:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Agriskill', '0008_alter_forms_age_alter_forms_mobile_number_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forms',
            name='profession',
        ),
    ]
