from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import (
    ResidentialComplex, 
    ComplexImage, 
    ApartmentType, 
    ApartmentTypeImage, 
    Favorite, 
    Review,
    Apartment
)
import random

User = get_user_model()


class ComplexImageInline(admin.TabularInline):
    """Inline для добавления фото ЖК"""
    model = ComplexImage
    extra = 1
    fields = ['image', 'title', 'description', 'order']


class ApartmentTypeInline(admin.TabularInline):
    """Inline для типов квартир в ЖК"""
    model = ApartmentType
    extra = 0
    fields = ['rooms', 'area', 'price', 'total_count', 'available_count', 'is_active']
    readonly_fields = ['total_count', 'available_count']  # Только для чтения


class ApartmentInline(admin.TabularInline):
    """Inline для конкретных квартир в типе"""
    model = Apartment
    extra = 0
    fields = ['number', 'floor', 'position', 'status', 'is_corner', 'is_vip']
    readonly_fields = []


@admin.register(ResidentialComplex)
class ResidentialComplexAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'status', 
        'total_apartment_types', 
        'total_apartments_count',
        'completion_date', 
        'is_active'
    ]
    list_filter = ['status', 'is_active', 'completion_date']
    search_fields = ['name', 'address']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'address')
        }),
        ('Характеристики', {
            'fields': ('total_buildings', 'total_floors', 'status', 'completion_date')
        }),
        ('Медиа', {
            'fields': ('main_image',)
        }),
        ('Геолокация', {
            'fields': ('location_2gis',),
            'classes': ('collapse',)
        }),
        ('Инфраструктура', {
            'fields': ('infrastructure',),
            'classes': ('collapse',)
        }),
        ('Системные', {
            'fields': ('is_active',)
        })
    )
    
    inlines = [ComplexImageInline, ApartmentTypeInline]
    
    # НОВОЕ ДЕЙСТВИЕ ДЛЯ АРХИТЕКТУРНОЙ ГЕНЕРАЦИИ
    actions = ['generate_all_apartments']
    
    def total_apartment_types(self, obj):
        return obj.apartment_types.count()
    total_apartment_types.short_description = 'Типов квартир'
    
    def total_apartments_count(self, obj):
        """Показывает общее количество созданных квартир"""
        total = 0
        for apt_type in obj.apartment_types.all():
            total += apt_type.apartments.count()
        return total
    total_apartments_count.short_description = 'Всего квартир'
    
    def generate_all_apartments(self, request, queryset):
        """🏗️ Генерирует все квартиры ЖК с архитектурно правильным распределением"""
        
        total_generated = 0
        
        for complex_obj in queryset:
            # Проверяем есть ли все 3 типа квартир
            apartment_types = complex_obj.apartment_types.filter(is_active=True)
            
            if apartment_types.count() != 3:
                self.message_user(
                    request, 
                    f'❌ В ЖК "{complex_obj.name}" должно быть ровно 3 типа квартир (1-к, 2-к, 3-к). '
                    f'Сейчас: {apartment_types.count()}',
                    level='ERROR'
                )
                continue
            
            # Проверяем что есть все нужные типы
            has_1k = apartment_types.filter(rooms=1).exists()
            has_2k = apartment_types.filter(rooms=2).exists()
            has_3k = apartment_types.filter(rooms=3).exists()
            
            if not (has_1k and has_2k and has_3k):
                self.message_user(
                    request,
                    f'❌ В ЖК "{complex_obj.name}" отсутствуют нужные типы квартир '
                    f'(нужны: 1-комнатная, 2-комнатная, 3-комнатная)',
                    level='ERROR'
                )
                continue
            
            # Удаляем ВСЕ существующие квартиры этого ЖК
            for apt_type in apartment_types:
                apt_type.apartments.all().delete()
            
            # Получаем типы квартир
            type_1k = apartment_types.get(rooms=1)
            type_2k = apartment_types.get(rooms=2) 
            type_3k = apartment_types.get(rooms=3)
            
            total_floors = complex_obj.total_floors
            apartments_created = 0
            
            # 🏗️ АРХИТЕКТУРНАЯ ГЕНЕРАЦИЯ ПО ЭТАЖАМ
            for floor in range(1, total_floors + 1):
                
                # 1-комнатные квартиры (позиции 1, 2)
                for pos in [1, 2]:
                    number = floor * 10 + pos  # 11, 12, 21, 22, 31, 32...
                    Apartment.objects.create(
                        apartment_type=type_1k,
                        number=number,
                        floor=floor,
                        position=pos,
                        status='available'
                    )
                    apartments_created += 1
                
                # 2-комнатные квартиры (позиции 3, 4)  
                for pos in [3, 4]:
                    number = floor * 10 + pos  # 13, 14, 23, 24, 33, 34...
                    Apartment.objects.create(
                        apartment_type=type_2k,
                        number=number,
                        floor=floor,
                        position=pos,
                        status='available'
                    )
                    apartments_created += 1
                
                # 3-комнатные квартиры (позиции 5, 6)
                for pos in [5, 6]:
                    number = floor * 10 + pos  # 15, 16, 25, 26, 35, 36...
                    Apartment.objects.create(
                        apartment_type=type_3k,
                        number=number,
                        floor=floor,
                        position=pos,
                        status='available'
                    )
                    apartments_created += 1
            
            # 📊 АВТОМАТИЧЕСКИ ОБНОВЛЯЕМ СЧЕТЧИКИ В ТИПАХ КВАРТИР
            for apartment_type in apartment_types:
                total_apts = apartment_type.apartments.count()
                apartment_type.total_count = total_apts
                apartment_type.available_count = total_apts  # Все доступны
                apartment_type.save()
            
            total_generated += apartments_created
            
            # Добавляем немного проданных для реализма
            self._mark_some_as_sold(apartment_types)
            
            self.message_user(
                request,
                f'✅ ЖК "{complex_obj.name}": создано {apartments_created} квартир '
                f'({total_floors} этажей × 6 квартир на этаже)\n'
                f'   • 1-комнатные: {total_floors * 2} шт\n'
                f'   • 2-комнатные: {total_floors * 2} шт\n'
                f'   • 3-комнатные: {total_floors * 2} шт'
            )
        
        if total_generated > 0:
            self.message_user(
                request,
                f'🎉 ИТОГО сгенерировано {total_generated} квартир с архитектурно правильным распределением!'
            )
    
    generate_all_apartments.short_description = '🏗️ Сгенерировать все квартиры ЖК (архитектурно правильно)'
    
    def _mark_some_as_sold(self, apartment_types):
        """Помечает случайные квартиры как проданные для реализма"""
        for apartment_type in apartment_types:
            apartments = list(apartment_type.apartments.all())
            if apartments:
                # Продаем 10-20% квартир случайно
                sold_count = max(1, len(apartments) // 8)  # ~12.5%
                sold_apartments = random.sample(apartments, min(sold_count, len(apartments)))
                
                for apt in sold_apartments:
                    apt.status = 'sold'
                    apt.save()
                
                # Обновляем счетчик доступных
                apartment_type.available_count = apartment_type.apartments.filter(status='available').count()
                apartment_type.save()


class ApartmentTypeImageInline(admin.TabularInline):
    """Inline для фото интерьеров"""
    model = ApartmentTypeImage
    extra = 1
    fields = ['image', 'title', 'room_name', 'order']


@admin.register(ApartmentType)
class ApartmentTypeAdmin(admin.ModelAdmin):
    list_display = [
        'complex', 
        'room_name', 
        'area', 
        'price', 
        'total_count', 
        'available_count',
        'actual_apartments_count',
        'availability_status',
        'is_active'
    ]
    list_filter = ['complex', 'rooms', 'is_active']
    search_fields = ['complex__name']
    list_editable = ['price']  # Убрали возможность редактировать счетчики
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('complex', 'rooms', 'area', 'price')
        }),
        ('Описание', {
            'fields': ('layout_description',)
        }),
        ('Изображения', {
            'fields': ('main_image', 'layout_image')
        }),
        ('Счетчики квартир (автоматические)', {
            'fields': ('total_count', 'available_count'),
            'description': '⚠️ Эти поля заполняются автоматически при генерации квартир из ЖК',
            'classes': ('collapse',)
        }),
        ('Системные', {
            'fields': ('is_active',)
        })
    )
    
    readonly_fields = ['total_count', 'available_count']  # Только для чтения
    
    inlines = [ApartmentTypeImageInline, ApartmentInline]
    
    def room_name(self, obj):
        return obj.room_name
    room_name.short_description = 'Тип'
    
    def availability_status(self, obj):
        return obj.availability_status
    availability_status.short_description = 'Статус'
    
    def actual_apartments_count(self, obj):
        """Показывает реальное количество созданных квартир"""
        return obj.apartments.count()
    actual_apartments_count.short_description = 'Создано квартир'


@admin.register(ComplexImage)
class ComplexImageAdmin(admin.ModelAdmin):
    list_display = ['complex', 'title', 'order']
    list_filter = ['complex']
    list_editable = ['order']


@admin.register(ApartmentTypeImage)
class ApartmentTypeImageAdmin(admin.ModelAdmin):
    list_display = ['apartment_type', 'title', 'room_name', 'order']
    list_filter = ['apartment_type__complex', 'apartment_type__rooms']
    list_editable = ['order']


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'apartment_type', 'created_at']
    list_filter = ['apartment_type__complex', 'created_at']
    search_fields = ['user__username', 'apartment_type__complex__name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'complex', 'rating', 'is_approved', 'created_at']
    list_filter = ['complex', 'rating', 'is_approved', 'created_at']
    search_fields = ['user__username', 'complex__name', 'text']
    list_editable = ['is_approved']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Отзыв', {
            'fields': ('user', 'complex', 'rating', 'text')
        }),
        ('Модерация', {
            'fields': ('is_approved', 'created_at')
        })
    )


@admin.register(Apartment)
class ApartmentAdmin(admin.ModelAdmin):
    list_display = [
        'number',
        'apartment_type',
        'complex_name', 
        'floor',
        'position',
        'status',
        'price',
        'is_corner',
        'is_vip'
    ]
    list_filter = [
        'apartment_type__complex',
        'apartment_type__rooms',
        'floor',
        'status',
        'is_corner',
        'is_vip'
    ]
    search_fields = ['number', 'apartment_type__complex__name']
    list_editable = ['status', 'is_corner', 'is_vip']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('apartment_type', 'number', 'floor', 'position')
        }),
        ('Статус', {
            'fields': ('status',)
        }),
        ('Особенности', {
            'fields': ('is_corner', 'is_vip', 'view_direction', 'custom_price')
        })
    )
    
    def complex_name(self, obj):
        return obj.complex.name
    complex_name.short_description = 'ЖК'
    
    # Массовые действия
    actions = ['mark_as_sold', 'mark_as_available']
    
    def mark_as_sold(self, request, queryset):
        updated = queryset.update(status='sold')
        # Обновляем счетчики в типах квартир
        for apartment in queryset:
            apt_type = apartment.apartment_type
            apt_type.available_count = apt_type.apartments.filter(status='available').count()
            apt_type.save()
        self.message_user(request, f'{updated} квартир помечено как проданные')
    mark_as_sold.short_description = 'Пометить как проданные'
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(status='available')
        # Обновляем счетчики в типах квартир
        for apartment in queryset:
            apt_type = apartment.apartment_type
            apt_type.available_count = apt_type.apartments.filter(status='available').count()
            apt_type.save()
        self.message_user(request, f'{updated} квартир помечено как свободные')
    mark_as_available.short_description = 'Пометить как свободные'