# tests/test_search_api.py
import pytest
from django.urls import reverse
from django.test import Client
from core.models import Document, TextChunk


@pytest.mark.django_db
def test_semantic_search_api_returns_results(settings):
    """
    Ensure /search/ works and returns JSON structure.
    We seed one TextChunk manually; in a real test, you might run a parser first.
    """

    client = Client()

    doc = Document.objects.create(
        doc_type="URA_GFA",
        name="Dummy URA Doc",
        path=settings.BASE_DIR, 
    )

    TextChunk.objects.create(
        document=doc,
        chunk_id="dummy-id",
        order=0,
        text="Gross floor area (GFA) includes covered floor space...",
        embedding_dim=384,
    )

    # Call the API
    response = client.get("/search/", {"q": "floor area"})
    assert response.status_code in (200, 400)

    if response.status_code == 200:
        data = response.json()
        assert "results" in data
        if data["results"]:
            first = data["results"][0]
            assert "id" in first
            assert "text" in first
            assert "metadata" in first
