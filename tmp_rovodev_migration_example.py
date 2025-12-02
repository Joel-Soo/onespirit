# Generated migration example for converting ClubStaff.user to ClubStaff.contact

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0005_remove_is_club_owner_field'),
        ('clubs', '0003_add_club_name_uniqueness_constraint'),
    ]

    operations = [
        # Step 1: Remove the existing constraint and index that reference the user field
        migrations.RemoveConstraint(
            model_name='clubstaff',
            name='unique_staff_assignment_per_club',
        ),
        migrations.RemoveIndex(
            model_name='clubstaff',
            name='clubs_clubs_user_id_18f863_idx',
        ),
        
        # Step 2: Remove the user field
        migrations.RemoveField(
            model_name='clubstaff',
            name='user',
        ),
        
        # Step 3: Add the contact field
        migrations.AddField(
            model_name='clubstaff',
            name='contact',
            field=models.ForeignKey(
                help_text='Contact assigned to club staff role',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='club_assignments',
                to='people.contact'
            ),
        ),
        
        # Step 4: Recreate the constraint and index with the new field
        migrations.AddIndex(
            model_name='clubstaff',
            index=models.Index(
                fields=['contact', 'is_active'], 
                name='clubs_clubs_contact_cd30f0_idx'
            ),
        ),
        migrations.AddConstraint(
            model_name='clubstaff',
            constraint=models.UniqueConstraint(
                fields=('contact', 'club', 'role'),
                name='unique_staff_assignment_per_club'
            ),
        ),
    ]