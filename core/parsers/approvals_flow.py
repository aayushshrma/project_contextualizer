import os
import re
import json
import hashlib
from typing import Dict, List, Tuple, Any
import pdfplumber
from core.parsers.utils import convert_to_markdown
from openai import OpenAI
from core.models import Document, ProcessStep, TextChunk
from core.vectorstore import add_chunks_to_chroma


def parse_markdown_sections(path: str):  # chunk by sections

    sections = {}
    current_heading = None

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n").strip()

            if not line:
                continue
            if line.startswith("![]"):
                continue

            # Detect headings (#, ##, ###)
            if line.startswith("#"):
                heading_text = line.lstrip("#").strip()
                current_heading = heading_text
                sections[current_heading] = []
                continue

            # Normal content lines
            if current_heading is not None:
                sections[current_heading].append(line)

    return sections


def parse_approvals_flow(doc: Document) -> Tuple[int, int]:
    
    filepath = doc.path.replace(".pdf", ".md")
    if not os.path.exists(filepath):
        filepath = convert_to_markdown(path_=doc.path)
        
    sections = parse_markdown_sections(filepath)

    steps_id = 1
    chunks = []
    
    for heading in sections.keys():
        lines_per_heading = sections[heading]

        for line in lines_per_heading:
            ProcessStep.objects.update_or_create(document=doc,
                                                 step_id=steps_id,
                                                 defaults={"name": heading[:255],
                                                           "description": line,
                                                           "predecessor_step_ids": ""})
            steps_id+=1
        
        chunk = (" ").join(lines_per_heading)
        chunks.append(chunk)

    chunk_pairs = add_chunks_to_chroma(doc.id, chunks, metadata={"doc_type": doc.doc_type})

    for order, (cid, cemb, ctext) in enumerate(chunk_pairs):
        hashval = hashlib.md5(ctext.encode("utf-8")).hexdigest()
        TextChunk.objects.update_or_create(document=doc,
                                           text_hash=hashval,
                                           defaults={'chunk_id':cid,
                                                     'order':order,
                                                     'text':ctext,
                                                     'embedding_dim':len(cemb)})
    return steps_id, len(chunks)

