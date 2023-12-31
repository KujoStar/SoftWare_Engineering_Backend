# Generated by Django 4.1 on 2023-04-07 14:02

from django.db import migrations, models
import utils.utils_time


class Migration(migrations.Migration):

    dependencies = [
        ('ImagesApp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ImageCounter',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('hash', models.CharField(max_length=255, unique=True)),
                ('counter', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='ImageUploadRecord',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('hash', models.CharField(max_length=255)),
                ('uploader', models.CharField(max_length=255)),
                ('upload_time', models.FloatField(default=utils.utils_time.get_timestamp)),
            ],
        ),
        migrations.DeleteModel(
            name='GIFImage',
        ),
        migrations.AddIndex(
            model_name='imageuploadrecord',
            index=models.Index(fields=['id'], name='ImagesApp_i_id_4d2d8a_idx'),
        ),
        migrations.AddIndex(
            model_name='imagecounter',
            index=models.Index(fields=['id'], name='ImagesApp_i_id_9dad5d_idx'),
        ),
    ]
