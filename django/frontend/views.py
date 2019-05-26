from django.shortcuts import render


def handle404(request, exception):
    return render(request, "errors/404.html", locals())


def handle500(request):
    return render(request, "errors/500.html", locals())
