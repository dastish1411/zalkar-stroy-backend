from django.urls import path
from .views import (
    RegistrationView, 
    ChangePasswordView,
    RestorePasswordView,
    SetRestoredPasswordView,
    DeleteAccountView,
    UserProfileView,
    UserStatsView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Регистрация БЕЗ активации
    path('register/', RegistrationView.as_view(), name='registration'),
    
    # Авторизация (JWT токены)
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Управление паролем
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('restore-password/', RestorePasswordView.as_view(), name='restore_password'),
    path('set-restored-password/', SetRestoredPasswordView.as_view(), name='set_restored_password'),
    
    # Личный кабинет
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('stats/', UserStatsView.as_view(), name='user_stats'),
    
    # Удаление аккаунта
    path('delete-account/', DeleteAccountView.as_view(), name='delete_account')
]

# УБРАЛИ АКТИВАЦИЮ:
# path('activate/<str:activation_code>/', AccountActivationView.as_view(), name='activation'),

# Итоговые URLs для account БЕЗ активации:
#
# Регистрация и авторизация:
# POST   /account/register/                    - Регистрация (сразу активен)
# POST   /account/login/                       - Вход (получить токены)
# POST   /account/api/token/refresh/           - Обновить токен
#
# Управление паролем:
# POST   /account/change-password/             - Сменить пароль
# POST   /account/restore-password/            - Восстановить пароль
# POST   /account/set-restored-password/       - Установить новый пароль
#
# Личный кабинет:
# GET    /account/profile/                     - Получить профиль
# PUT    /account/profile/                     - Обновить профиль
# PATCH  /account/profile/                     - Частично обновить профиль
# GET    /account/stats/                       - Статистика пользователя
#
# Удаление:
# DELETE /account/delete-account/              - Удалить аккаунт