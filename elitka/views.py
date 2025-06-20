from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg
from collections import defaultdict

from .models import (
    ResidentialComplex, 
    ApartmentType, 
    Favorite, 
    Review,
    Apartment
)
from .serializers import (
    ResidentialComplexListSerializer,
    ResidentialComplexDetailSerializer,
    ResidentialComplexCreateSerializer,
    ApartmentTypeListSerializer,
    ApartmentTypeDetailSerializer,
    ApartmentTypeCreateSerializer,
    FavoriteSerializer,
    ReviewSerializer,
    ReviewCreateSerializer,
    ApartmentListSerializer,
    ApartmentDetailSerializer,
    FloorPlanSerializer,
    ComplexFloorStatsSerializer
)


class ResidentialComplexViewSet(viewsets.ModelViewSet):
    """
    ViewSet для жилых комплексов
    
    list: Главная страница - показать все ЖК
    retrieve: Страница ЖК - показать детали + типы квартир
    """
    queryset = ResidentialComplex.objects.filter(is_active=True)
    lookup_field = 'slug'
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['name', 'address', 'description']
    ordering_fields = ['created_at', 'name', 'completion_date']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ResidentialComplexListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ResidentialComplexCreateSerializer
        return ResidentialComplexDetailSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'reviews']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def reviews(self, request, slug=None):
        """Получить отзывы о ЖК"""
        try:
            complex = self.get_object()
            reviews = complex.reviews.filter(is_approved=True).order_by('-created_at')
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data)
        except Exception as e:
            print(f"Error in reviews: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def stats(self, request, slug=None):
        """Статистика по ЖК"""
        complex = self.get_object()
        apartment_types = complex.apartment_types.filter(is_active=True)
        
        stats = {
            'total_apartment_types': apartment_types.count(),
            'total_apartments': sum(apt.total_count for apt in apartment_types),
            'available_apartments': sum(apt.available_count for apt in apartment_types),
            'sold_apartments': sum(apt.sold_count for apt in apartment_types),
            'average_rating': complex.reviews.filter(is_approved=True).aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0,
            'reviews_count': complex.reviews.filter(is_approved=True).count()
        }
        
        return Response(stats)


class ApartmentTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet для типов квартир
    
    list: Все типы квартир (с фильтрацией по ЖК)
    retrieve: Страница типа квартиры - детали + галерея фото
    """
    queryset = ApartmentType.objects.filter(is_active=True).select_related('complex')
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['complex', 'rooms']
    search_fields = ['complex__name']
    ordering_fields = ['price', 'area', 'rooms', 'created_at']
    ordering = ['complex', 'rooms']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Дополнительные фильтры по цене
        price_min = self.request.query_params.get('price__gte')
        price_max = self.request.query_params.get('price__lte')
        
        if price_min:
            queryset = queryset.filter(price__gte=price_min)
        if price_max:
            queryset = queryset.filter(price__lte=price_max)
            
        # Дополнительные фильтры по площади
        area_min = self.request.query_params.get('area__gte')
        area_max = self.request.query_params.get('area__lte')
        
        if area_min:
            queryset = queryset.filter(area__gte=area_min)
        if area_max:
            queryset = queryset.filter(area__lte=area_max)
            
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ApartmentTypeListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ApartmentTypeCreateSerializer
        return ApartmentTypeDetailSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action in ['add_to_favorites', 'remove_from_favorites']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'])
    def add_to_favorites(self, request, pk=None):
        """Добавить в избранное"""
        apartment_type = self.get_object()
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            apartment_type=apartment_type
        )
        
        if created:
            return Response({'message': 'Добавлено в избранное'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'message': 'Уже в избранном'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'])
    def remove_from_favorites(self, request, pk=None):
        """Удалить из избранного"""
        apartment_type = self.get_object()
        try:
            favorite = Favorite.objects.get(user=request.user, apartment_type=apartment_type)
            favorite.delete()
            return Response({'message': 'Удалено из избранного'}, status=status.HTTP_204_NO_CONTENT)
        except Favorite.DoesNotExist:
            return Response({'message': 'Не найдено в избранном'}, status=status.HTTP_404_NOT_FOUND)


class FavoriteViewSet(viewsets.ModelViewSet):
    """
    ViewSet для избранного пользователя
    Только для авторизованных пользователей
    """
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).select_related(
            'apartment_type__complex'
        )
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet для отзывов
    
    list: Все одобренные отзывы
    create: Создать отзыв (только авторизованные)
    """
    queryset = Review.objects.filter(is_approved=True).select_related('user', 'complex')
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['complex', 'rating']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        # Проверяем, есть ли уже отзыв от этого пользователя на этот ЖК
        complex_slug = request.data.get('complex')
        if Review.objects.filter(user=request.user, complex__slug=complex_slug).exists():
            return Response(
                {'error': 'Вы уже оставили отзыв об этом ЖК'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().create(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ApartmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet для конкретных квартир
    
    list: Все квартиры с фильтрацией
    retrieve: Детали конкретной квартиры
    floor_plan: План конкретного этажа
    complex_floors: Статистика по всем этажам ЖК
    """
    queryset = Apartment.objects.all().select_related('apartment_type__complex')
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['apartment_type__complex', 'apartment_type__rooms', 'floor', 'status']
    search_fields = ['number', 'apartment_type__complex__name']
    ordering_fields = ['number', 'floor', 'apartment_type__price']
    ordering = ['apartment_type__complex', 'floor', 'position']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ApartmentListSerializer
        return ApartmentDetailSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'floor_plan', 'complex_floors']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Дополнительные фильтры
        complex_slug = self.request.query_params.get('complex')
        if complex_slug:
            queryset = queryset.filter(apartment_type__complex__slug=complex_slug)
            
        # Фильтр только доступных
        available_only = self.request.query_params.get('available_only')
        if available_only and available_only.lower() == 'true':
            queryset = queryset.filter(status='available')
            
        return queryset
    
    @action(detail=False, methods=['get'])
    def floor_plan(self, request):
        """
        Получить план конкретного этажа
        URL: /elitka/apartments/floor_plan/?complex=madison&floor=5&rooms=2
        """
        complex_slug = request.query_params.get('complex')
        floor_number = request.query_params.get('floor')
        rooms = request.query_params.get('rooms')
        
        if not complex_slug or not floor_number:
            return Response(
                {'error': 'Требуются параметры complex и floor'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            floor_number = int(floor_number)
        except ValueError:
            return Response(
                {'error': 'floor должен быть числом'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем квартиры этажа
        queryset = Apartment.objects.filter(
            apartment_type__complex__slug=complex_slug,
            floor=floor_number
        ).select_related('apartment_type').order_by('position')
        
        # Фильтр по количеству комнат
        if rooms:
            try:
                rooms = int(rooms)
                queryset = queryset.filter(apartment_type__rooms=rooms)
            except ValueError:
                pass
        
        apartments = list(queryset)
        
        if not apartments:
            return Response(
                {'error': 'Этаж не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Статистика этажа
        total = len(apartments)
        available = len([apt for apt in apartments if apt.status == 'available'])
        booked = len([apt for apt in apartments if apt.status == 'booked'])
        sold = len([apt for apt in apartments if apt.status == 'sold'])
        
        data = {
            'floor': floor_number,
            'apartments': ApartmentListSerializer(apartments, many=True).data,
            'total_apartments': total,
            'available_apartments': available,
            'booked_apartments': booked,
            'sold_apartments': sold
        }
        
        serializer = FloorPlanSerializer(data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def complex_floors(self, request):
        """
        Получить статистику по всем этажам ЖК
        URL: /elitka/apartments/complex_floors/?complex=madison
        """
        complex_slug = request.query_params.get('complex')
        
        if not complex_slug:
            return Response(
                {'error': 'Требуется параметр complex'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            complex_obj = ResidentialComplex.objects.get(slug=complex_slug)
        except ResidentialComplex.DoesNotExist:
            return Response(
                {'error': 'ЖК не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Получаем все квартиры ЖК
        apartments = Apartment.objects.filter(
            apartment_type__complex=complex_obj
        ).select_related('apartment_type')
        
        # Группируем по этажам и типам
        floors_data = defaultdict(lambda: defaultdict(lambda: {
            'total': 0, 'available': 0, 'booked': 0, 'sold': 0
        }))
        
        max_floor = 0
        
        for apt in apartments:
            floor = apt.floor
            room_key = f'{apt.apartment_type.rooms}-room'
            
            max_floor = max(max_floor, floor)
            
            floors_data[floor][room_key]['total'] += 1
            
            if apt.status == 'available':
                floors_data[floor][room_key]['available'] += 1
            elif apt.status == 'booked':
                floors_data[floor][room_key]['booked'] += 1
            elif apt.status == 'sold':
                floors_data[floor][room_key]['sold'] += 1
        
        # Преобразуем в обычный dict для сериализации
        floors_data = dict(floors_data)
        for floor_data in floors_data.values():
            for room_type in floor_data:
                floor_data[room_type] = dict(floor_data[room_type])
        
        data = {
            'complex_slug': complex_slug,
            'complex_name': complex_obj.name,
            'floors_data': floors_data,
            'total_floors': max_floor
        }
        
        serializer = ComplexFloorStatsSerializer(data)
        return Response(serializer.data)