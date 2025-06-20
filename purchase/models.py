from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Booking(models.Model):
    """
    Бронирование конкретной квартиры
    Теперь привязано к Apartment, а не ApartmentType
    """
    # Основная информация
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Клиент'
    )
    
    # ИЗМЕНЕНИЕ: Теперь бронируем конкретную квартиру
    apartment = models.ForeignKey(
        'elitka.Apartment',  # Ссылка на конкретную квартиру
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name='Квартира'
    )
    
    # Контакты клиента
    full_name = models.CharField('ФИО', max_length=200)
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Email')
    
    # Статус заявки
    STATUS_CHOICES = [
        ('pending', 'Новая заявка'),
        ('confirmed', 'Подтверждено'),
        ('completed', 'Сделка завершена'),
        ('cancelled', 'Отменено'),
    ]
    status = models.CharField(
        'Статус', 
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending'
    )
    
    # Комментарий клиента
    comment = models.TextField('Комментарий', blank=True)
    
    # Цена на момент бронирования
    price = models.DecimalField('Цена ($)', max_digits=12, decimal_places=2)
    
    # Даты
    created_at = models.DateTimeField('Дата заявки', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    # Ответ менеджера
    manager_comment = models.TextField('Ответ менеджера', blank=True)

    def __str__(self):
        return f'{self.full_name} - Кв.{self.apartment.number} ({self.get_status_display()})'

    @property
    def complex_name(self):
        return self.apartment.complex.name

    @property
    def room_name(self):
        return self.apartment.room_name

    @property
    def apartment_number(self):
        return self.apartment.number

    @property
    def floor(self):
        return self.apartment.floor

    def save(self, *args, **kwargs):
        # Автоматически берем цену из квартиры
        if not self.price:
            self.price = self.apartment.price
        
        # Если меняется статус на 'cancelled', возвращаем квартиру
        if self.pk:  # Объект уже существует
            old_booking = Booking.objects.get(pk=self.pk)
            if old_booking.status != 'cancelled' and self.status == 'cancelled':
                # Возвращаем квартиру в доступные
                self.apartment.status = 'available'
                self.apartment.save()
                # Обновляем счетчик типа квартиры
                apartment_type = self.apartment.apartment_type
                apartment_type.available_count += 1
                apartment_type.save()
        
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        При удалении бронирования возвращаем квартиру в доступные
        """
        if self.status in ['pending', 'confirmed']:
            # Возвращаем квартиру в доступные
            self.apartment.status = 'available'
            self.apartment.save()
            # Обновляем счетчик типа квартиры
            apartment_type = self.apartment.apartment_type
            apartment_type.available_count += 1
            apartment_type.save()
        
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']


class Inquiry(models.Model):
    """
    Вопросы от клиентов с привязкой к пользователю
    Может быть привязан как к типу квартиры, так и к конкретной квартире
    """
    # Привязка к пользователю (может быть NULL для анонимных вопросов)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inquiries',
        verbose_name='Пользователь',
        null=True,
        blank=True,
        help_text='Пользователь, задавший вопрос (если авторизован)'
    )
    
    # ИЗМЕНЕНИЕ: Теперь можно задать вопрос о конкретной квартире
    apartment = models.ForeignKey(
        'elitka.Apartment',
        on_delete=models.CASCADE,
        related_name='inquiries',
        verbose_name='Квартира',
        null=True,
        blank=True,
        help_text='Конкретная квартира (если вопрос о ней)'
    )
    
    # Оставляем для совместимости - вопрос о типе квартиры
    apartment_type = models.ForeignKey(
        'elitka.ApartmentType',
        on_delete=models.CASCADE,
        related_name='inquiries',
        verbose_name='Тип квартиры',
        null=True,
        blank=True,
        help_text='Тип квартиры (если вопрос общий)'
    )
    
    # Контакты (остаются для отображения и связи)
    name = models.CharField('Имя', max_length=100)
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Email', blank=True)
    
    # Вопрос
    message = models.TextField('Вопрос')
    
    # Статус
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('answered', 'Отвечен'),
        ('closed', 'Закрыт'),
    ]
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='new'
    )
    
    created_at = models.DateTimeField('Дата', auto_now_add=True)
    
    # Ответ менеджера
    answer = models.TextField('Ответ', blank=True)

    def __str__(self):
        user_info = f"от {self.user.username}" if self.user else f"от {self.name}"
        if self.apartment:
            object_info = f"кв.{self.apartment.number}"
        elif self.apartment_type:
            object_info = f"{self.apartment_type}"
        else:
            object_info = "общий вопрос"
        return f'Вопрос {user_info} о {object_info}'

    @property
    def subject_name(self):
        """Возвращает название объекта вопроса"""
        if self.apartment:
            return f"Кв.{self.apartment.number} ({self.apartment.room_name}, {self.apartment.area}м²)"
        elif self.apartment_type:
            return f"{self.apartment_type.complex.name} - {self.apartment_type.room_name}"
        return "Общий вопрос"

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['-created_at']