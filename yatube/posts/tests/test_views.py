from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            group=cls.group,
            author=User.objects.create(username='testuser')
        )
        cls.group2 = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )

    def setUp(self):
        cache.clear()
        self.user = User.objects.get(username='testuser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.new_user = User.objects.create(username='testuser3')
        self.new_authorized_client = Client()
        self.new_authorized_client.force_login(self.new_user)

    def test_post_in_home(self):
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn(self.post, response.context['page_obj'])

    def test_post_in_group(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertIn(self.post, response.context['page_obj'])

    def test_post_in_profile(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.assertIn(self.post, response.context['page_obj'])

    def test_post_in_group(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group2.slug}))
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit', kwargs={'post_id': self.post.id}
            ): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def template_context(self, first_object):
        post_text_0 = first_object.text
        post_group_0 = first_object.group.title
        post_author_0 = first_object.author.username
        self.assertEqual(post_text_0, self.post.text)
        self.assertEqual(post_group_0, self.group.title)
        self.assertEqual(post_author_0, self.user.username)
        self.assertEqual(first_object.id, self.post.id)

    def test_post_list_page_show_correct_context(self):
        """Шаблон 'posts/index.html' сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.template_context(first_object)

    def test_group_list_page_show_correct_context(self):
        """Шаблон 'posts/group_list.html'
        сформирован с правильным контекстом.
        """
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        self.template_context(first_object)

        second_object = response.context['group']
        group_title = second_object.title
        group_slug = second_object.slug
        group_description = second_object.description
        self.assertEqual(group_title, self.group.title)
        self.assertEqual(group_slug, self.group.slug)
        self.assertEqual(group_description, self.group.description)
        self.assertEqual(second_object.id, self.group.id)

    def test_profile_list_page_show_correct_context(self):
        """Шаблон 'posts/profile.html' сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        first_object = response.context['page_obj'][0]
        self.template_context(first_object)

        second_object = response.context['author']
        author_username = second_object.username
        self.assertEqual(author_username, self.user.username)
        self.assertEqual(second_object.id, self.post.author.id)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон 'posts/post_detail.html'
        сформирован с правильным контекстом.
        """
        response = (self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})))
        first_object = response.context['post']
        self.template_context(first_object)

    def test_edit_page_show_correct_context(self):
        """Шаблон 'posts/create_post.html' (редактирование поста)
        сформирован с правильным контекстом.
        """
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_page_show_correct_context(self):
        """Шаблон 'posts/create_post.html' (создание поста)
        сформирован с правильным контекстом.
        """
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_work_cache(self):
        """Тестирование работы кэша."""
        initinal_response = self.authorized_client.get(reverse('posts:index'))
        Post.objects.get(id=self.post.id).delete()
        cached_response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(initinal_response.content, cached_response.content)
        cache.clear()
        new_response = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(initinal_response.content, new_response.content)

    def test_authorized_client_subscribe_on_authors(self):
        """Авторизованный пользователь может подписываться
        на других пользователей."""
        follow_count = Follow.objects.all().count()
        Post.objects.create(
            text='Тестовый пост2',
            group=self.group,
            author=User.objects.create(username='testuser2')
        )
        Follow.objects.create(
            user=User.objects.get(username='testuser'),
            author=User.objects.get(username='testuser2'),
        )
        self.assertEqual(Follow.objects.all().count(), follow_count + 1)

    def test_authorized_client_unsubscribe_on_authors(self):
        """Авторизованный пользователь может отписываться от пользователей."""
        follow_count = Follow.objects.all().count()
        Post.objects.create(
            text='Тестовый пост2',
            group=self.group,
            author=User.objects.create(username='testuser2')
        )
        Follow.objects.create(
            user=User.objects.get(username='testuser'),
            author=User.objects.get(username='testuser2'),
        )
        Follow.objects.filter(
            user=User.objects.get(username='testuser'),
            author=User.objects.get(username='testuser2'),
        ).delete()
        self.assertEqual(Follow.objects.all().count(), follow_count)

    def test_new_post_on_author_in_follower(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан."""
        Follow.objects.create(
            user=User.objects.get(username='testuser'),
            author=User.objects.create(username='testuser2'),
        )
        new_post = Post.objects.create(
            text='Тестовый пост2',
            group=self.group,
            author=User.objects.get(username='testuser2')
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertIn(new_post, response.context['page_obj'])

    def test_new_post_on_author_in_not_follower(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто на него не подписан."""
        Follow.objects.create(
            user=User.objects.get(username='testuser'),
            author=User.objects.create(username='testuser2'),
        )
        new_post = Post.objects.create(
            text='Тестовый пост2',
            group=self.group,
            author=User.objects.get(username='testuser2')
        )
        response = self.new_authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(new_post, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        author = User.objects.create(username='testuser')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        for i in range(13):
            Post.objects.create(
                text='Тестовый пост ' + str(i),
                group=cls.group,
                author=author
            )

    def setUp(self):
        cache.clear()
        self.user = User.objects.get(username='testuser')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(
            len(response.context['page_obj']),
            settings.POSTS_ON_PAGE
        )

    def test_index_second_page_contains_three_records(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']),
            Post.objects.all().count() - settings.POSTS_ON_PAGE
        )

    def test_group_list_first_page_contains_ten_records(self):
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertEqual(
            len(response.context['page_obj']),
            settings.POSTS_ON_PAGE
        )

    def test_group_list_second_page_contains_three_records(self):
        response = self.client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']),
            Post.objects.all().count() - settings.POSTS_ON_PAGE
        )

    def test_profile_first_page_contains_ten_records(self):
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        self.assertEqual(
            len(response.context['page_obj']),
            settings.POSTS_ON_PAGE
        )

    def test_profile_second_page_contains_three_records(self):
        response = self.client.get(
            reverse('posts:profile',
                    kwargs={'username': self.user.username}) + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']),
            Post.objects.all().count() - settings.POSTS_ON_PAGE
        )
