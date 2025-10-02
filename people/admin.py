from django.contrib import admin
from .models import Contact, LoginUser


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'email', 'mobile_number', 'created_at', 'is_active']
    list_filter = ['created_at', 'is_active']
    search_fields = ['first_name', 'last_name', 'email']
    ordering = ['last_name', 'first_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'email', 'mobile_number')
        }),
        ('Address', {
            'fields': ('address',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoginUser)  
class LoginUserAdmin(admin.ModelAdmin):
    list_display = ['contact', 'user', 'permissions_level', 'is_club_owner', 'is_club_staff']
    list_filter = ['permissions_level', 'is_club_owner', 'is_club_staff', 'can_create_clubs']
    search_fields = ['contact__first_name', 'contact__last_name', 'user__username']
    readonly_fields = ['created_at', 'updated_at', 'last_login_attempt']
    
    fieldsets = (
        ('User Relationships', {
            'fields': ('user', 'contact')
        }),
        ('Permissions', {
            'fields': ('permissions_level', 'is_club_owner', 'is_club_staff', 
                      'can_create_clubs', 'can_manage_members')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_login_attempt'),
            'classes': ('collapse',)
        }),
    )
