from rest_framework.routers import DefaultRouter
from .views import BookingViewSet, InquiryViewSet

router = DefaultRouter()

# Основные endpoints
router.register('bookings', BookingViewSet, basename='bookings')
router.register('inquiries', InquiryViewSet, basename='inquiries')

urlpatterns = router.urls

# Итоговые URLs для purchase:
#
# Бронирования:
# GET    /purchase/bookings/                   - Список бронирований (свои/все)
# POST   /purchase/bookings/                   - Создать бронирование КОНКРЕТНОЙ квартиры
# GET    /purchase/bookings/{id}/              - Детали бронирования
# PATCH  /purchase/bookings/{id}/update_status/ - Изменить статус (админ)
# GET    /purchase/bookings/my_bookings/       - Мои бронирования
# DELETE /purchase/bookings/{id}/             - Удалить бронирование (админ)
#
# Вопросы:
# GET    /purchase/inquiries/                  - Все вопросы (админ)
# POST   /purchase/inquiries/                  - Задать вопрос (любой) о конкретной квартире
# GET    /purchase/inquiries/{id}/             - Детали вопроса (админ)
# PATCH  /purchase/inquiries/{id}/answer/      - Ответить на вопрос (админ)
# GET    /purchase/inquiries/my_inquiries/     - Мои вопросы (авторизованные)
# DELETE /purchase/inquiries/{id}/            - Удалить вопрос (админ)
#
# НОВЫЕ ВОЗМОЖНОСТИ:
# - Бронирование привязано к конкретной квартире (apartment), а не типу
# - Вопросы могут быть о конкретной квартире или о типе квартиры
# - Автоматическое управление статусами квартир при бронировании/отмене
# - Синхронизация счетчиков available_count в ApartmentType