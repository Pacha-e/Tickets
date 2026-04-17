from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages


def registro(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Bienvenido, {user.username}. ¡Tu cuenta fue creada!')
            return redirect('home')
    else:
        form = UserCreationForm()

    return render(request, 'auth/registro.html', {'form': form})
