from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post

User = get_user_model()


def page_not_found(request, exception):
    return render(request, 'misc/404.html', {'path': request.path}, status=404)


def server_error(request):
    return render(request, 'misc/500.html', status=500)


@cache_page(20)
def index(request):
    post_list = Post.objects.select_related('author', 'group').prefetch_related('comments').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'index.html', {'page': page, 'paginator': paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related('author', 'group').prefetch_related('comments').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'group.html', {
        'page': page,
        'paginator': paginator
    })


@login_required
def new_post(request):
    form = PostForm(request.POST or None, files=request.FILES or None)

    if form.is_valid():
        form.instance.author = request.user
        form.save()
        return redirect('index')

    return render(request, 'new_post.html', {'form': form})


def profile(request, username):
    author = get_object_or_404(
        User.objects.prefetch_related('posts', 'following', 'follower'),
        username=username
    )
    post_list = author.posts.select_related('author', 'group').prefetch_related('comments').all()

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    if request.user.is_anonymous:
        following = False
    else:
        following = (Follow.objects.filter(user=request.user, author=author).count() > 0)

    return render(request, 'profile.html', {
        'page': page,
        'author': author,
        'paginator': paginator,
        'following': following
    })


def post_view(request, username, post_id):
    post = get_object_or_404(
        Post.objects.select_related('author', 'group'),
        author__username=username, pk=post_id
    )

    comments = post.comments.select_related('author').all()

    return render(request, 'post.html', {
        'post': post,
        'author': post.author,
        'form': CommentForm(),
        'comments': comments
    })


def post_edit(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)

    if request.user != post.author:
        return redirect('post', username=username, post_id=post_id)

    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)

    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)

    return render(request, 'new_post.html', {'form': form, 'post': post})


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)

    form = CommentForm(request.POST or None)

    if form.is_valid():
        form.instance.author = request.user
        form.instance.post = post
        form.save()

    return redirect('post', username=username, post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user). \
        select_related('author', 'group').prefetch_related('comments').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'follow.html', {'page': page, 'paginator': paginator})


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    is_exist = Follow.objects.filter(user=request.user, author=author).exists()
    if author != request.user and not is_exist:
        Follow.objects.create(user=request.user, author=author)

    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()

    return redirect('profile', username=username)
