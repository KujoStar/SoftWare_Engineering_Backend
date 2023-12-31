# Generated by Django 4.1 on 2023-04-12 07:57

import django.contrib.postgres.fields
from django.db import migrations, models
import utils.utils_time


class Migration(migrations.Migration):

    dependencies = [
        ('ImagesApp', '0006_gifimage_category_gifimage_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('text', models.TextField(max_length=3000)),
                ('poster', models.CharField(max_length=255)),
                ('post_time', models.FloatField(default=utils.utils_time.get_timestamp)),
                ('likes', models.IntegerField(default=0)),
                ('reply_to_image', models.BigIntegerField()),
                ('reply_to_comment', models.BigIntegerField()),
                ('replies', django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(), default=list, size=None)),
            ],
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(fields=['id'], name='ImagesApp_c_id_644bad_idx'),
        ),
    ]
