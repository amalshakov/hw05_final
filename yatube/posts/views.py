from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post


def paginate_page(request, queryset):
    paginator = Paginator(queryset, settings.POSTS_ON_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):
    """Главная страница"""
    posts = Post.objects.select_related('group', 'author')
    context = {
        'page_obj': paginate_page(request, posts),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Страница c постами, отфильтрованная по группам"""
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('group', 'author')
    context = {
        'group': group,
        'page_obj': paginate_page(request, posts),
    }
    return render(request, 'posts/group_list.html', context)


User = get_user_model()


def profile(request, username):
    """Профиль автора"""
    author = get_object_or_404(User, username=username)
    posts = author.posts_author.select_related('author', 'group')
    following = (
        request.user.is_authenticated
        and author.following.filter(user=request.user).exists()
    )
    context = {
        'author': author,
        'page_obj': paginate_page(request, posts),
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = post.comments.select_related('author')
    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        form.save()
        return redirect('posts:profile', request.user)
    return render(request, 'posts/create_post.html', {'form': form})


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post.id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('posts:post_detail', post.id)
    context = {
        'form': form,
        'is_edit': True,
        'post_id': post_id
    }
    return render(request, 'posts/create_post.html', context)


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


@login_required
def follow_index(request):
    """Страница с постами авторов на которых подписан текущий пользователь."""
    posts = Post.objects.filter(author__following__user=request.user)
    context = {'page_obj': paginate_page(request, posts)}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Подписаться на автора."""
    following = get_object_or_404(User, username=username)
    already_follows = Follow.objects.filter(
        user=request.user,
        author=following,
    ).exists()
    if not already_follows and request.user != following:
        Follow.objects.create(
            user=request.user,
            author=following,
        )
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    """Отписаться от автора."""
    following = get_object_or_404(User, username=username)
    Follow.objects.filter(
        user=request.user,
        author=following,
    ).delete()
    return redirect('posts:profile', username=username)
