# Generated by Django 5.1.1 on 2024-10-25 08:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Agriskill', '0009_remove_forms_profession'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='forms',
            name='state',
        ),
    ]
