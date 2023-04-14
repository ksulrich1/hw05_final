import shutil
import tempfile

from django import forms
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Group, Post, Follow
from ..views import POSTS_PER_PAGE

TEMP_NUMB_FIRST_PAGE: int = 13
TEMP_NUMB_SECOND_PAGE: int = 3

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username="TestAuthor")
        cls.group = Group.objects.create(
            title="test_title",
            description="test_description",
            slug="test-slug",
        )
        cls.second_group = Group.objects.create(
            title="test_title_2",
            description="test_description_2",
            slug="test-slug2",
        )
        cls.small_gif = (
            b"\x47\x49\x46\x38\x39\x61\x02\x00"
            b"\x01\x00\x80\x00\x00\x00\x00\x00"
            b"\xFF\xFF\xFF\x21\xF9\x04\x00\x00"
            b"\x00\x00\x00\x2C\x00\x00\x00\x00"
            b"\x02\x00\x01\x00\x00\x02\x02\x0C"
            b"\x0A\x00\x3B"
        )
        cls.post = Post.objects.create(
            text="test_post", author=cls.author,
            group=cls.group,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем авторизованный клиент
        self.user = User.objects.create_user(username="TestUser")
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.author_client = Client()
        self.author_client.force_login(PostPagesTests.author)

    # Проверяем используемые шаблоны
    def test_pages_use_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            reverse("posts:index"): "posts/index.html",
            reverse(
                "posts:group_list", kwargs={"slug": self.group.slug}
            ): "posts/group_list.html",
            reverse(
                "posts:profile",
                kwargs={"username": self.post.author.username},
            ): "posts/profile.html",
            reverse(
                "posts:post_edit", kwargs={"post_id": self.post.pk}
            ): "posts/post_create.html",
            reverse("posts:post_create"): "posts/post_create.html",
            reverse(
                "posts:post_detail", kwargs={"post_id": self.post.pk}
            ): "posts/post_detail.html",
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.author_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        self.uploaded = SimpleUploadedFile(
            name="small.image",
            content=self.small_gif,
            content_type="image/gif"
        )
        response = self.authorized_client.get(reverse("posts:index"))
        first_object = response.context["page_obj"][0]
        post_author = first_object.author
        post_text = first_object.text
        post_pub_date = first_object.pub_date
        image = first_object.image
        self.assertEqual(post_author, self.author)
        self.assertEqual(post_text, self.post.text)
        self.assertEqual(post_pub_date, self.post.pub_date)
        self.assertEqual(image, self.post.image)

    def test_group_list_page_shows_correct_context(self):
        response = self.authorized_client.get(
            reverse("posts:group_list", args=(self.group.slug,))
        )
        first_object = response.context["page_obj"][0]
        post_group = first_object.group
        self.assertEqual(post_group, self.group)

    def test_profile_page_shows_correct_context(self):
        response = self.authorized_client.get(
            reverse("posts:profile", args=[self.author.username])
        )
        first_object = response.context["page_obj"][0]
        post_author = first_object.author
        self.assertEqual(post_author, self.author)

    def test_post_detail_page_shows_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                "posts:post_detail", kwargs={"post_id": self.post.id}
            )
        )
        self.assertEqual(
            response.context["post"].text, self.post.text
        )
        self.assertEqual(
            response.context["post"].group, self.post.group
        )
        self.assertEqual(
            response.context["post"].author, self.post.author
        )
        self.assertEqual(
            response.context["post"].image, self.post.image,
        )

    def test_post_edit_page_shows_correct_context(self):
        """Шаблоны post_edit и create сформированы с правильным контекстом."""
        response = self.author_client.get(
            reverse(
                "posts:post_edit", kwargs={"post_id": self.post.id}
            )
        )
        form_fields = {
            "group": forms.models.ModelChoiceField,
            "text": forms.fields.CharField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse("posts:post_create"))
        form_fields = {
            "text": forms.fields.CharField,
            "group": forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get("form").fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_post_success_in_pages(self):
        """
        При создании поста, пост попадает на главную страницу, профайл и групп
        """
        form_data = {
            "text": "Тестовый текст (создание)",
            "group": PostPagesTests.group.pk,
        }
        post_count_in_second_group = (
            PostPagesTests.second_group.posts.count()
        )  # количество постов во второй группе до создания
        # поста в базе нет
        self.author_client.post(  # создали пост
            reverse("posts:post_create"), data=form_data, follow=True
        )
        # проверяем что пост в профайле
        profile_response = self.author_client.get(
            reverse("posts:profile", args=[self.author.username])
        )
        first_object = profile_response.context["page_obj"][0]
        self.assertEqual(first_object.text, "Тестовый текст (создание)")
        # проверяем что пост появился на главной
        index_response = self.author_client.get(reverse("posts:index"))
        first_object = index_response.context["page_obj"][0]
        self.assertEqual(first_object.text, "Тестовый текст (создание)")
        # проверяем что пост попал в группу
        group_response = self.author_client.get(
            reverse("posts:group_list", args=[self.group.slug])
        )
        first_object = group_response.context["page_obj"][0]
        self.assertEqual(first_object.text, "Тестовый текст (создание)")
        self.assertEqual(
            post_count_in_second_group,
            self.second_group.posts.count(),
        )

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        response = self.authorized_client.get(reverse("posts:index"))
        posts = response.content
        Post.objects.create(
            text="test_new_post",
            author=self.author,
        )
        response_old = self.authorized_client.get(reverse("posts:index"))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse("posts:index"))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username="NoName")
        cls.group = Group.objects.create(
            title="test_title",
            description="test_description",
            slug="test-slug",
        )
        objs = [
            Post(text=f"text{post_temp}", author=cls.author, group=cls.group)
            for post_temp in range(TEMP_NUMB_FIRST_PAGE)
        ]
        Post.objects.bulk_create(objs)

    def setUp(self):
        self.user_client = Client()

    def test_first_page_contains_ten_records(self):
        pages_address = [
            reverse("posts:index"),
            reverse("posts:group_list", kwargs={"slug": self.group.slug}),
            reverse(
                "posts:profile", kwargs={"username": self.author.username}
            ),
        ]
        for reverse_name in pages_address:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context["page_obj"]), POSTS_PER_PAGE
                )

    def test_second_page_contains_three_records(self):
        pages_address = [
            reverse("posts:index") + "?page=2",
            reverse("posts:group_list", kwargs={"slug": self.group.slug})
            + "?page=2",
            reverse("posts:profile", kwargs={"username": self.author})
            + "?page=2",
        ]
        for reverse_name in pages_address:
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertEqual(
                    len(response.context["page_obj"]), TEMP_NUMB_SECOND_PAGE
                )


class Test404Page(TestCase):
    def test_404page_use_correct_template(self):
        url_page = "/unexisting-page/"
        response = self.client.get(url_page)
        self.assertTemplateUsed(response, "core/404.html")


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = User.objects.create_user(username="test-author")
        cls.follower = User.objects.create_user(username="follower")
        cls.not_follower = User.objects.create_user(username="not_follower")

    def setUp(self) -> None:
        self.test_user_client = Client()
        self.test_user_client.force_login(FollowTests.test_user)
        self.follower_client = Client()
        self.follower_client.force_login(FollowTests.follower)
        self.not_follower_client = Client()
        self.not_follower_client.force_login(FollowTests.not_follower)

    def test_follow(self):
        """Авторизованный пользователь может
        подписываться на других пользователей"""
        user_to_follow = User.objects.create_user(username="user_to_follow")
        before = Follow.objects.count()
        self.test_user_client.get(
            reverse("posts:profile_follow", args=[user_to_follow, ])
        )
        self.assertEqual(Follow.objects.count(), before + 1)
        new_follow = Follow.objects.first()
        self.assertEqual(new_follow.author, user_to_follow)
        self.assertEqual(new_follow.user, self.test_user)

    def test_unfollow(self):
        """Авторизованный пользователь может отписываться"""
        user_to_follow = User.objects.create_user(username="user_to_follow")
        Follow.objects.create(
            author=user_to_follow,
            user=self.test_user
        )
        before = Follow.objects.count()
        self.test_user_client.get(
            reverse("posts:profile_unfollow", args=[user_to_follow, ])
        )
        self.assertEqual(before - 1, Follow.objects.count())

    def test_follow_index_show_correct_post(self):
        """Новая запись пользователя появляется в ленте тех, кто
        на него подписан и не появляется в ленте тех, кто не подписан."""
        Follow.objects.create(
            author=self.test_user,
            user=self.follower
        )
        Post.objects.create(
            text="test_one_post",
            author=self.test_user
        )
        response_not_follower = self.not_follower_client.get(
            reverse("posts:follow_index")
        )
        before_not_follower = len(response_not_follower.context["page_obj"])
        response_follower = self.follower_client.get(
            reverse("posts:follow_index")
        )
        before_follower = len(response_follower.context["page_obj"])
        Post.objects.create(
            text="test_one_post",
            author=self.test_user
        )
        response_not_follower = self.not_follower_client.get(
            reverse("posts:follow_index")
        )
        after_not_follower = len(response_not_follower.context["page_obj"])
        self.assertEqual(before_not_follower, after_not_follower)
        response_follower = self.follower_client.get(
            reverse("posts:follow_index")
        )
        after_follower = len(response_follower.context["page_obj"])
        self.assertEqual(before_follower, after_follower - 1)
