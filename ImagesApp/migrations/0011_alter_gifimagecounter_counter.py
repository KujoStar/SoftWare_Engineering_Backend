# Generated by Django 4.1 on 2023-04-12 16:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ImagesApp', '0010_delete_comment'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gifimagecounter',
            name='counter',
            field=models.IntegerField(default=1),
        ),
    ]
