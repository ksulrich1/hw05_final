from django import forms

from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("text", "group", "image")
        names = {
            "text": "Текст поста",
            "group": "Группа",
        }
        extra_names = {
            "text": "Текст нового поста",
            "group": "Группа, к которой будет относиться пост",
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ("text", )
