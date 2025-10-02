from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Club, ClubStaff, ClubMember, ClubAffiliation


class ClubStaffInline(admin.TabularInline):
    model = ClubStaff
    extra = 0
    fields = ['user', 'role', 'title', 'is_active', 'can_manage_members']
    readonly_fields = ['assigned_at']


class ClubMemberInline(admin.TabularInline):
    model = ClubMember
    extra = 0
    fields = ['member_account', 'membership_number', 'status', 'joined_date']
    readonly_fields = ['joined_date']


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'tenant', 'member_count', 'staff_count',
        'is_active', 'created'
    ]
    list_filter = ['is_active', 'is_public', 'created', 'tenant']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created', 'modified', 'member_count', 'staff_count']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'tenant', 'description', 'founded_date', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Address', {
            'fields': ('address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'instagram_handle', 'twitter_handle', 'youtube_url', 'linkedin_url')
        }),
        ('Settings', {
            'fields': ('is_public', 'max_members')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ClubStaffInline, ClubMemberInline]

    def member_count(self, obj):
        count = obj.member_count
        if count > 0:
            url = reverse('admin:people_contact_changelist') + f'?organization__id__exact={obj.id}'
            return format_html('<a href="{}">{} members</a>', url, count)
        return f"{count} members"
    member_count.short_description = 'Members'

    def staff_count(self, obj):
        count = obj.staff_count
        return f"{count} staff"
    staff_count.short_description = 'Staff'


@admin.register(ClubStaff)
class ClubStaffAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'club', 'role', 'organization_status', 'is_active', 'assigned_at']
    list_filter = ['role', 'is_active', 'assigned_at', 'organization_user__is_admin']
    search_fields = ['user__contact__first_name', 'user__contact__last_name', 'club__name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('club', 'user', 'role', 'is_active')
        }),
        ('Organization Integration', {
            'fields': ('organization_user', 'organization_admin_status', 'permission_hierarchy'),
            'classes': ('collapse',)
        }),
        ('Staff Details', {
            'fields': ('title', 'bio', 'specialties')
        }),
        ('Permissions', {
            'fields': ('can_manage_members', 'can_manage_schedule', 'can_view_finances')
        }),
        ('Timestamps', {
            'fields': ('assigned_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['assigned_at', 'updated_at', 'organization_admin_status', 'permission_hierarchy']

    def user_name(self, obj):
        return obj.user.contact.get_full_name()
    user_name.short_description = 'Staff Member'

    def organization_status(self, obj):
        if obj.organization_user:
            status = "Org Admin" if obj.organization_user.is_admin else "Org Member"
            return f"✓ {status}"
        return "No Org Link"
    organization_status.short_description = 'Organization Status'

    def organization_admin_status(self, obj):
        """Display organization admin status for readonly field"""
        if obj.organization_user:
            return "Yes" if obj.organization_user.is_admin else "No"
        return "No Organization User"
    organization_admin_status.short_description = 'Is Organization Admin'

    def permission_hierarchy(self, obj):
        """Display permission hierarchy level for readonly field"""
        level = obj.get_permission_hierarchy_level()
        levels = {
            100: "Superuser",
            90: "Organization Admin",
            80: "Club Owner",
            70: "Club Admin",
            50: "Instructor",
            30: "Assistant",
            10: "Basic Staff"
        }
        return f"{level} - {levels.get(level, 'Unknown')}"
    permission_hierarchy.short_description = 'Permission Level'


@admin.register(ClubMember)
class ClubMemberAdmin(admin.ModelAdmin):
    list_display = ['member_name', 'club', 'membership_number', 'status', 'joined_date']
    list_filter = ['status', 'joined_date']
    search_fields = ['member_account__member_contact__first_name', 'member_account__member_contact__last_name', 'membership_number']

    fieldsets = (
        ('Basic Information', {
            'fields': ('club', 'member_account', 'membership_number', 'status')
        }),
        ('Membership Dates', {
            'fields': ('joined_date', 'renewal_date', 'last_payment_date')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship'),
            'classes': ('collapse',)
        }),
        ('Medical Information', {
            'fields': ('medical_conditions', 'medical_clearance_date'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['joined_date', 'created_at', 'updated_at']

    def member_name(self, obj):
        return obj.member_account.member_contact.get_full_name()
    member_name.short_description = 'Member'


@admin.register(ClubAffiliation)
class ClubAffiliationAdmin(admin.ModelAdmin):
    list_display = ['club_primary', 'affiliation_type', 'club_secondary', 'is_active', 'established_at']
    list_filter = ['affiliation_type', 'is_active', 'established_at']
    search_fields = ['club_primary__name', 'club_secondary__name']

    fieldsets = (
        ('Affiliation Details', {
            'fields': ('club_primary', 'club_secondary', 'affiliation_type', 'is_active')
        }),
        ('Description', {
            'fields': ('description',)
        }),
        ('Timestamps', {
            'fields': ('established_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['established_at', 'updated_at']