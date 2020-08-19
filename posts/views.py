from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import PostForm, CommentForm
from .models import Post, Group

User = get_user_model()


def page_not_found(request, exception):
    return render(request, 'misc/404.html', {'path': request.path}, status=404)


def server_error(request):
    return render(request, 'misc/500.html', status=500)


# @cache_page(20)
def index(request):
    post_list = Post.objects.all().select_related('author', 'group').prefetch_related('comments')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'index.html', {'page': page, 'paginator': paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all().select_related('author', 'group').prefetch_related('comments')
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
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all().select_related('author', 'group').prefetch_related('comments')

    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)

    return render(request, 'profile.html', {
        'page': page,
        'author': author,
        'paginator': paginator
    })


def post_view(request, username, post_id):
    post = get_object_or_404(
        Post.objects.select_related('author', 'group').
        prefetch_related('comments__author'),
        author__username=username, pk=post_id
    )

    return render(request, 'post.html', {
        'post': post,
        'author': post.author,
        'form': CommentForm()
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


def add_comment(request, username, post_id):
    post = get_object_or_404(Post, author__username=username, pk=post_id)

    form = CommentForm(request.POST or None)

    if form.is_valid():
        form.instance.author = request.user
        form.instance.post = post
        form.save()

    return redirect('post', username=post.author.username, post_id=post.pk)
