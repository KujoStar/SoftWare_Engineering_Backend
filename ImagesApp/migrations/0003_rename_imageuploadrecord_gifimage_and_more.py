# Generated by Django 4.1 on 2023-04-07 17:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ImagesApp', '0002_imagecounter_imageuploadrecord_delete_gifimage_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ImageUploadRecord',
            new_name='GIFImage',
        ),
        migrations.RenameModel(
            old_name='ImageCounter',
            new_name='GIFImageCounter',
        ),
        migrations.RenameIndex(
            model_name='gifimage',
            new_name='ImagesApp_g_id_0b4686_idx',
            old_name='ImagesApp_i_id_4d2d8a_idx',
        ),
        migrations.RenameIndex(
            model_name='gifimagecounter',
            new_name='ImagesApp_g_id_367fb9_idx',
            old_name='ImagesApp_i_id_9dad5d_idx',
        ),
    ]
