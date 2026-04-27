import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0001_initial'),
        ('tickets', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CannedResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('body', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='canned_responses', to='organizations.department')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='canned_responses', to='organizations.organization')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
    ]
