from rest_framework.routers import DefaultRouter
from .views import (
    ResidentialComplexViewSet,
    ApartmentTypeViewSet,
    FavoriteViewSet,
    ReviewViewSet,
    ApartmentViewSet
)

router = DefaultRouter()

# Основные endpoints для каталога
router.register('complexes', ResidentialComplexViewSet, basename='complexes')
router.register('apartment-types', ApartmentTypeViewSet, basename='apartment-types')
router.register('apartments', ApartmentViewSet, basename='apartments')

# Пользовательские функции
router.register('favorites', FavoriteViewSet, basename='favorites')
router.register('reviews', ReviewViewSet, basename='reviews')

urlpatterns = router.urls

# Итоговые URLs для elitka:
#
# Жилые комплексы:
# GET    /elitka/complexes/                     - Список всех ЖК
# GET    /elitka/complexes/{slug}/              - Детали ЖК + типы квартир
# GET    /elitka/complexes/{slug}/reviews/      - Отзывы о ЖК
# GET    /elitka/complexes/{slug}/stats/        - Статистика ЖК
#
# Типы квартир:
# GET    /elitka/apartment-types/               - Все типы квартир
# GET    /elitka/apartment-types/{id}/          - Детали типа + фото
# POST   /elitka/apartment-types/{id}/add_to_favorites/    - В избранное
# DELETE /elitka/apartment-types/{id}/remove_from_favorites/ - Из избранного
#
# Конкретные квартиры:
# GET    /elitka/apartments/                    - Все квартиры с фильтрацией
# GET    /elitka/apartments/{id}/               - Детали конкретной квартиры
# GET    /elitka/apartments/floor_plan/         - План этажа (complex, floor, rooms)
# GET    /elitka/apartments/complex_floors/     - Статистика этажей ЖК (complex)
#
# Избранное (только для авторизованных):
# GET    /elitka/favorites/                     - Мои избранные
# POST   /elitka/favorites/                     - Добавить в избранное
# DELETE /elitka/favorites/{id}/               - Удалить из избранного
#
# Отзывы:
# GET    /elitka/reviews/                       - Все отзывы
# POST   /elitka/reviews/                       - Создать отзыв