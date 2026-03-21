from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssetType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_types", to="organizations.organization")),
            ],
            options={"unique_together": {("organization", "name")}},
        ),
        migrations.CreateModel(
            name="AssetLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("details", models.CharField(blank=True, max_length=255)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_locations", to="organizations.organization")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="organizations.site")),
            ],
            options={"unique_together": {("organization", "site", "name")}},
        ),
        migrations.CreateModel(
            name="Asset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("asset_id", models.CharField(max_length=80, unique=True)),
                ("vendor", models.CharField(blank=True, max_length=120)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("serial_number", models.CharField(blank=True, max_length=120)),
                ("location_text", models.CharField(blank=True, max_length=255)),
                ("notes", models.TextField(blank=True)),
                ("maintenance_schedule", models.JSONField(blank=True, default=dict)),
                ("in_service", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("asset_type", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="assets.assettype")),
                ("location", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="assets.assetlocation")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assets", to="organizations.organization")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="organizations.site")),
            ],
        ),
    ]
