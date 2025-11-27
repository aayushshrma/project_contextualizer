import re
from typing import Dict, List, Tuple, Any
import pdfplumber
import hashlib
from core.parsers.utils import convert_to_markdown
from core.models import Document, RegulationClause, TextChunk
from core.vectorstore import add_chunks_to_chroma


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


def extract_qa_from_ura_md(path: str) -> Dict[str, str]:
    """
    Extract all questions with their answers.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    q_indices: List[Tuple[int, int]] = []
    for i, line in enumerate(lines):
        s = line.strip()
        m = re.match(r'^[#\s]*\**Q([1-9][0-9]?)\.', s)
        if m:
            qn = int(m.group(1))
            q_indices.append((i, qn))

    qa: Dict[str, str] = {}

    for idx, (line_idx, qn) in enumerate(q_indices):
        raw = lines[line_idx].strip()
        q_text = re.sub(r'^#+\s*', '', raw).strip()
        q_text = re.sub(r'\*\*(Q\d+)\.\*\*', r'\1.', q_text)
        if q_text.startswith("**") and q_text.endswith("**"):
            q_text = q_text[2:-2].strip()
        q_text = q_text.strip("* ").strip()

        # Determine answer range
        if idx + 1 < len(q_indices):
            next_q_line = q_indices[idx + 1][0]
        else:
            next_q_line = len(lines)

        answer_lines: List[str] = []

        for j in range(line_idx + 1, next_q_line):
            s = lines[j].strip()
            if s.startswith("#"):
                break
            answer_lines.append(lines[j])

        # Clean and join
        answer_block = _clean_lines(answer_lines)
        ans_text = " ".join(answer_block)
        ans_text = re.sub(r"\s+", " ", ans_text).strip()

        qa[q_text] = ans_text

    return qa


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


def parse_ura_circular(doc:Document) -> Tuple[int, int]:
    """
    Returns (qa_dict, chunks_list).
    """
    qa = extract_qa_from_ura_md(doc.path.replace(".pdf", ".md"))
    chunks = chunk_markdown_by_headings(doc.path.replace(".pdf", ".md"), min_chars=500)

    clause_ref = 1
    for ques, ans in qa.items():
        RegulationClause.objects.update_or_create(document=doc,
                                                  clause_ref=clause_ref,
                                                  defaults={"question":ques,
                                                            "answer":ans,
                                                            "measurement_basis":""})
        clause_ref += 1

    chunk_pairs = add_chunks_to_chroma(doc.id, chunks, metadata={"doc_type": doc.doc_type})

    for order, (cid, cemb, ctext) in enumerate(chunk_pairs):
        hashval = hashlib.md5(ctext.encode("utf-8")).hexdigest()
        TextChunk.objects.update_or_create(document=doc,
                                           text_hash=hashval,
                                           defaults={'chunk_id':cid,
                                                     'order':order,
                                                     'text':ctext,
                                                     'embedding_dim':len(cemb)})
    return clause_ref, len(chunks)
