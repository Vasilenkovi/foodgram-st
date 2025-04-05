import base64
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import UserSerializer as BaseUserSerializer
from recipe.models import (
    Ingredient,
    IngredientsInRecipe,
    Recipe,
    User,
    Follow,
    Favorite,
    ShoppingCart
)

UserModel = get_user_model()


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientsInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('id', 'name', 'measurement_unit', 'amount')


class UserSerializer(BaseUserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'avatar'
                  )

    def get_is_subscribed(self, obj):
        current_user = self.context.get('request').user
        return current_user.is_authenticated and Follow.objects.filter(
            follower=current_user, author=obj
        ).exists()


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = IngredientsInRecipeSerializer(
        source='ingredients_in_recipe',
        many=True,
        allow_empty=False
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = (
            'id', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Favorite.objects.filter(
            user=user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and ShoppingCart.objects.filter(
            user=user,
            recipe=obj
        ).exists()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class RecipeCreateUpdateSerializer(RecipeSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = RecipeSerializer.Meta.fields

    def process_ingredients(self, recipe, ingredients_data):
        IngredientsInRecipe.objects.bulk_create(
            IngredientsInRecipe(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item.get('amount', 1)
            ) for item in ingredients_data
        )

    def validate(self, data):
        ingredients = data.get('ingredients_in_recipe', [])
        if not ingredients:
            raise serializers.ValidationError(
                {"ingredients": "Необходимо указать ингредиенты"}
            )

        seen_ids = set()
        for item in ingredients:
            if item.get('amount', 0) < 1:
                raise serializers.ValidationError(
                    {"amount": "Количество ингредиента не может быть меньше 1"}
                )

            ing_id = item['ingredient'].id
            if ing_id in seen_ids:
                raise serializers.ValidationError(
                    {"ingredients": "Ингредиенты не должны повторяться"}
                )
            seen_ids.add(ing_id)
        return data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients_in_recipe')
        recipe = super().create(validated_data)
        self.process_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients_in_recipe', None)
        instance.ingredients_in_recipe.all().delete()
        self.process_ingredients(instance, ingredients)
        return super().update(instance, validated_data)


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = fields


class FollowedUserSerializer(UserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count')

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name',
            'last_name', 'is_subscribed', 'recipes',
            'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        recipes_limit = int(
            self.context['request'].query_params.get('recipes_limit', 10**10)
        )
        return RecipeMinifiedSerializer(
            obj.recipes.all()[:recipes_limit],
            many=True
        ).data


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)
