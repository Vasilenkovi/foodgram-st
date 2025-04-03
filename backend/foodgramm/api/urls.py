from django.urls import include, path
from rest_framework import routers

from api.views import UserViewSet, RecipeViewSet, IngredientViewSet

router = routers.SimpleRouter()
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")
router.register("users", UserViewSet, basename="users")

app_name = "api"

urlpatterns = [
    path("", include(router.urls)),
    path("", include("djoser.urls")),
    path("auth/", include("djoser.urls.authtoken")),
]