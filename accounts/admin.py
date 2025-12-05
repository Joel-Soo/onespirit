from django.contrib import admin
from django.utils.html import format_html
from .models import (
    TenantAccount, MemberAccount, PaymentHistory,
    TenantAccountContact
)


class TenantAccountContactInline(admin.TabularInline):
    """Inline admin for TenantAccount-Contact relationships"""
    model = TenantAccountContact
    extra = 1
    fields = ['contact', 'role', 'is_active']
    autocomplete_fields = ['contact']


@admin.register(TenantAccount)
class TenantAccountAdmin(admin.ModelAdmin):
    """Admin interface for TenantAccount model"""
    list_display = [
        'tenant_name', 'tenant_slug', 'subscription_type', 
        'get_member_count', 'subscription_status', 'is_active', 'created_at'
    ]
    list_filter = [
        'subscription_type', 'is_active', 'account_status', 
        'subscription_start_date', 'created_at'
    ]
    search_fields = [
        'tenant_name', 'tenant_slug', 'primary_contact__first_name', 
        'primary_contact__last_name', 'primary_contact__email'
    ]
    readonly_fields = ['created_at', 'updated_at', 'get_member_count', 'subscription_status']
    autocomplete_fields = ['primary_contact', 'billing_contact']
    inlines = [TenantAccountContactInline]
    
    fieldsets = (
        ('Tenant Information', {
            'fields': ('tenant_name', 'tenant_slug', 'tenant_domain')
        }),
        ('Contact Information', {
            'fields': ('primary_contact', 'billing_contact', 'billing_email')
        }),
        ('Subscription Details', {
            'fields': (
                'subscription_type', 'subscription_start_date', 'subscription_end_date',
                'monthly_fee', 'subscription_status'
            )
        }),
        ('Limits and Configuration', {
            'fields': (
                'max_member_accounts', 'max_clubs', 'max_associations',
                'timezone', 'locale'
            ),
            'classes': ('collapse',)
        }),
        ('Status and Metadata', {
            'fields': ('account_status', 'is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('get_member_count',),
            'classes': ('collapse',)
        }),
    )
    
    def get_member_count(self, obj):
        """Display current member count"""
        if obj.pk:
            count = obj.get_member_count()
            max_count = obj.max_member_accounts
            percentage = (count / max_count * 100) if max_count > 0 else 0
            
            color = 'green' if percentage < 80 else 'orange' if percentage < 95 else 'red'
            return format_html(
                '<span style="color: {};">{} / {} ({:.1f}%)</span>',
                color, count, max_count, percentage
            )
        return 'N/A'
    get_member_count.short_description = 'Members'
    get_member_count.admin_order_field = 'member_accounts__count'
    
    def subscription_status(self, obj):
        """Display subscription status with color coding"""
        if obj.pk:
            status = obj.get_subscription_status()
            color = 'green' if status == 'active' else 'red'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, status.upper()
            )
        return 'N/A'
    subscription_status.short_description = 'Subscription Status'




@admin.register(MemberAccount)
class MemberAccountAdmin(admin.ModelAdmin):
    """Admin interface for MemberAccount model"""
    list_display = [
        'membership_number', 'get_member_name', 'tenant', 'membership_type',
        'membership_status', 'membership_start_date', 'is_active'
    ]
    list_filter = [
        'tenant', 'membership_type', 'is_active', 'membership_start_date',
        'membership_end_date', 'created_at'
    ]
    search_fields = [
        'membership_number', 'member_contact__first_name', 
        'member_contact__last_name', 'member_contact__email',
        'tenant__tenant_name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'membership_status', 
        'get_member_age', 'is_membership_active'
    ]
    autocomplete_fields = ['tenant', 'member_contact', 'primary_contact', 'billing_contact']
    
    fieldsets = (
        ('Member Information', {
            'fields': ('member_contact', 'membership_number', 'membership_type')
        }),
        ('Tenant Association', {
            'fields': ('tenant',)
        }),
        ('Contact Information', {
            'fields': ('primary_contact', 'billing_contact', 'billing_email')
        }),
        ('Membership Details', {
            'fields': (
                'membership_start_date', 'membership_end_date',
                'membership_status', 'is_membership_active'
            )
        }),
        ('Status and Metadata', {
            'fields': ('account_status', 'is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Member Details', {
            'fields': ('get_member_age',),
            'classes': ('collapse',)
        }),
    )
    
    def get_member_name(self, obj):
        """Display member's full name"""
        if obj.member_contact:
            return obj.member_contact.get_full_name()
        return 'No Contact'
    get_member_name.short_description = 'Member Name'
    get_member_name.admin_order_field = 'member_contact__last_name'
    
    def get_member_age(self, obj):
        """Display member's age"""
        if obj.member_contact:
            age = obj.member_contact.get_age()
            return f"{age} years" if age else 'Unknown'
        return 'No Contact'
    get_member_age.short_description = 'Age'
    
    def membership_status(self, obj):
        """Display membership status with color coding"""
        if obj.pk:
            status = obj.get_membership_status()
            color_map = {
                'active': 'green',
                'expired': 'red', 
                'inactive': 'gray'
            }
            color = color_map.get(status, 'black')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color, status.upper()
            )
        return 'N/A'
    membership_status.short_description = 'Status'


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PaymentHistory model"""
    list_display = [
        'get_account_info', 'payment_type', 'amount', 'currency',
        'payment_status', 'payment_date', 'payment_method'
    ]
    list_filter = [
        'payment_status', 'payment_type', 'payment_method', 
        'currency', 'payment_date', 'created_at'
    ]
    search_fields = [
        'invoice_number', 'transaction_reference', 'description',
        'account_object_id'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'get_account_display',
        'is_refund', 'get_net_amount'
    ]
    autocomplete_fields = ['created_by']
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Account Information', {
            'fields': ('account_content_type', 'account_object_id', 'get_account_display')
        }),
        ('Payment Details', {
            'fields': (
                'amount', 'currency', 'payment_date', 'due_date',
                'payment_type', 'get_net_amount', 'is_refund'
            )
        }),
        ('Payment Processing', {
            'fields': (
                'payment_method', 'payment_status', 'transaction_reference',
                'processor_fee'
            )
        }),
        ('References and Notes', {
            'fields': ('invoice_number', 'description', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_account_info(self, obj):
        """Display account information"""
        return obj.get_account_display()
    get_account_info.short_description = 'Account'
    
    def get_net_amount(self, obj):
        """Display net amount after processor fees"""
        if obj.amount and obj.processor_fee:
            net = obj.amount - obj.processor_fee
            return f"{net} {obj.currency}"
        return f"{obj.amount} {obj.currency}"
    get_net_amount.short_description = 'Net Amount'
    
    def save_model(self, request, obj, form, change):
        """Set created_by field automatically"""
        if not change:  # Only for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TenantAccountContact)
class TenantAccountContactAdmin(admin.ModelAdmin):
    """Admin interface for TenantAccountContact through model"""
    list_display = [
        'account', 'contact', 'role', 'is_active', 'added_date'
    ]
    list_filter = ['role', 'is_active', 'added_date']
    search_fields = [
        'account__tenant_name', 'contact__first_name', 
        'contact__last_name', 'contact__email'
    ]
    readonly_fields = ['added_date']
    autocomplete_fields = ['account', 'contact']




# Customize admin site headers
admin.site.site_header = 'OneSpirit Account Management'
admin.site.site_title = 'OneSpirit Admin'
admin.site.index_title = 'Account Management Dashboard'