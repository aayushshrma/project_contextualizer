import os
import django

from prefect import flow, task

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "contextualizer.settings")
django.setup()

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
    from core.models import Document as DocModel
    doc = DocModel.objects.get(id=doc_id)

    if doc.doc_type == "SCHEDULE":
        entities, chunks = parse_schedule_document(doc)
    elif doc.doc_type == "COSTING":
        entities, chunks = parse_costing_document(doc)
    elif doc.doc_type == "URA_GFA":
        entities, chunks = parse_ura_circular(doc)
    elif doc.doc_type == "APPROVAL_FLOW":
        entities, chunks = parse_approvals_flow(doc)
    else:
        raise ValueError(f"Unknown doc_type: {doc.doc_type}")

    print(f"[{doc.name}] {doc.doc_type}: {entities} entities, {chunks} chunks")


@flow(name="contextualizer-extract-documents", log_prints=True)
def extract_documents_flow():
    """
    Main Prefect flow to ingest the 4 sample docs into Postgres + Chroma.
    """

    schedule_path = os.path.join(BASE_DOC_DIR, "Project schedule document.pdf")
    costing_path = os.path.join(BASE_DOC_DIR, "Construction planning and costing.pdf")
    ura_path = os.path.join(BASE_DOC_DIR, "URA-Circular on GFA area definition.pdf")
    approvals_path = os.path.join(BASE_DOC_DIR, "construction approvals -long process chart.pdf")

    # Create Document rows
    schedule_id = create_document_record(name="Project schedule", doc_type="SCHEDULE", 
                                         path=schedule_path)
    costing_id = create_document_record(name="Construction planning and costing", 
                                        doc_type="COSTING", path=costing_path)
    ura_id = create_document_record(name="URA circular GFA", doc_type="URA_GFA",
                                    path=ura_path)
    approvals_id = create_document_record(name="Construction approvals flow",
                                          doc_type="APPROVAL_FLOW", path=approvals_path)

    # Run parsers
    run_parser(schedule_id)
    run_parser(costing_id)
    run_parser(ura_id)
    run_parser(approvals_id)


if __name__ == "__main__":
    extract_documents_flow()
