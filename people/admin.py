from django.contrib import admin
from .models import Contact, UserProfile


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


@admin.register(UserProfile)  
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['contact', 'user', 'is_system_admin', 'is_club_owner_display']
    list_filter = ['is_system_admin', 'can_create_clubs', 'can_manage_members']
    search_fields = ['contact__first_name', 'contact__last_name', 'user__username']
    readonly_fields = ['is_club_owner_display', 'created_at', 'updated_at', 'last_login_attempt']
    
    fieldsets = (
        ('User Relationships', {
            'fields': ('user', 'contact')
        }),
        ('Permissions', {
            'fields': ('is_system_admin', 'is_club_owner_display',
                      'can_create_clubs', 'can_manage_members')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_login_attempt'),
            'classes': ('collapse',)
        }),
    )

    def is_club_owner_display(self, obj):
        """Display method for is_club_owner in admin."""
        return obj.is_club_owner()
    is_club_owner_display.short_description = 'Is Club Owner'
    is_club_owner_display.boolean = True
