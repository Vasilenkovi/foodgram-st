from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Sum
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipe.models import (
    Recipe,
    ShoppingCart,
    IngredientsInRecipe,
    Favorite,
    Ingredient,
    Follow
)
from .filters import IngredientFilter, RecipeFilter
from .pagination import PaginationLimiter
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AvatarSerializer,
    FollowedUserSerializer,
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeMinifiedSerializer,
    RecipeSerializer
)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    pagination_class = PaginationLimiter
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        requester = request.user
        subs = User.objects.filter(authors_subs__follower=requester)
        page = self.paginate_queryset(subs)
        context_serializer = FollowedUserSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(context_serializer.data)

    @action(methods=['get'], detail=False,
            permission_classes=[IsAuthenticated]
            )
    def me(self, request):
        return super().me(request)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated]
            )
    def subscribe(self, request, id=None):
        current_user = request.user
        target_user = get_object_or_404(User, id=id)

        if request.method == 'POST':
            return self.handle_subscription_create(current_user,
                                                   target_user, request
                                                   )
        return self.handle_subscription_delete(current_user, target_user)

    def handle_subscription_create(self, follower, author, req):
        if follower == author:
            return Response(
                {'errors': 'Нельзя подписаться на себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        _, created = Follow.objects.get_or_create(
            follower=follower,
            author=author
        )

        if not created:
            return Response(
                {'errors': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serialized = FollowedUserSerializer(author, context={'request': req})
        return Response(serialized.data, status=status.HTTP_201_CREATED)

    def handle_subscription_delete(self, follower, author):
        try:
            sub = get_object_or_404(
                Follow,
                follower=follower,
                author=author
            )
            sub.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        except Http404:
            return Response(
                {"errors": "Подписка не найдена"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, url_path='me/avatar',
            methods=['put', 'delete'],
            permission_classes=[IsAuthenticated]
            )
    def avatar(self, request):
        profile = request.user

        if request.method == 'PUT':
            avatar_serializer = AvatarSerializer(profile, data=request.data)
            avatar_serializer.is_valid(raise_exception=True)
            avatar_serializer.save()
            return Response(avatar_serializer.data)
        profile.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    pagination_class = PaginationLimiter
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ['create', 'partial_update']:
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def generate_shopping_list(self, profile):
        components = IngredientsInRecipe.objects.filter(
            recipe__shoppingcarts__user=profile
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total=Sum('amount')).order_by('ingredient__name')

        dishes = Recipe.objects.filter(shoppingcarts__user=profile)
        output = []
        timestamp = timezone.now().strftime('%d-%m-%Y %H:%M')
        output.append(f'Список покупок на {timestamp}\n')
        output.append('\nРецепты:')

        for dish in dishes:
            output.append(f'- {dish.name} (Автор: {dish.author.username})')
        output.append('\nИнгредиенты:')
        for idx, item in enumerate(components, 1):
            unit = item['ingredient__measurement_unit']
            quantity = item['total']
            name = item['ingredient__name'].capitalize()
            output.append(f'{idx}. {name} ({unit}) — {quantity}')

        return '\n'.join(output)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated]
            )
    def download_shopping_cart(self, request):
        data = self.generate_shopping_list(request.user)
        resp = FileResponse(data, as_attachment=True,
                            filename='shopping_list.txt'
                            )
        return resp

    def include_recipe_in(self, profile, recipe, model):
        obj, created = model.objects.get_or_create(
            user=profile,
            recipe=recipe

        )

        if not created:
            return Response(
                {"errors": "Рецепт уже добавлен"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serialized = RecipeMinifiedSerializer(recipe)
        return Response(serialized.data, status=status.HTTP_201_CREATED)

    def exclude_recipe_from(self, profile, recipe, model):
        try:
            entry = get_object_or_404(model, user=profile, recipe=recipe)
            entry.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Http404:
            return Response(
                {"errors": "Рецепт не был добавлен"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def modify_recipe_relation(self, req, pk):
        profile = req.user
        dish = get_object_or_404(Recipe, id=pk)
        relation_model = Favorite if 'favorite' in req.path else ShoppingCart

        if req.method == 'POST':
            return self.include_recipe_in(profile, dish, relation_model)
        return self.exclude_recipe_from(profile, dish, relation_model)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated]
            )
    def favorite(self, request, pk=None):
        return self.modify_recipe_relation(request, pk)

    @action(
        detail=True, methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=(IsAuthenticated,)
    )
    def shopping_cart(self, request, pk=None):
        return self.modify_recipe_relation(request, pk)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except IntegrityError as err:
            if "unique_ingredient_in_recipe" in str(err):
                return Response(
                    {"errors": "Ингредиенты не должны повторяться"},
                    status=status.HTTP_400_BAD_REQUEST
                )

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_short_link(self, request, pk=None):
        path = reverse('recipe:recipe_short_link', kwargs={'pk': pk})
        full_url = request.build_absolute_uri(path)
        return Response(data={"short-link": full_url})


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
