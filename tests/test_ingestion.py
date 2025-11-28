import os
import pytest
from core.models import Document, ScheduleTask, TextChunk
from core.parsers.schedule import parse_schedule_document
from core.vectorstore import search_similar


@pytest.mark.django_db
def test_schedule_ingestion_creates_tasks_and_chunks(settings):
    """
    Integration test:
    - Parse the sample schedule PDF
    - Check tasks are written to Postgres
    - Check chunks are embedded into Chroma
    """

    base_dir = settings.BASE_DIR
    pdf_path = os.path.join(base_dir, "sample_docs", "Project schedule document.pdf")
    assert os.path.exists(pdf_path), f"Missing test PDF at {pdf_path}"

    # Create a Document row
    doc = Document.objects.create(
        doc_type="SCHEDULE",
        name="Test Schedule Document",
        path=pdf_path,
    )

    # Run parser
    num_tasks, num_chunks = parse_schedule_document(doc)

    # DB assertions
    assert num_tasks > 0
    assert num_chunks > 0

    assert ScheduleTask.objects.filter(document=doc).count() == num_tasks
    assert TextChunk.objects.filter(document=doc).count() == num_chunks

    # Simple semantic search check
    res = search_similar("start date", n_results=3)
    assert "ids" in res and res["ids"]
    assert "documents" in res and res["documents"]
