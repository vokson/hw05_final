import os
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Comment, Follow, Group, Post

User = get_user_model()


@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media', 'tests'))
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

    def test_cached_index_page(self):
        Post.objects.create(group=self.group, author=self.user, text='TEST_TEXT_1')
        response = self.authorized_client.get(self.urls['index'])
        self.assertContains(response, 'TEST_TEXT', 1, 200)

        Post.objects.create(group=self.group, author=self.user, text='TEST_TEXT_2')
        response = self.authorized_client.get(self.urls['index'])
        self.assertContains(response, 'TEST_TEXT', 1, 200)

        cache.clear()

        response = self.authorized_client.get(self.urls['index'])
        self.assertContains(response, 'TEST_TEXT', 2, 200)


@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media', 'tests'))
class TestFollow(TestCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.authorized_client_1 = Client()
        self.authorized_client_2 = Client()
        self.user_1 = User.objects.create_user(username='test_user_1')
        self.user_2 = User.objects.create_user(username='test_user_2')

        self.authorized_client_1.force_login(self.user_1)
        self.authorized_client_2.force_login(self.user_2)

    def test_authorized_user_may_subscribe(self):
        response = self.authorized_client_1.get(
            reverse('profile_follow', args=[self.user_2.username]), follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Follow.objects.filter(user=self.user_1, author=self.user_2).count(), 1)

    def test_authorized_user_may_unsubscribe(self):
        response = self.authorized_client_1.get(
            reverse('profile_follow', args=[self.user_2.username]), follow=True
        )
        self.assertEqual(response.status_code, 200)

        response = self.authorized_client_1.get(
            reverse('profile_unfollow', args=[self.user_2.username]), follow=True
        )
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Follow.objects.filter(user=self.user_1, author=self.user_2).count(), 0)

    def test_following_post_is_published_for_subscribed_users(self):
        Follow.objects.create(user=self.user_1, author=self.user_2)
        Post.objects.create(group=None, author=self.user_2, text='TEST_TEXT')

        response = self.authorized_client_1.get(reverse('follow_index'))
        post = response.context['page'][0]
        self.assertEqual(post.author, self.user_2)
        self.assertEqual(post.text, 'TEST_TEXT')


@override_settings(MEDIA_ROOT=os.path.join(settings.BASE_DIR, 'media', 'tests'))
class TestComment(TestCase):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.authorized_client = Client()
        self.unauthorized_client = Client()

        self.user = User.objects.create_user(username='test_user')
        self.authorized_client.force_login(self.user)

        self.post = Post.objects.create(author=self.user, text='TEST_TEXT')
        self.add_comment_url = reverse('add_comment', args=[self.user.username, self.post.pk])

    def test_authorized_user_may_comment(self):
        response = self.authorized_client.post(
            self.add_comment_url, {'text': 'COMMENT_TEXT'}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 1)

        comment = Comment.objects.first()
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(comment.text, 'COMMENT_TEXT')

    def test_unauthorized_user_may_not_comment(self):
        response = self.unauthorized_client.post(
            self.add_comment_url, {'text': 'COMMENT_TEXT'}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 0)
