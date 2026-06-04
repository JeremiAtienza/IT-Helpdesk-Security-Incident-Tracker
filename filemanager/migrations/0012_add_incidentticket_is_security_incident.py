from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('filemanager', '0011_userprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='incidentticket',
            name='is_security_incident',
            field=models.BooleanField(default=False),
        ),
    ]
