import django_filters
from recipe.models import Recipe, Ingredient


class RecipeFilter(django_filters.FilterSet):
    author = django_filters.NumberFilter(field_name='author__id')
    is_liked = django_filters.NumberFilter(method='filter_is_liked')
    added_to_cart = django_filters.NumberFilter(method='filter_added_to_cart')

    def filter_is_liked(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorite__user=user)
        return queryset

    def filter_added_to_cart(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shoppingcart__user=user)
        return queryset

    class Meta:
        model = Recipe
        fields = ['author']


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ['name']
