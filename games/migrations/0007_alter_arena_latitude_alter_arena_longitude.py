# Generated by Django 5.0.6 on 2024-06-03 23:50

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("games", "0006_team_franchise"),
    ]

    operations = [
        migrations.AlterField(
            model_name="arena",
            name="latitude",
            field=models.FloatField(blank=True, db_column="Latitude", null=True),
        ),
        migrations.AlterField(
            model_name="arena",
            name="longitude",
            field=models.FloatField(blank=True, db_column="Longitude", null=True),
        ),
    ]
