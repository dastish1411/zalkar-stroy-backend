from rest_framework import serializers
from .models import (
    ResidentialComplex, 
    ComplexImage, 
    ApartmentType, 
    ApartmentTypeImage, 
    Favorite, 
    Review,
    Apartment
)


class ComplexImageSerializer(serializers.ModelSerializer):
    """Сериализатор для фотографий ЖК"""
    class Meta:
        model = ComplexImage
        fields = ['id', 'image', 'title', 'description', 'order']


class ApartmentTypeImageSerializer(serializers.ModelSerializer):
    """Сериализатор для фотографий интерьеров"""
    class Meta:
        model = ApartmentTypeImage
        fields = ['id', 'image', 'title', 'room_name', 'order']


class ApartmentTypeListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор типов квартир для списка"""
    room_name = serializers.CharField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    availability_status = serializers.CharField(read_only=True)
    sold_count = serializers.IntegerField(read_only=True)
    complex_name = serializers.CharField(source='complex.name', read_only=True)
    
    class Meta:
        model = ApartmentType
        fields = [
            'id', 'rooms', 'room_name', 'area', 'price', 
            'total_count', 'available_count', 'sold_count',
            'is_available', 'availability_status', 'main_image',
            'complex_name', 'complex'
        ]


class ApartmentTypeDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор типа квартиры"""
    room_name = serializers.CharField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    availability_status = serializers.CharField(read_only=True)
    sold_count = serializers.IntegerField(read_only=True)
    images = ApartmentTypeImageSerializer(many=True, read_only=True)
    complex_name = serializers.CharField(source='complex.name', read_only=True)
    
    class Meta:
        model = ApartmentType
        fields = [
            'id', 'complex', 'complex_name', 'rooms', 'room_name', 
            'area', 'price', 'layout_description',
            'main_image', 'layout_image', 'total_count', 
            'available_count', 'sold_count', 'is_available', 
            'availability_status', 'images', 'created_at'
        ]


class ResidentialComplexListSerializer(serializers.ModelSerializer):
    """Краткий сериализатор ЖК для главной страницы"""
    total_apartment_types = serializers.IntegerField(read_only=True)
    price_range = serializers.CharField(read_only=True)
    
    class Meta:
        model = ResidentialComplex
        fields = [
            'slug', 'name', 'address', 'status', 'completion_date',
            'main_image', 'total_apartment_types', 'price_range',
            'location_2gis'
        ]


class ResidentialComplexDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор ЖК"""
    apartment_types = ApartmentTypeListSerializer(many=True, read_only=True)
    images = ComplexImageSerializer(many=True, read_only=True)
    total_apartment_types = serializers.IntegerField(read_only=True)
    price_range = serializers.CharField(read_only=True)
    
    class Meta:
        model = ResidentialComplex
        fields = [
            'slug', 'name', 'description', 'address', 
            'total_buildings', 'total_floors', 'status', 
            'completion_date', 'infrastructure', 'main_image',
            'location_2gis', 'total_apartment_types',
            'price_range', 'apartment_types', 'images'
        ]


class FavoriteSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного"""
    apartment_type_detail = ApartmentTypeListSerializer(source='apartment_type', read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'user', 'apartment_type', 'apartment_type_detail', 'created_at']
        read_only_fields = ['user']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор для отзывов"""
    user = serializers.StringRelatedField(read_only=True)
    complex_name = serializers.CharField(source='complex.name', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'user', 'complex', 'complex_name', 
            'rating', 'text', 'created_at', 'is_approved'
        ]
        read_only_fields = ['user', 'is_approved']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания отзыва"""
    class Meta:
        model = Review
        fields = ['complex', 'rating', 'text']
    
    def validate_rating(self, value):
        if value not in range(1, 6):
            raise serializers.ValidationError('Рейтинг должен быть от 1 до 5')
        return value
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ApartmentTypeCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания типа квартиры"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ApartmentType
        fields = '__all__'
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        apartment_type = ApartmentType.objects.create(**validated_data)
        
        for i, image_data in enumerate(images_data):
            ApartmentTypeImage.objects.create(
                apartment_type=apartment_type,
                image=image_data,
                order=i
            )
        
        return apartment_type


class ResidentialComplexCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ЖК"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ResidentialComplex
        fields = '__all__'
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        complex = ResidentialComplex.objects.create(**validated_data)
        
        for i, image_data in enumerate(images_data):
            ComplexImage.objects.create(
                complex=complex,
                image=image_data,
                order=i
            )
        
        return complex


class ApartmentListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка квартир"""
    complex_name = serializers.CharField(source='complex.name', read_only=True)
    room_name = serializers.CharField(read_only=True)
    area = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Apartment
        fields = [
            'id', 'number', 'floor', 'position', 'status',
            'complex_name', 'room_name', 'area', 'price',
            'is_corner', 'is_vip', 'view_direction'
        ]


class ApartmentDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор квартиры"""
    apartment_type_detail = ApartmentTypeDetailSerializer(source='apartment_type', read_only=True)
    complex_name = serializers.CharField(source='complex.name', read_only=True)
    room_name = serializers.CharField(read_only=True)
    area = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = Apartment
        fields = [
            'id', 'number', 'floor', 'position', 'status',
            'complex_name', 'room_name', 'area', 'price',
            'is_corner', 'is_vip', 'view_direction', 'custom_price',
            'apartment_type_detail', 'created_at'
        ]


class FloorPlanSerializer(serializers.Serializer):
    """Сериализатор для плана этажа"""
    floor = serializers.IntegerField()
    apartments = ApartmentListSerializer(many=True)
    total_apartments = serializers.IntegerField()
    available_apartments = serializers.IntegerField()
    booked_apartments = serializers.IntegerField()
    sold_apartments = serializers.IntegerField()


class ComplexFloorStatsSerializer(serializers.Serializer):
    """Статистика по этажам ЖК"""
    complex_slug = serializers.CharField()
    complex_name = serializers.CharField()
    floors_data = serializers.DictField()
    total_floors = serializers.IntegerField()