from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from posts.models import Group, Post, Follow
from .forms import PostForm, CommentForm

User = get_user_model()

POSTS_PER_PAGE = 10
CHARACTERS_FOR_POST = 30


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
    }
    return render(request, "posts/index.html", context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "group": group,
        "page_obj": page_obj,
    }
    return render(request, "posts/group_list.html", context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.all()
    context = {
        "post": post,
        "comments": comments,
        "form": CommentForm()
    }
    template = "posts/post_detail.html"
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    template = "posts/profile.html"
    posts = author.posts.all()
    user = request.user
    post_count = posts.count()
    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        "page_obj": page_obj,
        "author": author,
        "posts_count": post_count,
    }
    if user.is_authenticated:
        context['following'] = user.follower.filter(author=author).exists()
    return render(request, template, context)


@login_required
def post_create(request):
    template = "posts/post_create.html"
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect("posts:profile", request.user.username)
    context = {"form": form}
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect("posts:post_detail", post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None,
                    instance=post,
                    )
    if form.is_valid():
        form.save()
        return redirect("posts:post_detail", post_id)
    template = "posts/post_create.html"
    context = {
        "form": form,
        "is_edit": True,
    }
    return render(request, template, context)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, POSTS_PER_PAGE)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    if request.user.username == username:
        return redirect("posts:profile", username=username)
    following = get_object_or_404(User, username=username)
    already_follows = Follow.objects.filter(
        user=request.user,
        author=following
    ).exists()
    if not already_follows:
        Follow.objects.create(user=request.user, author=following)
    return redirect("posts:profile", username=username)


@login_required
def profile_unfollow(request, username):
    following = get_object_or_404(User, username=username)
    follower = get_object_or_404(Follow, author=following, user=request.user)
    follower.delete()
    return redirect("posts:profile", username=username)
