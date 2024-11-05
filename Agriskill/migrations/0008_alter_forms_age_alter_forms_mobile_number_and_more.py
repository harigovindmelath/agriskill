# Generated by Django 5.1.1 on 2024-10-17 16:16

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Agriskill', '0007_alter_forms_age'),
    ]

    operations = [
        migrations.AlterField(
            model_name='forms',
            name='age',
            field=models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='forms',
            name='mobile_number',
            field=models.CharField(max_length=20, unique=True, validators=[django.core.validators.RegexValidator('^\\+?1?\\d{9,15}$')]),
        ),
        migrations.AlterField(
            model_name='forms',
            name='total_area',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]