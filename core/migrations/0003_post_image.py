# Generated by Django 4.2.10 on 2024-03-07 19:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_post_circles_alter_user_timezone"),
    ]

    operations = [
        migrations.AddField(
            model_name="post",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="images/"),
        ),
    ]