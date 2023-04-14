import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from ..models import Post, Group, Comment
from ..forms import PostForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_post_author = User.objects.create_user(username="test-author")
        cls.test_comment_author = User.objects.create_user(
            username='test-comment-author')
        cls.test_group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Описание группы",
        )
        cls.test_post = Post.objects.create(
            author=cls.test_post_author,
            group=cls.test_group,
            text="Тестовый пост",
        )
        cls.form = PostForm()
        cls.TEST_COMMENT_URL = reverse(
            'posts:add_comment',
            args=[cls.test_post.id]
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.author_client = Client()
        self.author_client.force_login(self.test_post_author)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded_gif = SimpleUploadedFile(
            name="small.gif",
            content=small_gif,
            content_type="image/gif"
        )
        form_data = {
            "text": "Тестовый текст",
            "group": self.test_group.pk,
            'image': uploaded_gif,
        }

        response = self.author_client.post(
            reverse("posts:post_create"), data=form_data, follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                args=(self.test_post_author.username,)
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text=form_data['text']).exists())

    def test_edit_post_success(self):
        posts_count = Post.objects.count()
        form_data = {
            "text": "Новый тестовый текст",
            "group": self.test_group.pk,
        }

        response = self.author_client.post(
            reverse("posts:post_edit", args=[self.test_post.pk]),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse("posts:post_detail", args=[self.test_post.pk]),
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter
                        (text=form_data['text']).exists())


class CommentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='comment')
        cls.post = Post.objects.create(
            text='Текст поста',
            author=cls.user,
        )
        cls.comment_url = reverse('posts:add_comment', args=['1'])

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_authorized_client_comment(self):
        """Авторизированный пользователь может оставлять комментарии"""
        text_comment = 'Kомментарий'
        self.authorized_client.post(self.comment_url,
                                    data={'text': text_comment}
                                    )
        comment = Comment.objects.get(id=self.post.id)
        self.assertEqual(comment.text, text_comment)
        self.assertEqual(Comment.objects.count(), 1)

    def test_guest_client_comment_redirect_login(self):
        """Неавторизированный пользователь не может оставлять комментарии"""
        count_comments = Comment.objects.count()
        self.client.post(CommentTests.comment_url)
        self.assertEqual(count_comments, Comment.objects.count())
