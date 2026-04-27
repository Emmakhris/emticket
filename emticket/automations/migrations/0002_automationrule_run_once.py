from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('automations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='automationrule',
            name='run_once',
            field=models.BooleanField(default=True),
        ),
    ]
