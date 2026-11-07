from django.shortcuts import render

def home(request):
    return render(request, 'myapp/home.html')

def reserva(request):
    return render(request, 'myapp/reserva.html')