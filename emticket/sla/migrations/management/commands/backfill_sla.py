from django.core.management.base import BaseCommand
from tickets.models import Ticket
from sla.services import initialize_or_recompute_sla

class Command(BaseCommand):
    help = "Backfill SLAStatus for existing tickets."

    def handle(self, *args, **options):
        count = 0
        for t in Ticket.objects.select_related("site").all().iterator(chunk_size=200):
            initialize_or_recompute_sla(t)
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Backfilled SLA for {count} tickets"))
