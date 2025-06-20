from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models

from .models import Booking, Inquiry
from .serializers import (
    BookingSerializer,
    BookingCreateSerializer,
    BookingListSerializer,
    BookingUpdateSerializer,
    InquirySerializer,
    InquiryCreateSerializer
)


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet для бронирований квартир
    
    Клиенты могут:
    - Создавать бронирования конкретных квартир
    - Просматривать свои бронирования
    
    Админы могут:
    - Просматривать все бронирования
    - Изменять статусы
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'apartment__apartment_type__complex']
    search_fields = ['full_name', 'phone', 'email', 'apartment__number']
    ordering_fields = ['created_at', 'price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            # Админы видят все бронирования
            return Booking.objects.all().select_related(
                'user', 
                'apartment__apartment_type__complex'
            )
        else:
            # Клиенты видят только свои
            return Booking.objects.filter(user=user).select_related(
                'apartment__apartment_type__complex'
            )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        elif self.action == 'list' and self.request.user.is_staff:
            return BookingListSerializer
        elif self.action in ['update', 'partial_update']:
            return BookingUpdateSerializer
        return BookingSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """Создание бронирования с обновлением статуса квартиры"""
        # Получаем квартиру
        apartment = serializer.validated_data['apartment']
        
        # Проверяем доступность
        if apartment.status != 'available':
            raise serializers.ValidationError({
                'apartment': f'Квартира {apartment.number} больше не доступна для бронирования'
            })
        
        # Создаем бронирование с текущей ценой квартиры
        booking = serializer.save(
            user=self.request.user,
            price=apartment.price
        )
        
        # ВАЖНО: Помечаем квартиру как забронированную
        apartment.status = 'booked'
        apartment.save()
        
        # Уменьшаем счетчик доступных квартир
        apartment_type = apartment.apartment_type
        apartment_type.available_count -= 1
        apartment_type.save()
        
        return booking
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def update_status(self, request, pk=None):
        """Изменение статуса бронирования (только для админов)"""
        booking = self.get_object()
        new_status = request.data.get('status')
        manager_comment = request.data.get('manager_comment', '')
        
        if new_status not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return Response(
                {'error': 'Неверный статус'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = booking.status
        apartment = booking.apartment
        apartment_type = apartment.apartment_type
        
        # Обрабатываем изменения статуса
        if old_status != new_status:
            if new_status == 'cancelled':
                # Отмена: возвращаем квартиру в доступные
                if old_status in ['pending', 'confirmed']:
                    apartment.status = 'available'
                    apartment.save()
                    apartment_type.available_count += 1
                    apartment_type.save()
            
            elif new_status == 'completed':
                # Завершение: помечаем квартиру как проданную
                if old_status in ['pending', 'confirmed']:
                    apartment.status = 'sold'
                    apartment.save()
                    # available_count уже уменьшен при бронировании
            
            elif new_status == 'confirmed':
                # Подтверждение: квартира остается забронированной
                if old_status == 'cancelled':
                    # Возвращаем из отмененного в подтвержденное
                    apartment.status = 'booked'
                    apartment.save()
                    apartment_type.available_count -= 1
                    apartment_type.save()
        
        # Обновляем бронирование
        booking.status = new_status
        booking.manager_comment = manager_comment
        booking.save()
        
        return Response({
            'message': f'Статус изменен с "{old_status}" на "{new_status}"',
            'status': new_status,
            'apartment_status': apartment.status
        })
    
    @action(detail=False, methods=['get'])
    def my_bookings(self, request):
        """Мои бронирования (для клиентов)"""
        bookings = self.get_queryset().filter(user=request.user)
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data)


class InquiryViewSet(viewsets.ModelViewSet):
    """
    ViewSet для вопросов клиентов с поддержкой конкретных квартир
    """
    queryset = Inquiry.objects.all().select_related(
        'apartment__apartment_type__complex', 
        'apartment_type__complex',
        'user'
    )
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 
        'apartment__apartment_type__complex',
        'apartment_type__complex'
    ]
    search_fields = [
        'name', 'phone', 'email', 'message',
        'apartment__number',
        'apartment__apartment_type__complex__name',
        'apartment_type__complex__name'
    ]
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InquiryCreateSerializer
        return InquirySerializer
    
    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]  # Любой может задать вопрос
        elif self.action in ['list', 'retrieve']:
            permission_classes = [IsAdminUser]  # Только админы видят все вопросы
        elif self.action == 'my_inquiries':
            permission_classes = [IsAuthenticated]  # Пользователи видят свои вопросы
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """При создании вопроса автоматически привязываем к пользователю"""
        # Если пользователь авторизован, привязываем вопрос к нему
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            # Анонимный вопрос (без привязки к пользователю)
            serializer.save()
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAdminUser])
    def answer(self, request, pk=None):
        """Ответить на вопрос (только для админов)"""
        inquiry = self.get_object()
        answer = request.data.get('answer', '')
        
        if not answer.strip():
            return Response(
                {'error': 'Ответ не может быть пустым'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inquiry.answer = answer
        inquiry.status = 'answered'
        inquiry.save()
        
        return Response({
            'message': 'Ответ отправлен',
            'answer': answer
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_inquiries(self, request):
        """
        Мои вопросы - поиск по ID пользователя
        """
        user = request.user
        
        # Ищем все вопросы этого пользователя
        inquiries = Inquiry.objects.filter(
            user=user
        ).select_related(
            'apartment__apartment_type__complex',
            'apartment_type__complex'
        ).order_by('-created_at')
        
        serializer = InquirySerializer(inquiries, many=True)
        return Response(serializer.data)