from django.contrib import admin
from django.utils.safestring import mark_safe
from recipe.models import (
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    Favorite,
    ShoppingCart
)


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

    def lookups(self, request, model_admin):
        cooking_times = Recipe.objects.all().values_list(
            'cooking_time', flat=True
        )
        if cooking_times:
            sorted_times = sorted(cooking_times)
            count_recipes = len(sorted_times)
            first_quartile = sorted_times[count_recipes // 4]
            third_quartile = sorted_times[(3 * count_recipes) // 4]
        else:
            first_quartile, third_quartile = 10, 30  # значения по умолчанию

        medium_count = Recipe.objects.filter(
            cooking_time__lte=third_quartile
        ).exclude(cooking_time__lte=first_quartile).count()

        return (
            ('fast', f'Быстрее {first_quartile} мин ({Recipe.objects.
             filter(cooking_time__lte=first_quartile).count()})'),
            ('medium', f'Быстрее {third_quartile} мин ({medium_count})'),
            ('slow', f'Долго ({Recipe.objects.
             filter(cooking_time__gt=third_quartile).count()})'),
        )

    def queryset(self, request, queryset):
        cooking_times = Recipe.objects.all().values_list(
            'cooking_time', flat=True
        )
        if not cooking_times:
            return queryset

        sorted_times = sorted(cooking_times)
        count_recipes = len(sorted_times)
        first_quartile = sorted_times[count_recipes // 4]
        third_quartile = sorted_times[(3 * count_recipes) // 4]

        if self.value() == 'fast':
            return queryset.filter(cooking_time__lte=first_quartile)
        if self.value() == 'medium':
            return queryset.filter(
                cooking_time__gt=first_quartile,
                cooking_time__lte=third_quartile
            )
        if self.value() == 'slow':
            return queryset.filter(cooking_time__gt=third_quartile)


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
