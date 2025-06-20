from rest_framework import serializers
from .models import Booking, Inquiry


class BookingSerializer(serializers.ModelSerializer):
    """Сериализатор для бронирования квартиры"""
    complex_name = serializers.CharField(read_only=True)
    room_name = serializers.CharField(read_only=True)
    apartment_number = serializers.IntegerField(read_only=True)
    floor = serializers.IntegerField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    apartment_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'apartment', 'apartment_info', 'apartment_number', 'floor',
            'full_name', 'phone', 'email', 'comment', 'price',
            'status', 'complex_name', 'room_name', 'created_at',
            'manager_comment'
        ]
        read_only_fields = ['user', 'price', 'status', 'manager_comment']
    
    def get_apartment_info(self, obj):
        """Полная информация о квартире"""
        return {
            'number': obj.apartment.number,
            'floor': obj.apartment.floor,
            'room_name': obj.apartment.room_name,
            'area': obj.apartment.area,
            'complex_name': obj.apartment.complex.name,
            'is_corner': obj.apartment.is_corner,
            'is_vip': obj.apartment.is_vip,
        }
    
    def validate_phone(self, value):
        """Простая валидация телефона"""
        if not value.startswith('+996') and not value.startswith('0'):
            raise serializers.ValidationError('Введите корректный номер телефона')
        return value
    
    def validate_apartment(self, value):
        """Проверяем доступность квартиры"""
        if value.status != 'available':
            raise serializers.ValidationError('Эта квартира уже недоступна для бронирования')
        return value
    
    def create(self, validated_data):
        # Устанавливаем пользователя из контекста
        validated_data['user'] = self.context['request'].user
        
        # Получаем квартиру
        apartment = validated_data['apartment']
        
        # Проверяем доступность еще раз
        if apartment.status != 'available':
            raise serializers.ValidationError('Эта квартира уже недоступна')
        
        # Создаем бронирование с ценой квартиры
        booking = Booking.objects.create(
            **validated_data,
            price=apartment.price
        )
        
        # Помечаем квартиру как забронированную
        apartment.status = 'booked'
        apartment.save()
        
        # Уменьшаем счетчик доступных квартир в типе
        apartment_type = apartment.apartment_type
        apartment_type.available_count -= 1
        apartment_type.save()
        
        return booking


class BookingCreateSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для создания бронирования"""
    class Meta:
        model = Booking
        fields = ['apartment', 'full_name', 'phone', 'email', 'comment']
    
    def validate_phone(self, value):
        if not value.strip():
            raise serializers.ValidationError('Телефон обязателен')
        if not value.startswith('+996') and not value.startswith('0'):
            raise serializers.ValidationError('Введите корректный номер телефона')
        return value
    
    def validate_full_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Введите полное имя')
        return value
    
    def validate_apartment(self, value):
        if value.status != 'available':
            raise serializers.ValidationError('Эта квартира больше не доступна')
        return value


class InquirySerializer(serializers.ModelSerializer):
    """Сериализатор для вопросов клиентов"""
    subject_name = serializers.CharField(read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Inquiry
        fields = [
            'id', 'user', 'user_username', 'apartment', 'apartment_type', 'subject_name',
            'name', 'phone', 'email', 'message',
            'status', 'answer', 'created_at'
        ]
        read_only_fields = ['user', 'status', 'answer']


class InquiryCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания вопроса"""
    class Meta:
        model = Inquiry
        fields = ['apartment', 'apartment_type', 'name', 'phone', 'email', 'message']
    
    def validate(self, attrs):
        """Проверяем, что указан либо apartment, либо apartment_type"""
        apartment = attrs.get('apartment')
        apartment_type = attrs.get('apartment_type')
        
        if not apartment and not apartment_type:
            raise serializers.ValidationError('Укажите квартиру или тип квартиры для вопроса')
        
        if apartment and apartment_type:
            raise serializers.ValidationError('Укажите что-то одно: либо конкретную квартиру, либо тип квартиры')
        
        return attrs
    
    def validate_message(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError('Вопрос слишком короткий')
        return value
    
    def create(self, validated_data):
        # Автоматически привязываем к пользователю если он авторизован
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        return super().create(validated_data)


# Сериализаторы для админки
class BookingListSerializer(serializers.ModelSerializer):
    """Список бронирований для админки"""
    complex_name = serializers.CharField(read_only=True)
    room_name = serializers.CharField(read_only=True)
    apartment_number = serializers.IntegerField(read_only=True)
    floor = serializers.IntegerField(read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'id', 'user_username', 'full_name', 'phone',
            'apartment_number', 'floor', 'complex_name', 'room_name', 
            'price', 'status', 'created_at'
        ]


class BookingUpdateSerializer(serializers.ModelSerializer):
    """Обновление статуса бронирования (для менеджеров)"""
    class Meta:
        model = Booking
        fields = ['status', 'manager_comment']