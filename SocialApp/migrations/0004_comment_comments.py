# Generated by Django 4.1 on 2023-04-15 06:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SocialApp', '0003_likecommentrelation_likeimagerelation_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='comments',
            field=models.IntegerField(default=0),
        ),
    ]
