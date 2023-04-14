from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from ..models import Group, Post


User = get_user_model()

GROUP_SLUG = "test-slug"
AUTHOR_USERNAME = "test_user"


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.no_author = User.objects.create_user(username="no_author")
        cls.group = Group.objects.create(
            title="Тестовый заголовок",
            slug=GROUP_SLUG,
            description="Тестовый текст",
        )
        cls.post = Post.objects.create(
            author=cls.author, group=cls.group, text="Тестовый текст"
        )
        cls.URL_POST_DETAIL = reverse("posts:post_detail", args=[cls.post.id])
        cls.URL_POST_EDIT = reverse("posts:post_edit", args=[cls.post.id])
        cls.URL_ADD_COMMENT = reverse("posts:add_comment",
                                      args=[cls.post.id])
        cls.private_urls = {
            "/create/": "posts/post_create.html",
            f"/posts/{cls.post.id}/edit/": "posts/post_create.html",
        }
        cls.public_urls = {
            "": "posts/index.html",
            f"/posts/{cls.post.id}/": "posts/post_detail.html",
            f"/profile/{AUTHOR_USERNAME}/": "posts/profile.html",
            f"/group/{GROUP_SLUG}/": "posts/group_list.html",
        }

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(PostURLTests.author)
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(PostURLTests.no_author)

    def test_page_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        for address, _ in self.public_urls.items():
            with self.subTest(adress=address):
                response = self.client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)
        for address, _ in self.private_urls.items():
            with self.subTest(adress=address):
                response = self.author_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_redirect_anonymous(self):
        """Страница post_edit перенаправляет анонимного пользователя."""
        response = self.client.get(PostURLTests.URL_POST_EDIT)
        self.assertRedirects(
            response, (f"/auth/login/?next={PostURLTests.URL_POST_EDIT}")
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_comment_url_redirect_anonymous(self):
        """Комментарии доступны только авторизованному пользователю."""
        response = self.client.get(PostURLTests.URL_ADD_COMMENT)
        self.assertRedirects(
            response, (f"/auth/login/?next={PostURLTests.URL_ADD_COMMENT}")
        )

    def test_no_author_of_post_cant_edit_post(self):
        """Страница posts/<post_id>/edit/ не доступна
        авторизованному пользователю, но не автору поста"""
        response = self.authorized_client_1.get(PostURLTests.URL_POST_EDIT)
        self.assertRedirects(response, PostURLTests.URL_POST_DETAIL)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unknown_page_url_unexists_at_desired_location(self):
        """Страница не существует"""
        response = self.client.get("/none/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        test_urls = {**self.public_urls, **self.private_urls}
        for url, template in test_urls.items():
            with self.subTest(url=url):
                response = self.author_client.get(url)
                self.assertTemplateUsed(
                    response,
                    template,
                    f"Неверный шаблон {template} для url {url}",
                )
