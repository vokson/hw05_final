# Generated by Django 2.2.9 on 2020-08-08 15:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0011_auto_20200807_0623'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='description',
            field=models.TextField(help_text='Дайте описание сообществу..', verbose_name='Описание'),
        ),
    ]
