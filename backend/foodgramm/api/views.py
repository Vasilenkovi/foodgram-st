from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from recipe.models import Recipe, ShoppingCart, IngredientsInRecipe, Favorite, Ingredient, Follow
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from .filters import IngredientFilter, RecipeFilter
from .permissions import IsAuthorOrReadOnly
from .pagination import PaginationLimiter

from .serializers import (
    FollowedUserSerializer, 
    RecipeSerializer, 
    AvatarSerializer, 
    IngredientSerializer, 
    RecipeMinifiedSerializer, 
    RecipeCreateUpdateSerializer
    )


User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    pagination_class = PaginationLimiter
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(methods=['get'], detail=False, permission_classes=[IsAuthenticated])
    def me(self, request):
        return super().me(request)

    @action(detail=False, url_path='me/avatar', methods=['put', 'delete'], permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        user = request.user
        subscriptions = User.objects.filter(authors_subs__follower=user)

        page = self.paginate_queryset(subscriptions)
        serializer = FollowedUserSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    def create_subscription(self, user, author, request):
        if user == author:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'detail': 'Нельзя подписаться на себя'})

        _, created = Follow.objects.get_or_create(follower=user, author=author)
        if not created:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'detail': 'Нельзя повторно подписаться на пользователя'})

        serializer = FollowedUserSerializer(
            author,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_subscription(self, user, author):
        get_object_or_404(Follow, follower=user, author=author).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            return self.create_subscription(user, author, request)

        return self.delete_subscription(user, author)


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = PaginationLimiter
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.action == 'create' or self.action == 'partial_update':
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def create_shopping_list(self, user):
        ingredients = IngredientsInRecipe.objects.filter(
            recipe__shoppingcarts__user=user
        ).values(
            'ingredient__name',
            'ingredient__measure_unit'
        ).annotate(total_number=Sum('number')).order_by('ingredient__name')

        recipes = Recipe.objects.filter(
            shoppingcarts__user=user
        )
        file_content = []
        date = timezone.now().strftime('%d-%m-%Y %H:%M')
        file_content.append(f'Список покупок на {date}\n')

        file_content.append('\nРецепты:')
        
        for recipe in recipes:
            file_content.append(f'- {recipe.name} (Автор: {recipe.author.username})')
        file_content.append('\nИнгредиенты:')
        for counter, ingredient in enumerate(ingredients, start=1):
            unit = ingredient['ingredient__measure_unit']
            number = ingredient['total_number']
            name = ingredient['ingredient__name'].capitalize()
            file_content.append(f'{counter}. {name} ({unit}) — {number}')

        file_content = '\n'.join(file_content)
        return file_content

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        response = FileResponse(
            self.create_shopping_list(request.user),
            as_attachment=True,
            filename='shopping_list.txt'
        )

        return response

    def add_recipe_to(self, user, recipe, model):
        obj, created = model.objects.get_or_create(user=user, recipe=recipe)
        if not created:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={'detail': 'Этот рецепт уже добавлен'})

        serializer = RecipeMinifiedSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def remove_recipe_from(self, user, recipe, model):
        get_object_or_404(model, user=user, recipe=recipe).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def update_recipe_in(self, request, user_id):
        user = request.user
        recipe = get_object_or_404(Recipe, id=user_id)
        model = Favorite if 'favorite' in request.path else ShoppingCart
        if request.method == 'POST':
            return self.add_recipe_to(user, recipe, model)
        return self.remove_recipe_from(user, recipe, model)

    @action(detail=True, methods=['post', 'delete'], permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self.update_recipe_in(request, pk)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart', permission_classes=(IsAuthenticated,))
    def shopping_cart(self, request, pk=None):
        return self.update_recipe_in(request, pk)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, id=pk)

        short_link = request.build_absolute_uri(
            reverse('redirect_to_recipe', kwargs={'recipe_id': recipe.pk})
        )

        return Response({"short-link": short_link}, status=status.HTTP_200_OK)
