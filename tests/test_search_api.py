
import os
import shutil
import pytest
from django.test import Client                                                                                                                  
from core.vectorstore import add_chunks_to_chroma

@pytest.mark.django_db
def test_semantic_search_integration(tmp_path, settings):
    # Point CHROMA_DIR to a temp directory
    test_chroma_dir = tmp_path / "chroma"
    settings.BASE_DIR = tmp_path  # because CHROMA_DIR uses BASE_DIR

    # Seed a chunk into Chroma
    chunks = ["Gross floor area (GFA) includes covered floor space..."]
    add_chunks_to_chroma(document_id=1, chunks=chunks)

    # Call the search API
    client = Client()
    response = client.get("/search/", {"q": "floor area"})
    assert response.status_code == 200

    data = response.json()
    assert "results" in data
    assert len(data["results"]) >= 1

    first = data["results"][0]
    assert "Gross floor area" in first["text"]

    # clean up Chroma dir
    shutil.rmtree(test_chroma_dir, ignore_errors=True)
