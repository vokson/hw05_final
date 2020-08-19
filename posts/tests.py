import os
import shutil
import time

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.cache import cache

from .models import Group, Post

User = get_user_model()


@override_settings(
    MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media', 'tests'),
    # CACHES={}
)
class TestPost(TestCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.authorized_client = Client()
        self.user = User.objects.create_user(username='test_user')
        self.authorized_client.force_login(self.user)

        self.unauthorized_client = Client()

        self.group = Group.objects.create(title='TEST_COMMUNITY_1', slug='test_community_1')
        self.group_test_edit = Group.objects.create(
            title='TEST_COMMUNITY_2', slug='test_community_2'
        )

        self.urls = {
            'new_post': reverse('new_post'),
            'index': reverse('index'),
            'login': reverse('login'),
            'profile': reverse('profile', args=[self.user.username]),
            'group_posts_1': reverse('group_posts', args=[self.group.slug]),
            'group_posts_2': reverse('group_posts', args=[self.group_test_edit.slug])
        }

    def tearDown(self):
        cache.clear()
        try:
            shutil.rmtree(os.path.join(settings.MEDIA_ROOT, 'posts'))
        except OSError:
            pass

    def test_profile(self):
        response = self.authorized_client.get(self.urls['profile'])
        self.assertEqual(response.status_code, 200)

    def test_new_post_with_authorized_user(self):
        response = self.authorized_client.post(
            self.urls['new_post'],
            {'group': self.group.pk, 'text': 'TEST_TEXT_AUTHORIZED'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        post = Post.objects.first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.text, 'TEST_TEXT_AUTHORIZED')

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
        post = Post.objects.create(group=self.group, author=self.user, text='TEST_TEXT')

        urls = [
            self.urls['index'],
            self.urls['profile'],
            self.urls['group_posts_1'],
            reverse('post', args=[self.user.username, post.id])
        ]

        self.check_post_attributes(urls, self.group, 'TEST_TEXT')

    def test_post_edit_with_authorized_user(self):
        post = Post.objects.create(group=self.group, author=self.user, text='TEST_TEXT')

        response = self.authorized_client.post(
            reverse('post_edit', args=[self.user.username, post.id]),
            {'group': self.group_test_edit.pk, 'text': 'TEST_TEXT_EDITED'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        post = Post.objects.first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group_test_edit)
        self.assertEqual(post.text, 'TEST_TEXT_EDITED')

    def test_post_edit_is_published(self):
        post = Post.objects.create(group=self.group, author=self.user, text='TEST_TEXT')
        post.group = self.group_test_edit
        post.text = 'TEST_TEXT_EDITED'
        post.save()

        urls = [
            self.urls['index'],
            self.urls['profile'],
            self.urls['group_posts_2'],
            reverse('post', args=[self.user.username, post.id])
        ]

        self.check_post_attributes(urls, self.group_test_edit, 'TEST_TEXT_EDITED')

    def check_post_attributes(self, urls, correct_group, correct_text, correct_img=None):
        for url in urls:
            response = self.unauthorized_client.get(url)
            ctx = response.context
            if ctx.get('paginator') is not None and ctx.get('page') is not None:
                self.assertEqual(ctx['paginator'].count, 1)
                post = ctx['page'][0]
            else:
                post = ctx['post']

            self.assertEqual(post.author, self.user)
            self.assertEqual(post.group, correct_group)
            self.assertEqual(post.text, correct_text)
            if correct_img is not None:
                self.assertEqual(post.image, correct_img)

    def test_check_404(self):
        response = self.authorized_client.get('/404/')
        self.assertEqual(response.status_code, 404)

    def test_is_post_with_picture_published(self):
        post = Post.objects.create(
            group=self.group, author=self.user, text='TEST_TEXT', image='input/test_image.jpg'
        )

        urls = [
            self.urls['index'],
            self.urls['profile'],
            self.urls['group_posts_1'],
            reverse('post', args=[self.user.username, post.id])
        ]

        self.check_post_attributes(urls, self.group, 'TEST_TEXT', 'input/test_image.jpg')

    def test_new_post_with_picture_with_authorized_user(self):
        with default_storage.open(os.path.join('input', 'test_image.jpg'), 'rb') as img:
            response = self.authorized_client.post(
                self.urls['new_post'],
                {'group': self.group.pk, 'text': 'TEST_TEXT_AUTHORIZED', 'image': img},
                follow=True
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)

        post = Post.objects.first()
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)
        self.assertEqual(post.text, 'TEST_TEXT_AUTHORIZED')
        self.assertEqual('posts/test_image.jpg', str(post.image))

    def test_new_post_with_bad_picture_with_authorized_user(self):
        with default_storage.open(os.path.join('input', 'non_picture.xlsx'), 'rb') as img:
            response = self.authorized_client.post(
                self.urls['new_post'],
                {'group': self.group.pk, 'text': 'TEST_TEXT_AUTHORIZED', 'image': img},
                follow=True
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 0)

    # @override_settings(CACHE_MIDDLEWARE_SECONDS=0)
    def test_cached_index_page(self):
        Post.objects.create(group=self.group, author=self.user, text='TEST_TEXT_1')
        response = self.authorized_client.get(self.urls['index'])
        self.assertEqual(response.context['paginator'].count, 1)

        self.assertNotEqual(cache.get('index_page', 'nothing'), 'nothing')

        # Post.objects.create(group=self.group, author=self.user, text='TEST_TEXT_2')
        # response = self.authorized_client.get(self.urls['index'])
        # self.assertEqual(response.context['paginator'].count, 1)

        # time.sleep(3)

        # response = self.authorized_client.get(self.urls['index'])
        # self.assertEqual(response.context['paginator'].count, 2)

    # def test_cache(self):
    #     cache.set('my_key', 'hello', 3)
    #     self.assertEqual(cache.get('my_key', 'expired'), 'hello')
    #     time.sleep(3)
    #     self.assertEqual(cache.get('my_key', 'expired'), 'expired')


