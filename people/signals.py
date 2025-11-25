"""
Signal handlers for organization awareness in people app models.
Sync Contact.organization with django-organizations membership changes.
"""

from django.dispatch import receiver
from django.db.models.signals import post_save
from organizations.signals import user_added, user_removed, owner_changed
from organizations.models import Organization, OrganizationUser


@receiver(user_added, sender=Organization)
def sync_contact_organization_on_add(sender, user, organization, **kwargs):
    """
    Update Contact.organization when user is added to organization.

    This ensures Contact model stays in sync with django-organizations membership.
    """
    from .models import LoginUser

    try:
        login_user = LoginUser.objects.get(user=user)
        contact = login_user.contact

        # Set organization if contact doesn't have one, or if this is a higher priority org
        if not contact.organization:
            contact.organization = organization
            contact.save(update_fields=['organization'])
    except LoginUser.DoesNotExist:
        # User exists in django-organizations but not in our LoginUser system
        # This is normal for admin users who may not have Contact records
        pass


@receiver(user_removed, sender=Organization)
def sync_contact_organization_on_remove(sender, user, organization, **kwargs):
    """
    Handle Contact.organization cleanup when user is removed from organization.
    
    Reassigns to another organization if user has other memberships.
    """
    from .models import LoginUser
    
    try:
        login_user = LoginUser.objects.get(user=user)
        contact = login_user.contact
        
        if contact.organization == organization:
            # Find other organization memberships for this user
            other_orgs = OrganizationUser.objects.filter(
                user=user
            ).exclude(
                organization=organization
            ).select_related('organization')
            
            if other_orgs.exists():
                # Assign to first remaining organization
                contact.organization = other_orgs.first().organization
            else:
                # No other organization memberships, clear organization
                contact.organization = None
                
            contact.save(update_fields=['organization'])
    except LoginUser.DoesNotExist:
        pass


@receiver(owner_changed, sender=Organization)
def update_owner_permissions(sender, organization, old_owner, new_owner, **kwargs):
    """
    Update LoginUser permissions when organization ownership changes.
    
    Ensures LoginUser permission levels reflect organization ownership.
    """
    from .models import LoginUser
    
    # Update old owner's permissions if they have LoginUser
    if old_owner:
        try:
            old_login_user = LoginUser.objects.get(user=old_owner)
            # Demote from admin if they're not admin in other orgs
            other_admin_orgs = OrganizationUser.objects.filter(
                user=old_owner, is_admin=True
            ).exclude(organization=organization)
            
            if not other_admin_orgs.exists() and old_login_user.permissions_level == 'admin':
                old_login_user.permissions_level = 'owner'  # Demote to regular owner
                old_login_user.save(update_fields=['permissions_level'])
        except LoginUser.DoesNotExist:
            pass
    
    # Update new owner's permissions if they have LoginUser  
    if new_owner:
        try:
            new_login_user = LoginUser.objects.get(user=new_owner)
            # Promote to admin level if not already
            if new_login_user.permissions_level not in ['admin']:
                new_login_user.permissions_level = 'admin'
                new_login_user.save(update_fields=['permissions_level'])
        except LoginUser.DoesNotExist:
            pass


@receiver(post_save, sender=OrganizationUser)
def sync_loginuser_permissions(sender, instance, created, **kwargs):
    """
    Sync LoginUser permissions when OrganizationUser admin status changes.
    
    Ensures bidirectional sync between django-organizations and LoginUser permissions.
    """
    from .models import LoginUser
    
    try:
        login_user = LoginUser.objects.get(user=instance.user)
        
        if instance.is_admin:
            # Promote LoginUser to admin if they're org admin
            if login_user.permissions_level not in ['admin']:
                login_user.permissions_level = 'admin'
                login_user.save(update_fields=['permissions_level'])
        else:
            # Check if user is admin in any other organizations
            is_admin_elsewhere = OrganizationUser.objects.filter(
                user=instance.user, is_admin=True
            ).exclude(id=instance.id).exists()
            
            if not is_admin_elsewhere and login_user.permissions_level == 'admin':
                # Demote from admin if not admin elsewhere
                login_user.permissions_level = 'owner'
                login_user.save(update_fields=['permissions_level'])
                
    except LoginUser.DoesNotExist:
        pass