from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=20, unique=True)  # e.g. KATH
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Site(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sites")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20)  # e.g. MAIN, WARD-A
    address = models.TextField(blank=True)

    class Meta:
        unique_together = ("organization", "code")

    def __str__(self) -> str:
        return f"{self.organization.code}:{self.code} - {self.name}"


class Department(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)  # IT, HR, LAB, BIOMED
    is_confidential = models.BooleanField(default=False)

    class Meta:
        unique_together = ("organization", "code")

    def __str__(self) -> str:
        return f"{self.organization.code}:{self.code}"


class Team(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="teams")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="teams")
    name = models.CharField(max_length=255)
    email_alias = models.EmailField(blank=True)  # future email routing
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("organization", "department", "name")

    def __str__(self) -> str:
        return f"{self.department.code} - {self.name}"


class WorkingCalendar(models.Model):
    """
    Used for SLA calculations: weekly hours + holidays per site.
    weekly_hours example:
      {"mon":[["08:00","17:00"]], "tue":[["08:00","17:00"]], ...}
    holidays example:
      ["2026-01-01", "2026-03-06"]
    """
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name="calendar")
    timezone = models.CharField(max_length=64, default="Africa/Accra")
    weekly_hours = models.JSONField(default=dict, blank=True)
    holidays = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"Calendar({self.site.organization.code}:{self.site.code})"
