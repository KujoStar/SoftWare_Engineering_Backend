# Generated by Django 4.1.3 on 2023-04-01 19:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('UsersApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='mail_code',
            field=models.CharField(default='', max_length=255, null=True),
        ),
    ]
