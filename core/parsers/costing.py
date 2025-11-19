import json
from typing import List, Dict, Any, Tuple
from core.parsers.utils import convert_to_markdown
from core.models import Document, CostItem, TextChunk
from core.vectorstore import add_chunks_to_chroma
from openai import OpenAI
import re
import pandas as pd
from django.conf import settings


OPENAI_KEY = getattr(settings, "OPENAI_KEY", ".")
client = OpenAI(api_key=OPENAI_KEY)


def load_table(md_path: str) -> pd.DataFrame:
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    marker = "2. Civil works Cost summary table - 2Whole line double-track line making"
    start = text.find(marker)
    sub = text[start:]

    table_start_match = re.search(r"^\| *№ *\| *Work Item", sub, flags=re.MULTILINE)
    table_start = table_start_match.start()

    end_marker = "3. Civil works Cost summary table - 3"
    end_rel = sub.find(end_marker)
    if end_rel == -1:
        end_rel = len(sub)

    table_block = sub[table_start:end_rel]

    return table_block


def extract_cost_items_from_markdown(table_text: str) -> List[Dict[str, Any]]:

    prompt = f"""
    You are given tabular information about construction cost items extracted
    from a markdown document. The text below contains items, sub-items,
    units, quantities, unit prices in Rp, total costs in Rp, and sometimes
    a cost-type column (e.g. "local cost" / "foreign cost"):

    <<<TABLE_TEXT_START>>>
    {table_text}
    <<<TABLE_TEXT_END>>>

    Your job is to convert this into a *list* of normalized cost item objects
    with the following schema:

    Each object MUST have these keys:

    - "item_name": VARCHAR
        Description of the cost item, including parent item + sub-item where
        applicable.
        There are "items" and "sub items" in the table. Sometimes the item
        (parent) row does not contain full numeric info, but the sub-items do.
        In such cases, append the parent item name to each sub-item.
        Example:
        If parent item is "Land preparation" and sub-items are various
        industrial sectors like "industrial sector; Lt～Me",
        produce item_name values such as:
            "Land preparation industrial sector; Lt～Me"
            "Land preparation industrial sector; Me～X"
        etc.

    - "quantity": NUMERIC
        Extracted quantity for that specific row (e.g. 234876, 736.2).
        If no numeric quantity is present for that row, use null.

    - "unit_price_yen": NUMERIC
        The unit price in Yen.
        The table values are given in Rp. Convert to Yen by dividing
        the original unit price (in Rp) by 110.
        Example:
        If unit price is 15,362 Rp, then:
            unit_price_yen = 15362 / 110
        Return the numeric result (not the expression), without commas
        and without currency symbols. If not available, use null.

    - "total_cost_yen": NUMERIC
        The total cost in Yen.
        The table provides total cost in Rp (for that row). Convert it to Yen
        by dividing by 110, same as above.
        Example:
        If total cost is 6,234,876 Rp, then:
            total_cost_yen = 6234876 / 110
        Again, return the numeric result only. If no total cost is available,
        use null.

    - "cost_type": VARCHAR
        Either "foreign cost" or "local cost".
        If the row or a related column clearly specifies one of these, use it.
        Otherwise, default to "local cost".

    Important behaviour and conventions:

    1. Parent + sub-item logic:
    - If a row looks like a higher-level item (e.g. "Land preparation")
        and the following rows are more specific sub-items (e.g. different
        sectors) that contain the numeric data, each resulting object should
        have the combined item name:
        "<parent item> <sub item text>"
        Use a space or a semicolon as appropriate (e.g.
        "Land preparation industrial sector; Lt～Me").

    2. Ignore pure summary / subtotal / grand-total rows unless they clearly
    represent a single cost item comparable to others.

    3. Numeric parsing:
    - Remove thousand separators (e.g. "6,234,876" → 6234876).
    - Convert strings like "120,000.0m3" to the numeric part for quantity
        (120000.0).
    - If a cell is empty or clearly non-numeric, treat quantity/price/cost
        as null.

    4. Currency conversion:
    - ALL costs in Rp must be converted to Yen by dividing by 110.
    - Round to a reasonable number of decimals (0–2) if appropriate.

    5. Output format:
    - Return ONLY a JSON array (list) of objects, no explanations.
    - Example overall structure (the numbers here are illustrative only):

        [
        {{
            "item_name": "Land preparation industrial sector; Lt～Me",
            "quantity": 234876,
            "unit_price_yen": 139.65,
            "total_cost_yen": 56680.69,
            "cost_type": "local cost"
        }},
        {{
            "item_name": "Land preparation industrial sector; Me～X",
            "quantity": 120000,
            "unit_price_yen": 139.65,
            "total_cost_yen": 152000.00,
            "cost_type": "local cost"
        }}
        ...
        ]

    - Do NOT wrap the array in any other object.
    - Ensure the JSON is valid and parsable.
    """

    response = client.responses.create(model="gpt-5.1", input=prompt)

    raw = response.output_text.strip()

    # Parse JSON safely
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: try to extract first JSON array
        import re
        m = re.search(r"\[\s*\{.*\}\s*\]", raw, re.DOTALL)
        if not m:
            raise ValueError("Model output was not valid JSON:\n" + raw)
        data = json.loads(m.group(0))

    return data


def _is_image_line(line: str) -> bool:
    """Return True if this markdown line is an image line."""
    s = line.strip()
    return s.startswith("!") or s.startswith("![") or s.startswith("![]")


def _clean_lines(lines: List[str]) -> List[str]:
    """Remove blank and image lines, keep everything else."""
    cleaned = []
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if _is_image_line(s):
            continue
        cleaned.append(s)
    return cleaned


def chunk_markdown_by_headings(path: str, min_chars: int = 500):
    """
    Chunk the entire markdown document between headings.
    - Returns a list of dicts: [{ "title": heading_text, "text": chunk_text }, ...]
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Find all heading indices
    heading_idxs: List[int] = []
    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith("#") or s.startswith("**"):
            heading_idxs.append(idx)

    def non_image_non_blank_text(start: int, end: int) -> str:
        seg = _clean_lines(lines[start:end])
        return "\n".join(seg).strip()

    chunks: List[str] = []
    i = 0

    while i < len(heading_idxs):
        start = heading_idxs[i]
        j = i + 1

        while True:
            end = heading_idxs[j] if j < len(heading_idxs) else len(lines)
            txt = non_image_non_blank_text(start, end)
            if len(txt) >= min_chars or j >= len(heading_idxs):
                break
            j += 1

        final_text = non_image_non_blank_text(start, end)
        if final_text:
            chunks.append(final_text)
        i = j

    return chunks


def parse_costing_document(doc: Document) -> Tuple[int, int]:

    table_block = load_table(doc.path.replace(".pdf", ".md"))
    extracted_items = extract_cost_items_from_markdown(table_block)

    items_created = 0

    for idx, item in enumerate(extracted_items, start=1):
        CostItem.objects.update_or_create(document=doc,
                                          item_id = idx,
                                          defaults= dict(category=item["item_name"],
                                                         quantity=item["quantity"],
                                                         unit_cost=item["unit_price_yen"],
                                                         total_cost=item["total_cost_yen"],
                                                         cost_type= item["cost_type"]))
        items_created += 1

    chunks = chunk_markdown_by_headings(doc.path.replace(".pdf", ".md"))
    chunk_pairs = add_chunks_to_chroma(doc.id, chunks, metadata={"doc_type": doc.doc_type})

    for order, (cid, ctext) in enumerate(chunk_pairs):
        TextChunk.objects.create(document=doc, chunk_id=cid, order=order, text=ctext,
                                 embedding_dim=len(chunk_pairs[0][1]) if chunk_pairs else 0)

    return items_created, len(chunks)

