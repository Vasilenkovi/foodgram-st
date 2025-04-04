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
    path("auth/", include("djoser.urls.authtoken")),
    path(
        "recipes/<int:pk>/get-link/",
        RecipeViewSet.as_view({"get": "get_link"}),
        name="recipe-get-link"
    ),
]
