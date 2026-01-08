from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def register_view(request):
    if request.method == 'POST':
        full_name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'accounts/register.html')

        # Split full name into first and last name
        names = full_name.strip().split()
        first_name = names[0]
        last_name = " ".join(names[1:]) if len(names) > 1 else ''

        # Create user — set username as email for now
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        login(request, user)
        messages.success(request, f"Welcome, {first_name}!")
        return redirect('/')

    return render(request, 'accounts/register.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'accounts/login.html')

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect('/')
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "You’ve been logged out.")
    return redirect('/')
