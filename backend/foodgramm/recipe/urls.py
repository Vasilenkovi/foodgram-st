from django.urls import path
from recipe.views import redirect_short_link

app_name = "recipe"

urlpatterns = [
    path('s/<int:pk>/', redirect_short_link, name='recipe_short_link')
]
