import os
import json

from django.conf import settings
from django.core.management import BaseCommand
from recipe.models import Ingredient


class Command(BaseCommand):
    help = 'Добавляет ингредиенты в БД'

    def handle(self, *args, **options):
        try:
            file_path = os.path.join(
                settings.BASE_DIR, 'data/', 'ingredients.json')

            with open(file_path, 'r', encoding='utf-8') as file:
                reader = json.load(file)
                ingredients = [
                    Ingredient(**item)
                    for item in reader
                ]
                Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)
                number_of_loaded_items = Ingredient.objects.count()

            print(f'Успешно загружено: ${number_of_loaded_items}')
        except IOError as e:
            print('Произошла ошибка при добавлении ингредиентов', e)
