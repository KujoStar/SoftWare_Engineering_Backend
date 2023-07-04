# Generated by Django 4.1 on 2023-04-12 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ImagesApp', '0008_remove_gifimagecounter_imagesapp_g_id_367fb9_idx_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='comment',
            old_name='text',
            new_name='content',
        ),
        migrations.AddField(
            model_name='comment',
            name='reply_to_user',
            field=models.CharField(default=str, max_length=255),
        ),
        migrations.AlterField(
            model_name='comment',
            name='reply_to_comment',
            field=models.BigIntegerField(default=-1),
        ),
        migrations.AlterField(
            model_name='gifimage',
            name='description',
            field=models.TextField(default=str, max_length=3000),
        ),
    ]
