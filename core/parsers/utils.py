from typing import List
from datalab_sdk import DatalabClient
from datalab_sdk.models import ConvertOptions
from django.conf import settings

DATALAB_KEY = getattr(settings, "DATALAB_KEY", ".")

def simple_chunk(text: str, max_chars: int = 800) -> List[str]:
    """
    Simple character-based chunking.
    """
    text = text.replace("\r", "")
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = []

    for p in paragraphs:
        if sum(len(x) for x in current) + len(p) + 1 > max_chars:
            if current:
                chunks.append("\n".join(current))
                current = []
        current.append(p)
    if current:
        chunks.append("\n".join(current))
    return chunks


def convert_to_markdown(path_, api_key=DATALAB_KEY):

    marker_client = DatalabClient(api_key=api_key)
    options = ConvertOptions(output_format="markdown", use_llm=True)
    result = marker_client.convert(path_, options=options)
    result.save_output(path_.replace(".pdf", ".md"))

    print("Conversion to Markdown Completed!")

