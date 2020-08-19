from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField('Сообщество', max_length=200, blank=False, unique=True)
    slug = models.SlugField(
        max_length=50, unique=True, null=False, blank=False
    )
    description = models.TextField('Описание', help_text='Дайте описание сообществу..')

    def __str__(self) -> str:
        return str(self.title)


class Post(models.Model):
    text = models.TextField('Текст', help_text='Напишите здесь то, чем хотите поделиться..')
    pub_date = models.DateTimeField('Дата публикации', auto_now_add=True)
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='posts', verbose_name='Автор',
        help_text='Выберите автора'
    )
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='posts', verbose_name='Сообщество', help_text='Выберите сообщество'
    )
    image = models.ImageField(
        upload_to='posts/', blank=True, null=True,
        verbose_name='Изображение', help_text='Добавьте красивую картинку'
    )

    class Meta:
        ordering = ['-pub_date']

    def __str__(self) -> str:
        short_text = self.text[:10]
        author_name = str(self.author)
        return f'{author_name}: {short_text}'


class Comment(models.Model):
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='comments',
        verbose_name='Запись', help_text='Выберите запись'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='comments',
        verbose_name='Автор', help_text='Выберите автора'
    )
    text = models.TextField('Текст', help_text='Напишите здесь свой комментарий..')
    created = models.DateTimeField('Дата публикации', auto_now_add=True)

    class Meta:
        ordering = ['-created']

    def __str__(self) -> str:
        short_text = self.text[:10]
        author_name = str(self.author)
        return f'{author_name}: {short_text}'
