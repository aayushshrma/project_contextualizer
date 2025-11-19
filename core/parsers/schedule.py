import datetime as dt
from typing import Tuple
import os
import sys
import contextlib
import pdfplumber
import camelot
from core.models import Document, ScheduleTask, TextChunk
from core.vectorstore import add_chunks_to_chroma


def parse_date(raw: str | None) -> dt.date | None:
    if not raw:
        return None
    raw = str(raw).strip()
    # Expect e.g. "Wed 1/11/06" or "1/11/06"
    parts = raw.split()
    date_part = parts[-1]
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(date_part, fmt).date()
        except Exception:
            continue
    return None


@contextlib.contextmanager
def suppress_stderr():
    old_stderr = sys.stderr
    try:
        with open(os.devnull, "w") as devnull:
            sys.stderr = devnull
            yield
    finally:
        sys.stderr = old_stderr


def parse_schedule_document(doc: Document):

    chunks = []
    task_created = 0
    with suppress_stderr():
        with pdfplumber.open(doc.path) as pdf:
            for page_no, page in enumerate(pdf.pages, start=1):
                
                words = page.extract_words()

                # Find first "Finish"
                finish_word = next((w for w in words if w["text"] == "Finish"), None)

                # Find last "days"
                days_words = [w for w in words if w["text"] == "days"]
                days_word = days_words[-1] if days_words else None

                if not finish_word or not days_word:
                    print(f"Page {page_no}: keywords not found")
                    continue

                x0 = 30
                x1 = int(finish_word["x1"])
                top = int(finish_word["top"])
                bottom = int(days_word["bottom"])

                # Convert to Camelot coordinate space:
                page_height = page.height
                camelot_top = page_height - top
                camelot_bottom = page_height - bottom
                area_str = f"{x0},{camelot_top},{x1},{camelot_bottom}"

                # print(f"Page {page_no} → table_area = {area_str}")

                # Extract tables
                tables = camelot.read_pdf(doc.path, pages=str(page_no), flavor="lattice", table_areas=[area_str])
                table_df = tables[0].df

                reqd_info = table_df.iloc[0,0].split("\n")
                each_entry = []
                for idx, item in enumerate(reqd_info):
                    if str(item).isdigit() and idx+1 < len(reqd_info) and not str(reqd_info[idx+1]).replace("days", "").strip().isdigit():
                        id_ = str(item).strip()
                        task_name = str(reqd_info[idx + 1]).strip()
                        duration = int(str(reqd_info[idx + 2]).strip().split()[0])
                        start = parse_date(str(reqd_info[idx + 3]))
                        finish = parse_date(str(reqd_info[idx + 4]))

                        ScheduleTask.objects.update_or_create(document=doc,
                                                              task_id=id_,
                                                              defaults=dict(name=task_name,
                                                                            duration_days=duration,
                                                                            start_date=start,
                                                                            finish_date=finish))

                        each_entry.append(f"ID: {id_}, Task Name: {task_name}, Duration: {duration}, Start: {start}, Finish: {finish}")
                        task_created+=1
                    if len(each_entry) == 10 or len(reqd_info) == idx+1:
                        chunk = "\n".join(each_entry)
                        chunks.append(chunk)
                        each_entry = []
    
    chunk_pairs = add_chunks_to_chroma(doc.id, chunks, metadata={"doc_type": doc.doc_type})

    for order, (cid, ctext) in enumerate(chunk_pairs):
        TextChunk.objects.create(document=doc, chunk_id=cid, order=order, text=ctext,
                                 embedding_dim=len(chunk_pairs[0][1]) if chunk_pairs else 0,)

    return task_created, len(chunks)

