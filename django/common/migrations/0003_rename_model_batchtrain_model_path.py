# Generated by Django 4.1.5 on 2023-02-04 20:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0002_batchtrain'),
    ]

    operations = [
        migrations.RenameField(
            model_name='batchtrain',
            old_name='model',
            new_name='model_path',
        ),
    ]