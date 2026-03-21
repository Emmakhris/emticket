from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="KBCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="kb_categories", to="organizations.department")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kb_categories", to="organizations.organization")),
            ],
            options={"unique_together": {("organization", "department", "name")}},
        ),
        migrations.CreateModel(
            name="KBArticle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("body", models.TextField()),
                ("visibility", models.CharField(choices=[("internal", "Internal"), ("public", "Public")], default="internal", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="articles", to="knowledgebase.kbcategory")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="kb_created", to=settings.AUTH_USER_MODEL)),
                ("department", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="kb_articles", to="organizations.department")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="kb_articles", to="organizations.organization")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="kb_updated", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="KBArticleFeedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("was_helpful", models.BooleanField()),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("article", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="feedback", to="knowledgebase.kbarticle")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
