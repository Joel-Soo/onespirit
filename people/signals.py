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
    from .models import UserProfile

    try:
        user_profile = UserProfile.objects.get(user=user)
        contact = user_profile.contact

        # Set organization if contact doesn't have one, or if this is a higher priority org
        if not contact.organization:
            contact.organization = organization
            contact.save(update_fields=['organization'])
    except UserProfile.DoesNotExist:
        # User exists in django-organizations but not in our UserProfile system
        # This is normal for admin users who may not have Contact records
        pass


@receiver(user_removed, sender=Organization)
def sync_contact_organization_on_remove(sender, user, organization, **kwargs):
    """
    Handle Contact.organization cleanup when user is removed from organization.
    
    Reassigns to another organization if user has other memberships.
    """
    from .models import UserProfile
    
    try:
        user_profile = UserProfile.objects.get(user=user)
        contact = user_profile.contact
        
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
    except UserProfile.DoesNotExist:
        pass


@receiver(owner_changed, sender=Organization)
def update_owner_permissions(sender, organization, old_owner, new_owner, **kwargs):
    """
    Update UserProfile permissions when organization ownership changes.
    
    Ensures UserProfile permission levels reflect organization ownership.
    """
    from .models import UserProfile
    
    # Update old owner's permissions if they have UserProfile
    if old_owner:
        try:
            old_user_profile = UserProfile.objects.get(user=old_owner)
            # Demote from admin if they're not admin in other orgs
            other_admin_orgs = OrganizationUser.objects.filter(
                user=old_owner, is_admin=True
            ).exclude(organization=organization)
            
            if not other_admin_orgs.exists() and old_user_profile.permissions_level == 'admin':
                old_user_profile.permissions_level = 'owner'  # Demote to regular owner
                old_user_profile.save(update_fields=['permissions_level'])
        except UserProfile.DoesNotExist:
            pass
    
    # Update new owner's permissions if they have UserProfile  
    if new_owner:
        try:
            new_user_profile = UserProfile.objects.get(user=new_owner)
            # Promote to admin level if not already
            if new_user_profile.permissions_level not in ['admin']:
                new_user_profile.permissions_level = 'admin'
                new_user_profile.is_club_owner = True
                new_user_profile.save(update_fields=['permissions_level', 'is_club_owner'])
        except UserProfile.DoesNotExist:
            pass


@receiver(post_save, sender=OrganizationUser)
def sync_loginuser_permissions(sender, instance, created, **kwargs):
    """
    Sync UserProfile permissions when OrganizationUser admin status changes.
    
    Ensures bidirectional sync between django-organizations and UserProfile permissions.
    """
    from .models import UserProfile
    
    try:
        user_profile = UserProfile.objects.get(user=instance.user)
        
        if instance.is_admin:
            # Promote UserProfile to admin if they're org admin
            if user_profile.permissions_level not in ['admin']:
                user_profile.permissions_level = 'admin'
                user_profile.is_club_owner = True
                user_profile.save(update_fields=['permissions_level', 'is_club_owner'])
        else:
            # Check if user is admin in any other organizations
            is_admin_elsewhere = OrganizationUser.objects.filter(
                user=instance.user, is_admin=True
            ).exclude(id=instance.id).exists()
            
            if not is_admin_elsewhere and user_profile.permissions_level == 'admin':
                # Demote from admin if not admin elsewhere
                user_profile.permissions_level = 'owner'
                user_profile.save(update_fields=['permissions_level'])
                
    except UserProfile.DoesNotExist:
        pass