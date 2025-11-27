from django.core.management.base import BaseCommand

from flows.extract_documents import extract_documents_flow


class Command(BaseCommand): 
    help = "Run the Prefect extraction flow for sample documents"  

    def handle(self, *args, **options):  
        self.stdout.write("Starting Prefect flow: extract_documents_flow")  
        extract_documents_flow()
        self.stdout.write(self.style.SUCCESS("Flow completed"))
        