import base64
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from rest_framework import serializers
from djoser.serializers import UserSerializer as SerializerForUser
from recipe.models import (
    Ingredient, 
    IngredientsInRecipe, 
    Recipe,
    User,
    Follow,
    Favorite,
    ShoppingCart
    )

User = get_user_model()

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measure_unit')


class IngredientsInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measure_unit = serializers.ReadOnlyField(source='ingredient.measure_unit')

    class Meta:
        model = IngredientsInRecipe
        fields = ('id', 'name', 'measure_unit', 'number')


class UserSerializer(SerializerForUser):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, user):
        current_user = self.context.get('request').user

        return current_user.is_authenticated and Follow.objects.filter(follower=current_user, author=user.id).exists()


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = IngredientsInRecipeSerializer(source='ingredients_in_recipe', 
                                                many=True, 
                                                allow_empty=False,
                                               allow_null=False)
    is_liked = serializers.SerializerMethodField()
    added_to_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 
            'ingredients', 
            'is_liked', 
            'added_to_cart', 
            'name', 
            'image', 
            'text',
            'cooking_time')



class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    ingredients = IngredientsInRecipeSerializer(source='ingredients_in_recipe', many=True, allow_empty=False,
                                               allow_null=False)
    is_liked = serializers.SerializerMethodField()
    added_to_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_liked', 'added_to_cart', 'name', 'image', 'text',
            'cooking_time')

    def get_is_liked(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and Favorite.objects.filter(user=user, recipe=obj).exists()

    def get_added_to_cart(self, obj):
        user = self.context['request'].user
        return user.is_authenticated and ShoppingCart.objects.filter(user=user, recipe=obj).exists()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class RecipeCreateUpdateSerializer(RecipeSerializer):
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_liked', 'added_to_cart', 'name', 'image', 'text',
            'cooking_time')

    def create_ingredients(self, recipe, ingredients):
        IngredientsInRecipe.objects.bulk_create(
            IngredientsInRecipe(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            ) for ingredient_data in ingredients
        )

    def validate_ingredients_field(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': serializers.ListField.default_error_messages['empty']}
            )

        ingredients_ids = []

        for item in ingredients:
            if item['ingredient'].id not in ingredients_ids:
                ingredients_ids.append(item['ingredient'].id)
            else:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты должны различаться'}
                )

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients_in_recipe')
        self.validate_ingredients_field(ingredients)

        recipe = super().create(validated_data)
        self.create_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients_in_recipe', None)
        self.validate_ingredients_field(ingredients)
        instance.ingredients_in_recipe.all().delete()
        self.create_ingredients(instance, ingredients)

        return super().update(instance, validated_data)


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


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
        fields = ('id', 'username', 'email', 'first_name', 'last_name',
                  'is_subscribed', 'recipes', 'recipes_count', 'avatar')

    def get_recipes(self, user):
        recipes_limit = int(self.context.get('request').query_params.get('recipes_limit', 10 ** 10))
        recipes = user.recipes.all()[:recipes_limit]

        return RecipeMinifiedSerializer(recipes, many=True).data