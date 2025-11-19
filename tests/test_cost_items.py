# tests/test_cost_items.py
import os
import pytest
from core.models import Document, CostItem
from core.parsers import costing as costing_module


@pytest.mark.django_db
def test_cost_item_parser_uses_llm_output_to_create_rows(monkeypatch, settings):
    """
    - Ensure CostItem rows are created correctly
    """

    fake_items = [
        {
            "item_name": "Land preparation industrial sector; Lt～Me",
            "quantity": 234876,
            "unit_price_yen": 139.65,
            "total_cost_yen": 56680.69,
            "cost_type": "local cost",
        },
        {
            "item_name": "Land preparation industrial sector; Me～X",
            "quantity": 120000,
            "unit_price_yen": 139.65,
            "total_cost_yen": 152000.00,
            "cost_type": "foreign cost",
        },
    ]

    def fake_extract_cost_items_from_markdown(table_text: str):
        return fake_items

    # Patch the real function
    monkeypatch.setattr(
        costing_module,
        "extract_cost_items_from_markdown",
        fake_extract_cost_items_from_markdown,
    )

    base_dir = settings.BASE_DIR
    md_path = os.path.join(base_dir, "sample_docs", "Construction planning and costing.md")
    assert os.path.exists(md_path), f"Missing markdown test file at {md_path}"

    # Create Document referencing the markdown
    doc = Document.objects.create(
        doc_type="COSTING",
        name="Test Costing Document",
        path=md_path.replace(".md", ".pdf"),
    )

    # Run the parser
    items_created, _ = costing_module.parse_costing_document(doc)

    assert items_created == 2
    qs = CostItem.objects.filter(document=doc).order_by("item_id")
    assert qs.count() == 2

    first = qs.first()
    assert first.category == fake_items[0]["item_name"]
    assert first.quantity == fake_items[0]["quantity"]
    assert first.cost_type == fake_items[0]["cost_type"]
