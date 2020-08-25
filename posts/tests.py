import os
import shutil
from io import BytesIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Comment, Follow, Group, Post

User = get_user_model()


@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media_test'))
class TestPost(TestCase):
    @classmethod
    def setUpTestData(self):
        self.authorized_client_1 = Client()
        self.authorized_client_2 = Client()
        self.user_1 = User.objects.create_user(username='test_user_1')
        self.user_2 = User.objects.create_user(username='test_user_2')
        self.authorized_client_1.force_login(self.user_1)
        self.authorized_client_2.force_login(self.user_2)

        self.unauthorized_client = Client()

        self.group = Group.objects.create(title='TEST_COMMUNITY_1', slug='test_community_1')
        self.group_test_edit = Group.objects.create(
            title='TEST_COMMUNITY_2', slug='test_community_2'
        )

        self.img_name = 'test_image.jpg'
        self.image = self.get_image_file(self.img_name)

        self.urls = {
            'new_post': reverse('new_post'),
            'index': reverse('index'),
            'login': reverse('login'),
            'profile': reverse('profile', args=[self.user_1.username]),
            'group_posts_1': reverse('group_posts', args=[self.group.slug]),
            'group_posts_2': reverse('group_posts', args=[self.group_test_edit.slug])
        }

    def setUp(self):
        cache.clear()
        try:
            shutil.rmtree(os.path.join(settings.BASE_DIR, 'media_test'))
        except OSError:
            pass

    @staticmethod
    def get_image_file(name):
        file_obj = BytesIO()
        image = Image.new('RGB', (100, 100), (255, 0, 0))
        image.save(file_obj, 'JPEG')
        return File(file_obj, name=name)

    def test_profile(self):
        response = self.unauthorized_client.get(self.urls['profile'])
        self.assertEqual(response.status_code, 200)

    def test_new_post_with_authorized_user(self):
        response = self.authorized_client_1.post(
            self.urls['new_post'],
            {
                'group': self.group.pk,
                'text': 'TEST_TEXT_AUTHORIZED',
                'image': SimpleUploadedFile(self.img_name, self.image.file.getvalue())
            },
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        self.compare_post_attributes(
            Post.objects.first(),
            self.user_1,
            self.group,
            'TEST_TEXT_AUTHORIZED',
            f'posts/{self.img_name}'
        )

    def test_new_post_with_unauthorized_user(self):
        url_new_post = self.urls['new_post']
        url_login = self.urls['login']
        response = self.unauthorized_client.post(
            url_new_post,
            {'group': self.group.pk, 'text': 'TEST_TEXT_UNATHORIZED'}
        )

        self.assertRedirects(response, f'{url_login}?next={url_new_post}')
        self.assertEqual(Post.objects.count(), 0)

    def test_is_post_published(self):
        post = Post.objects.create(group=self.group, author=self.user_1, text='TEST_TEXT')

        urls = [
            self.urls['index'],
            self.urls['profile'],
            self.urls['group_posts_1'],
            reverse('post', args=[self.user_1.username, post.id])
        ]

        self.check_post_attributes(urls, self.group, 'TEST_TEXT')

    def test_post_edit_with_authorized_user(self):
        post = Post.objects.create(group=self.group, author=self.user_1, text='TEST_TEXT')

        response = self.authorized_client_1.post(
            reverse('post_edit', args=[self.user_1.username, post.id]),
            {'group': self.group_test_edit.pk, 'text': 'TEST_TEXT_EDITED'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        self.compare_post_attributes(
            Post.objects.first(),
            self.user_1,
            self.group_test_edit,
            'TEST_TEXT_EDITED'
        )

    def test_post_edit_is_published(self):
        post = Post.objects.create(group=self.group, author=self.user_1, text='TEST_TEXT')
        post.group = self.group_test_edit
        post.text = 'TEST_TEXT_EDITED'
        post.save()

        urls = [
            self.urls['index'],
            self.urls['profile'],
            self.urls['group_posts_2'],
            reverse('post', args=[self.user_1.username, post.id])
        ]

        self.check_post_attributes(urls, self.group_test_edit, 'TEST_TEXT_EDITED')

    def check_post_attributes(self, urls, correct_group, correct_text, correct_img=None):
        for url in urls:
            with self.subTest(url=url):
                response = self.unauthorized_client.get(url)
                ctx = response.context
                if ctx.get('paginator') is not None and ctx.get('page') is not None:
                    self.assertEqual(ctx['paginator'].count, 1)
                    post = ctx['page'][0]
                else:
                    post = ctx['post']

                self.compare_post_attributes(
                    post,
                    self.user_1,
                    correct_group,
                    correct_text,
                    correct_img
                )

    def compare_post_attributes(self, post, author, group, text, img=None):
        self.assertEqual(post.author, author)
        self.assertEqual(post.group, group)
        self.assertEqual(post.text, text)
        if img is not None:
            self.assertEqual(post.image, img)

    def test_check_404(self):
        response = self.unauthorized_client.get('/404/')
        self.assertEqual(response.status_code, 404)

    def test_is_post_with_picture_published(self):
        post = Post.objects.create(
            group=self.group, author=self.user_1, text='TEST_TEXT', image=self.image
        )

        urls = [
            self.urls['index'],
            self.urls['profile'],
            self.urls['group_posts_1'],
            reverse('post', args=[self.user_1.username, post.id])
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.unauthorized_client.get(url)
                self.assertContains(response, '<img', 1, 200)

    def test_new_post_with_bad_picture_with_authorized_user(self):
        response = self.authorized_client_1.post(
            self.urls['new_post'],
            {
                'group': self.group.pk,
                'text': 'TEST_TEXT_AUTHORIZED',
                'image': SimpleUploadedFile(self.img_name, b'WRONG_FILE', 'image/jpeg')
            },
            follow=True
        )

        error_text = 'Загрузите правильное изображение. ' \
            'Файл, который вы загрузили, поврежден или не является изображением.'

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response,
            'form',
            'image',
            error_text
        )

    def test_cached_index_page(self):
        Post.objects.create(group=self.group, author=self.user_1, text='TEST_TEXT_1')
        response = self.unauthorized_client.get(self.urls['index'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paginator'].count, 1)
        self.assertIsNotNone(response.context['page'])
        self.compare_post_attributes(
            response.context['page'][0],
            self.user_1,
            self.group,
            'TEST_TEXT_1'
        )
        cached_content = response.content

        Post.objects.create(group=self.group, author=self.user_1, text='TEST_TEXT_2')
        response = self.unauthorized_client.get(self.urls['index'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, cached_content)

        cache.clear()

        response = self.unauthorized_client.get(self.urls['index'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['paginator'].count, 2)

    def test_authorized_user_may_subscribe(self):
        response = self.authorized_client_1.get(
            reverse('profile_follow', args=[self.user_2.username]), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), 1)
        follow = Follow.objects.first()
        self.assertEqual(follow.user, self.user_1)
        self.assertEqual(follow.author, self.user_2)

    def test_authorized_user_may_unsubscribe(self):
        Follow.objects.create(user=self.user_1, author=self.user_2)

        response = self.authorized_client_1.get(
            reverse('profile_unfollow', args=[self.user_2.username]), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Follow.objects.count(), 0)

    def test_following_post_is_published_for_subscribed_users(self):
        Follow.objects.create(user=self.user_1, author=self.user_2)
        Post.objects.create(group=None, author=self.user_2, text='TEST_TEXT', image=self.image)

        response = self.authorized_client_1.get(reverse('follow_index'))
        self.assertIsNotNone(response.context['paginator'])
        self.assertEqual(response.context['paginator'].count, 1)
        self.assertIsNotNone(response.context['page'])
        self.compare_post_attributes(
            response.context['page'][0],
            self.user_2,
            None,
            'TEST_TEXT',
            f'posts/{self.img_name}'
        )

    def test_following_post_is_not_published_for_unsubscribed_users(self):
        Post.objects.create(group=None, author=self.user_2, text='TEST_TEXT', image=self.image)

        response = self.authorized_client_1.get(reverse('follow_index'))
        self.assertIsNotNone(response.context['paginator'])
        self.assertEqual(response.context['paginator'].count, 0)

    def test_authorized_user_may_comment(self):
        post = Post.objects.create(author=self.user_1, text='TEST_TEXT')
        response = self.authorized_client_1.post(
            reverse('add_comment', args=[self.user_1.username, post.pk]),
            {'text': 'COMMENT_TEXT'}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 1)

        comment = Comment.objects.first()
        self.assertEqual(comment.author, self.user_1)
        self.assertEqual(comment.post, post)
        self.assertEqual(comment.text, 'COMMENT_TEXT')

    def test_unauthorized_user_may_not_comment(self):
        post = Post.objects.create(author=self.user_1, text='TEST_TEXT')
        response = self.unauthorized_client.post(
            reverse('add_comment', args=[self.user_1.username, post.pk]),
            {'text': 'COMMENT_TEXT'}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 0)
