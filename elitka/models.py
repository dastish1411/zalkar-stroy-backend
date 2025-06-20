from django.db import models
from django.contrib.auth import get_user_model
from slugify import slugify
from .utils import get_time

User = get_user_model()


class ResidentialComplex(models.Model):
    """
    Жилой комплекс - основная модель для ЖК Zalkar Stroy
    У вас будет 2 ЖК: например "ЖК Madison" и "ЖК Залкар"
    """
    name = models.CharField('Название ЖК', max_length=200)
    slug = models.SlugField('URL-адрес', max_length=220, primary_key=True, blank=True)
    description = models.TextField('Описание ЖК')
    address = models.CharField('Адрес', max_length=300)
    
    # Характеристики комплекса
    total_buildings = models.PositiveIntegerField('Количество домов', default=1)
    total_floors = models.PositiveIntegerField('Этажность', default=12)
    
    # Статус строительства
    STATUS_CHOICES = [
        ('planning', 'Планируется'),
        ('construction', 'Строится'),
        ('completed', 'Сдан'),
    ]
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='construction')
    completion_date = models.DateField('Дата сдачи', null=True, blank=True)
    
    # ИСПРАВЛЕНО: Инфраструктура как обычный текст
    infrastructure = models.TextField(
        'Инфраструктура', 
        blank=True,
        help_text='Опишите инфраструктуру ЖК: парковка, детские площадки, магазины и т.д.'
    )
    
    # Главное фото ЖК (фасад, общий вид)
    main_image = models.ImageField('Главное фото ЖК', upload_to='complexes/')
    
    # ИСПРАВЛЕНО: Геолокация как ссылка на 2GIS
    location_2gis = models.URLField(
        'Ссылка на 2GIS', 
        blank=True,
        help_text='Вставьте ссылку на местоположение в 2GIS'
    )
    
    # Системные поля
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    is_active = models.BooleanField('Активен', default=True)

    def save(self, *args, **kwargs):
        # Автоматически создаем URL из названия
        if not self.slug:
            self.slug = slugify(self.name + '-' + get_time())
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def total_apartment_types(self):
        """Сколько типов квартир в этом ЖК (должно быть 3)"""
        return self.apartment_types.filter(is_active=True).count()

    @property
    def price_range(self):
        """Диапазон цен в этом ЖК"""
        types = self.apartment_types.filter(is_active=True)
        if types.exists():
            min_price = types.order_by('price').first().price
            max_price = types.order_by('-price').first().price
            return f"${min_price:,.0f} - ${max_price:,.0f}"
        return "Цены уточняйте"

    class Meta:
        verbose_name = 'Жилой комплекс'
        verbose_name_plural = 'Жилые комплексы'
        ordering = ['-created_at']


class ComplexImage(models.Model):
    """
    Дополнительные фотографии ЖК
    Фасад, двор, инфраструктура, окружающая территория
    """
    complex = models.ForeignKey(
        ResidentialComplex, 
        on_delete=models.CASCADE, 
        related_name='images',
        verbose_name='Жилой комплекс'
    )
    image = models.ImageField('Фотография', upload_to='complexes/gallery/')
    title = models.CharField('Название фото', max_length=200, blank=True)
    description = models.TextField('Описание', blank=True)
    order = models.PositiveIntegerField('Порядок показа', default=0)

    class Meta:
        verbose_name = 'Фото ЖК'
        verbose_name_plural = 'Фотографии ЖК'
        ordering = ['order']

    def __str__(self):
        return f'{self.complex.name} - {self.title or "Фото"}'


class ApartmentType(models.Model):
    """
    Тип квартиры - основная модель для квартир
    У вас будет 6 записей: 3 типа в каждом из 2 ЖК
    
    Пример:
    - ЖК "Madison" + 1-комнатная
    - ЖК "Madison" + 2-комнатная  
    - ЖК "Madison" + 3-комнатная
    - ЖК "Залкар" + 1-комнатная
    - ЖК "Залкар" + 2-комнатная
    - ЖК "Залкар" + 3-комнатная
    """
    complex = models.ForeignKey(
        ResidentialComplex, 
        on_delete=models.CASCADE, 
        related_name='apartment_types',
        verbose_name='Жилой комплекс'
    )
    
    # Основные характеристики
    ROOM_CHOICES = [
        (1, '1-комнатная'),
        (2, '2-комнатная'),
        (3, '3-комнатная'),
    ]
    rooms = models.PositiveIntegerField('Количество комнат', choices=ROOM_CHOICES)
    area = models.DecimalField('Площадь (м²)', max_digits=8, decimal_places=2)
    
    # Фиксированная цена для этого типа в этом ЖК
    price = models.DecimalField('Цена ($)', max_digits=12, decimal_places=2)
    
    # Описание планировки
    layout_description = models.TextField('Описание планировки', blank=True)
    
    # Изображения
    main_image = models.ImageField('Главное фото', upload_to='apartment_types/')
    layout_image = models.ImageField('Планировка', upload_to='apartment_types/layouts/', blank=True)
    
    # КЛЮЧЕВЫЕ ПОЛЯ для вашей логики
    # Счетчики квартир - это то, что видит клиент!
    total_count = models.PositiveIntegerField('Всего квартир этого типа', default=0)
    available_count = models.PositiveIntegerField('Доступно для покупки', default=0)
    
    # Системные поля
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    is_active = models.BooleanField('Активен', default=True)

    @property
    def is_available(self):
        """Есть ли свободные квартиры этого типа"""
        return self.available_count > 0

    @property
    def room_name(self):
        """Название типа: "1-комнатная", "2-комнатная", "3-комнатная" """
        return f'{self.rooms}-комнатная'

    @property
    def sold_count(self):
        """Сколько квартир уже продано"""
        return self.total_count - self.available_count

    @property
    def availability_status(self):
        """Статус доступности для показа клиенту"""
        if self.available_count == 0:
            return "Все продано"
        elif self.available_count <= 5:
            return f"Осталось {self.available_count}"
        else:
            return f"Доступно {self.available_count}"

    def __str__(self):
        return f'{self.complex.name} - {self.room_name} ({self.area}м²)'

    class Meta:
        verbose_name = 'Тип квартиры'
        verbose_name_plural = 'Типы квартир'
        ordering = ['complex', 'rooms']
        # Важно! В одном ЖК может быть только один тип каждой комнатности
        unique_together = ['complex', 'rooms']


class ApartmentTypeImage(models.Model):
    """
    Фотографии интерьеров для каждого типа квартиры
    Здесь будут ваши 6 фото на каждый тип: гостиная, спальня, кухня, ванная и т.д.
    """
    apartment_type = models.ForeignKey(
        ApartmentType, 
        on_delete=models.CASCADE, 
        related_name='images',
        verbose_name='Тип квартиры'
    )
    image = models.ImageField('Фото интерьера', upload_to='apartment_types/gallery/')
    title = models.CharField('Название', max_length=200, blank=True)
    room_name = models.CharField(
        'Какая комната', 
        max_length=100, 
        blank=True,
        help_text='Гостиная, Спальня, Кухня, Ванная, Прихожая и т.д.'
    )
    order = models.PositiveIntegerField('Порядок показа', default=0)

    class Meta:
        verbose_name = 'Фото интерьера'
        verbose_name_plural = 'Фотографии интерьеров'
        ordering = ['order']

    def __str__(self):
        room_info = self.room_name or self.title or "Фото"
        return f'{self.apartment_type} - {room_info}'


class Favorite(models.Model):
    """
    Избранные квартиры для зарегистрированных пользователей
    Клиент может добавлять типы квартир в избранное
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    apartment_type = models.ForeignKey(
        ApartmentType,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Тип квартиры'
    )
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.apartment_type}'

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные квартиры'
        ordering = ['-created_at']
        # Один пользователь не может добавить один тип дважды
        unique_together = ['user', 'apartment_type']


class Review(models.Model):
    """
    Отзывы клиентов о жилых комплексах
    Только о ЖК в целом, не о конкретных квартирах
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Пользователь'
    )
    complex = models.ForeignKey(
        ResidentialComplex,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Жилой комплекс',
        to_field='slug'  # Связь по slug полю
    )
    rating = models.PositiveIntegerField(
        'Рейтинг',
        choices=[(i, f'{i} звезд') for i in range(1, 6)],
        default=5
    )
    text = models.TextField('Текст отзыва')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    is_approved = models.BooleanField('Одобрен модератором', default=False)

    def __str__(self):
        return f'Отзыв от {self.user.username} о {self.complex.name} ({self.rating}★)'

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        # Один пользователь - один отзыв на ЖК
        unique_together = ['user', 'complex']


# НАЙДИТЕ модель Apartment в файле elitka/models.py и ЗАМЕНИТЕ на это:

class Apartment(models.Model):
    """
    Конкретная квартира с номером, этажом и статусом
    Связана с типом квартиры (ApartmentType)
    """
    # Связь с типом квартиры
    apartment_type = models.ForeignKey(
        ApartmentType,
        on_delete=models.CASCADE,
        related_name='apartments',
        verbose_name='Тип квартиры'
    )
    
    # Основная информация о квартире
    number = models.PositiveIntegerField('Номер квартиры')
    floor = models.PositiveIntegerField('Этаж')
    position = models.PositiveIntegerField(
        'Позиция на этаже', 
        help_text='1,2,3,4,5,6 - позиция квартиры на этаже'
    )
    
    # Статус квартиры
    STATUS_CHOICES = [
        ('available', 'Свободна'),
        ('booked', 'Забронирована'),
        ('sold', 'Продана'),
    ]
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    
    # Дополнительные характеристики
    is_corner = models.BooleanField('Угловая квартира', default=False)
    is_vip = models.BooleanField('VIP квартира', default=False)
    view_direction = models.CharField(
        'Сторона света',
        max_length=50,
        blank=True,
        help_text='Север, Юг, Восток, Запад'
    )
    
    # Индивидуальная цена (если отличается от базовой)
    custom_price = models.DecimalField(
        'Индивидуальная цена ($)',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Если не указана, берется цена из типа квартиры'
    )
    
    # Системные поля
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    @property
    def complex(self):
        """Возвращает ЖК этой квартиры"""
        return self.apartment_type.complex

    @property
    def room_count(self):
        """Количество комнат"""
        return self.apartment_type.rooms

    @property
    def area(self):
        """Площадь квартиры"""
        return self.apartment_type.area

    @property
    def price(self):
        """Итоговая цена с учетом индивидуальных надбавок"""
        base_price = self.apartment_type.price
        
        if self.custom_price:
            return self.custom_price
            
        # Добавляем надбавки для особых квартир
        price = base_price
        if self.is_corner:
            price += 5000  # +$5000 за угловую
        if self.is_vip:
            price += 3000  # +$3000 за VIP
            
        return price

    @property
    def room_name(self):
        """Название типа квартиры"""
        return self.apartment_type.room_name

    def __str__(self):
        return f'Кв.{self.number} ({self.room_name}, {self.area}м², {self.get_status_display()})'

    class Meta:
        verbose_name = 'Квартира'
        verbose_name_plural = 'Квартиры'
        ordering = ['apartment_type__complex', 'floor', 'position']
        # ИСПРАВЛЕНО: номер квартиры уникален в рамках типа квартиры
        unique_together = [['apartment_type', 'number']]