from django.shortcuts import render

def homepage(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def resume(request):
    return render(request, 'resume.html')

def education(request):
    return render(request, 'education.html')

def projects(request):
    return render(request, 'projects.html')
