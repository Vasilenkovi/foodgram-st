from django.contrib import admin
from recipe.models import (
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    Favorite,
    ShoppingCart
)


@admin.register(Ingredient)
class Ingredient_Admin(admin.ModelAdmin):
    list_display = ("pk", "name", "measurement_unit")
    search_fields = ("name",)


class Ingredient_In_Recipe_Inline(admin.TabularInline):
    model = IngredientsInRecipe
    min_num = 1


@admin.register(Recipe)
class Recipe_Admin(admin.ModelAdmin):
    list_display = ("pk", "name", "author", "get_favorites", "created_at")
    search_fields = ("name", "author__username", "author__email")
    inlines = [Ingredient_In_Recipe_Inline]

    @admin.display(description="Добавлений рецепта в избранное")
    def get_favorites(self, obj):
        return obj.favorites.count()


@admin.register(IngredientsInRecipe)
class IngredientsInRecipe(admin.ModelAdmin):
    list_display = ("pk", "recipe", "ingredient")


@admin.register(ShoppingCart)
class Shopping_Cart_Admin(admin.ModelAdmin):
    list_display = ("pk", "user", "recipe")


@admin.register(Favorite)
class Favorite_Admin(admin.ModelAdmin):
    list_display = ("pk", "user", "recipe")
