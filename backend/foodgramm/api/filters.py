import django_filters
from recipe.models import Recipe, Ingredient


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(field_name='author__id')
    is_in_shopping_cart = django_filters.NumberFilter(
        method='check_shopping_cart'
    )
    author = django_filters.NumberFilter(field_name='author__id')
    is_favorited = django_filters.NumberFilter(method='check_favorite')

    def check_favorite(self, qs, field_name, value):
        current_user = self.request.user
        if value and current_user.is_authenticated:
            return qs.filter(favorites__user=current_user)
        return qs

    def check_shopping_cart(self, qs, field_name, value):
        if value and self.request.user.is_authenticated:
            return qs.filter(shoppingcarts__user=self.request.user)
        return qs

    class Meta:
        model = Recipe
        fields = ['author', 'is_favorited', 'is_in_shopping_cart']


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ['name']
