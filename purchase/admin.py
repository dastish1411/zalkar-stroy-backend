from django.contrib import admin
from django.contrib import messages
from .models import Booking, Inquiry


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 
        'phone', 
        'apartment_info',
        'complex_name',
        'price', 
        'status', 
        'created_at'
    ]
    list_filter = [
        'status', 
        'created_at'
    ]
    search_fields = [
        'full_name', 
        'phone', 
        'email'
    ]
    list_editable = ['status']
    readonly_fields = ['created_at', 'updated_at', 'price']
    
    fieldsets = (
        ('Клиент', {
            'fields': ('user', 'full_name', 'phone', 'email')
        }),
        ('Квартира', {
            'fields': ('apartment', 'price')
        }),
        ('Заявка', {
            'fields': ('status', 'comment', 'manager_comment')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def apartment_info(self, obj):
        if obj.apartment:
            return f"Кв.{obj.apartment.number} ({obj.apartment.room_name})"
        return "Не указана"
    apartment_info.short_description = 'Квартира'
    
    def complex_name(self, obj):
        if obj.apartment:
            return obj.apartment.complex.name
        return "Не указан"
    complex_name.short_description = 'ЖК'
    
    # Действия
    actions = [
        'mark_as_confirmed', 
        'mark_as_completed', 
        'mark_as_cancelled'
    ]
    
    def mark_as_confirmed(self, request, queryset):
        updated = 0
        for booking in queryset:
            if booking.status == 'pending':
                booking.status = 'confirmed'
                booking.save()
                updated += 1
        
        self.message_user(request, f'{updated} бронирований подтверждено')
    mark_as_confirmed.short_description = 'Подтвердить выбранные'
    
    def mark_as_completed(self, request, queryset):
        updated = 0
        for booking in queryset:
            if booking.status in ['pending', 'confirmed'] and booking.apartment:
                booking.status = 'completed'
                # Помечаем квартиру как проданную
                booking.apartment.status = 'sold'
                booking.apartment.save()
                booking.save()
                updated += 1
        
        self.message_user(request, f'{updated} сделок завершено')
    mark_as_completed.short_description = 'Завершить выбранные'
    
    def mark_as_cancelled(self, request, queryset):
        updated = 0
        for booking in queryset:
            if booking.status in ['pending', 'confirmed'] and booking.apartment:
                booking.status = 'cancelled'
                # Возвращаем квартиру в доступные
                booking.apartment.status = 'available'
                booking.apartment.save()
                # Обновляем счетчик
                apartment_type = booking.apartment.apartment_type
                apartment_type.available_count += 1
                apartment_type.save()
                booking.save()
                updated += 1
        
        self.message_user(request, f'{updated} бронирований отменено')
    mark_as_cancelled.short_description = 'Отменить выбранные'


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'phone', 
        'subject_info',
        'status', 
        'created_at'
    ]
    list_filter = [
        'status',
        'created_at'
    ]
    search_fields = [
        'name', 
        'phone', 
        'email',
        'message'
    ]
    list_editable = ['status']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Клиент', {
            'fields': ('user', 'name', 'phone', 'email')
        }),
        ('Объект вопроса', {
            'fields': ('apartment', 'apartment_type')
        }),
        ('Вопрос', {
            'fields': ('message',)
        }),
        ('Ответ', {
            'fields': ('status', 'answer')
        }),
        ('Система', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def subject_info(self, obj):
        if obj.apartment:
            return f"Кв.{obj.apartment.number}"
        elif obj.apartment_type:
            return f"{obj.apartment_type.room_name}"
        return "Общий вопрос"
    subject_info.short_description = 'Объект вопроса'
    
    # Действия
    actions = ['mark_as_answered', 'mark_as_closed']
    
    def mark_as_answered(self, request, queryset):
        updated = queryset.update(status='answered')
        self.message_user(request, f'{updated} вопросов помечено как отвеченные')
    mark_as_answered.short_description = 'Отметить как отвеченные'
    
    def mark_as_closed(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f'{updated} вопросов закрыто')
    mark_as_closed.short_description = 'Закрыть выбранные'