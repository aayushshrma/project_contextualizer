import os
import django

from prefect import flow, task

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contextualizer.settings")
django.setup()  # initializes Django
from core.models import Document 
from core.parsers import (parse_schedule_document, parse_costing_document,
                          parse_ura_circular, parse_approvals_flow)


BASE_DOC_DIR = os.path.abspath("sample_docs")


@task
def create_document_record(name: str, doc_type: str, path: str) -> int:
    doc, _ = Document.objects.get_or_create(name=name, doc_type=doc_type, defaults={"path": path})
    if doc.path != path:
        doc.path = path
        doc.save(update_fields=["path"])
    return doc.id


@task
def run_parser(doc_id: int):
    doc = Document.objects.get(id=doc_id)

    if doc.doc_type == "SCHEDULE":
        entities, chunks = parse_schedule_document(doc)
    elif doc.doc_type == "COSTING":
        entities, chunks = parse_costing_document(doc)
    elif doc.doc_type == "URA":
        entities, chunks = parse_ura_circular(doc)
    elif doc.doc_type == "APPROVALS":
        entities, chunks = parse_approvals_flow(doc)
    else:
        raise ValueError(f"Unknown doc_type: {doc.doc_type}")

    print(f"[{doc.name}] {doc.doc_type}: {entities} entities, {chunks} chunks")


@flow(name="contextualizer-extract-documents", log_prints=True)
def extract_documents_flow():
    """
    Main Prefect flow to ingest the sample docs into Postgres + Chroma.
    """
    doc_types = ['SCHEDULE', 'COSTING', 'URA', 'APPROVALS']
    pdf_files = [f for f in os.listdir(BASE_DOC_DIR) if f.endswith(".pdf")]

    doc_ids = []
    for file in pdf_files:
        file_path = os.path.join(BASE_DOC_DIR, file)
        for doc_type in doc_types:
            # Create Document rows
            if doc_type in file.upper():
                doc_id = create_document_record(name=file.replace(".pdf", ""), doc_type=doc_type,
                                                path=file_path)
                doc_ids.append(doc_id)
                break

    # Run parsers
    for id_ in doc_ids:
        run_parser(id_)


if __name__ == "__main__":
    extract_documents_flow()
