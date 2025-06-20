from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    UserRegistrationSerializer,
    PasswordChangeSerializer,
    RestorePasswordSerializer,
    SetRestorePasswordSerializer,
    UserSerializer,
    UserProfileUpdateSerializer
)
from .models import UserProfile


User = get_user_model()


class RegistrationView(APIView):
    @swagger_auto_schema(request_body=UserRegistrationSerializer)
    def post(self, request: Request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.save()
            return Response(
                {
                    'message': 'Registration successful! You can login now.',
                    'user': {
                        'username': user.username,
                        'email': user.email,
                        'is_active': user.is_active
                    }
                },
                status=status.HTTP_201_CREATED
            )


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=PasswordChangeSerializer)
    def post(self, request: Request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid(raise_exception=True):
            serializer.set_new_password()
            return Response(
                'Password changed successfully',
                status=status.HTTP_200_OK
            )


class RestorePasswordView(APIView):
    @swagger_auto_schema(request_body=RestorePasswordSerializer)
    def post(self, request: Request):
        serializer = RestorePasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.send_code()
            return Response(
                'Code was sent to your email',
                status=status.HTTP_200_OK
            )


class SetRestoredPasswordView(APIView):
    @swagger_auto_schema(request_body=SetRestorePasswordSerializer)
    def post(self, request: Request):
        serializer = SetRestorePasswordSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.set_new_password()
            return Response(
                'Password restored successfully',
                status=status.HTTP_200_OK
            )


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request: Request):
        username = request.user.username
        User.objects.filter(username=username).delete()
        return Response(
            'Account deleted',
            status=status.HTTP_204_NO_CONTENT
        )


class UserProfileView(APIView):
    """Личный кабинет пользователя"""
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        """Получить информацию о пользователе и его профиле"""
        # Создаем профиль если его нет
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=UserProfileUpdateSerializer)
    def put(self, request: Request):
        """Обновить профиль пользователя"""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(profile, data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {'message': 'Profile updated successfully'},
                status=status.HTTP_200_OK
            )

    @swagger_auto_schema(request_body=UserProfileUpdateSerializer)
    def patch(self, request: Request):
        """Частично обновить профиль пользователя"""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {'message': 'Profile updated successfully'},
                status=status.HTTP_200_OK
            )


class UserStatsView(APIView):
    """Статистика пользователя для личного кабинета"""
    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        user = request.user
        
        # Безопасный импорт с обработкой ошибок
        try:
            from elitka.models import Favorite, Review
            favorites_count = Favorite.objects.filter(user=user).count()
            reviews_count = Review.objects.filter(user=user).count()
        except ImportError:
            favorites_count = 0
            reviews_count = 0
            
        try:
            from purchase.models import Booking
            bookings_count = Booking.objects.filter(user=user).count()
        except ImportError:
            bookings_count = 0
        
        stats = {
            'favorites_count': favorites_count,
            'bookings_count': bookings_count,
            'reviews_count': reviews_count,
        }
        
        return Response(stats, status=status.HTTP_200_OK)