from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from recipe.models import Recipe


def redirect_short_link(request, pk):
    get_object_or_404(Recipe, id=pk)
    return redirect(f'/recipes/{pk}/')
