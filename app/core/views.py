from django.shortcuts import render

def homepage(request):
    return render(request, 'core/index.html')

def about(request):
    return render(request, 'core/about.html')

def resume(request):
    return render(request, 'core/resume.html')

def education(request):
    return render(request, 'core/education.html')

def projects(request):
    return render(request, 'core/projects.html')
