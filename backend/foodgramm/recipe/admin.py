from django.contrib import admin
from django.utils.safestring import mark_safe
from recipe.models import (
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    Favorite,
    ShoppingCart
)
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "measurement_unit", "get_recipe_count")
    search_fields = ("name",)

    @admin.display(description="Используется в рецептах")
    def get_recipe_count(self, obj):
        return obj.ingredients_in_recipe.count()


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientsInRecipe
    min_num = 1


class CookingTimeFilter(admin.SimpleListFilter):
    title = 'Время приготовления'
    parameter_name = 'cooking_time'
    first_quartile = None
    third_quartile = None

    def lookups(self, request, model_admin):
        cooking_times = list(Recipe.objects.values_list(
            'cooking_time', flat=True
        ))
        if not cooking_times:
            return ()

        sorted_times = sorted(cooking_times)
        count_recipes = len(sorted_times)
        self.first_quartile = sorted_times[count_recipes // 4]
        self.third_quartile = sorted_times[(3 * count_recipes) // 4]

        medium_count = sum(
            self.first_quartile < time <= self.third_quartile
            for time in cooking_times
        )

        return (
            ('fast', f'Быстрее {
                self.first_quartile} мин ({sum(
                    t <= self.first_quartile for t in cooking_times
                )
            })'),
            ('medium', f'Быстрее {self.third_quartile} мин ({medium_count})'),
            ('slow', f'Долго ({sum(
                t > self.third_quartile for t in cooking_times
            )})'),
        )

    def queryset(self, request, queryset):
        if not self.first_quartile or not self.third_quartile:
            return queryset

        if self.value() == 'fast':
            return queryset.filter(cooking_time__lte=self.first_quartile)
        if self.value() == 'medium':
            return queryset.filter(
                cooking_time__gt=self.first_quartile,
                cooking_time__lte=self.third_quartile
            )
        if self.value() == 'slow':
            return queryset.filter(cooking_time__gt=self.third_quartile)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "cooking_time",
        "author",
        "get_favorites",
        "get_ingredients_list",
        "get_image_preview",
        "created_at",
    )
    search_fields = ("name", "author__username", "author__email")
    list_filter = ("author", CookingTimeFilter)
    inlines = [IngredientInRecipeInline]

    @admin.display(description="В избранном")
    def get_favorites(self, obj):
        return obj.favorites.count()

    @admin.display(description="Ингредиенты")
    def get_ingredients_list(self, obj):
        ingredients = [
            f"{ing.ingredient.name} - {ing.amount} "
            f"{ing.ingredient.measurement_unit}"
            for ing in obj.ingredients_in_recipe.all()
        ]
        return mark_safe("<br>".join(ingredients))

    @admin.display(description="Изображение")
    def get_image_preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" style="max-height: 100px;">'
            )
        return "Нет изображения"


@admin.register(IngredientsInRecipe)
class IngredientsInRecipeAdmin(admin.ModelAdmin):
    list_display = ("pk", "recipe", "ingredient")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "recipe")


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "recipe")
