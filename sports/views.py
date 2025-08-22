from django.shortcuts import render


def index(request):
    return render(request, 'sports/index.html')
