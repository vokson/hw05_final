# Generated by Django 2.2.9 on 2020-08-18 03:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0015_auto_20200818_0645'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, error_messages={'invalid': 'Загружаемый файл должен быть изображением', 'invalid_image': 'Попытка загрузки некорректного файла изображения'}, help_text='Добавьте красивую картинку', null=True, upload_to='posts/', verbose_name='Изображение'),
        ),
    ]
