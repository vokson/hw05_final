# Generated by Django 2.2.9 on 2020-08-07 03:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0008_auto_20200807_0614'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='description',
            field=models.TextField(help_text='Опишите сообщество', verbose_name='Описание'),
        ),
    ]
