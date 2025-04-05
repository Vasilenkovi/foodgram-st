from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator


class User(AbstractUser):
    email = models.EmailField(
        'Адрес электронной почты',
        unique=True,
        max_length=254,
        blank=False
    )
    username = models.CharField(
        'Юзернейм',
        max_length=150,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[\w.@+-]+$'
        )]
    )
    first_name = models.CharField('Имя', max_length=150)
    last_name = models.CharField('Фамилия', max_length=150)
    avatar = models.ImageField(
        'Фото пользователя',
        upload_to='avatars/',
        null=True,
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username


class Ingredient(models.Model):
    name = models.CharField(
        verbose_name="Название ингридиента",
        max_length=128,
    )
    measurement_unit = models.CharField(
        verbose_name="Единица измерения",
        max_length=64,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор",
    )
    name = models.CharField(verbose_name="Название рецепта", max_length=256,)
    image = models.ImageField(
        upload_to="recipe_pic",
        verbose_name="Фотография",
        max_length=256
    )
    text = models.TextField(
        verbose_name="Описание"
    )
    cooking_time = models.PositiveIntegerField(
        "Время приготовления (в минутах)",
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientsInRecipe',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name


class IngredientsInRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="ingredients_in_recipe",
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Ингредиент",
    )
    amount = models.PositiveIntegerField(
        verbose_name="Число",
        validators=[MinValueValidator(1)]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient_in_recipe'
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name} в {self.recipe.name}'


class UserRecipeBaseModel(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint
            (
                fields=['user', 'recipe'],
                name='unique_user_recipe_%(class)s'
            )
        ]


class Favorite(UserRecipeBaseModel):
    class Meta(UserRecipeBaseModel.Meta):
        verbose_name = 'Избранное'

    def __str__(self):
        return f'{self.user.username} добавил в избранное {self.recipe.name}'


class ShoppingCart(UserRecipeBaseModel):
    class Meta(UserRecipeBaseModel.Meta):
        verbose_name = 'Корзина'

    def __str__(self):
        return f'Рецепт "{self.recipe.name}" в корзине у {self.user.username}'


class Follow(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authors_subs',
        verbose_name='автор'
    )
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers_subs',
        verbose_name='подписчик'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint
            (
                fields=['author', 'follower'],
                name='unique_subscription'
            )
        ]

    def __str__(self):
        return f'{self.follower} подписан на {self.author}'
