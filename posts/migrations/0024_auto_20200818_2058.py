# Generated by Django 2.2.9 on 2020-08-18 17:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0023_auto_20200818_1923'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, help_text='Добавьте красивую картинку', null=True, upload_to='posts/', verbose_name='Изображение'),
        ),
    ]
