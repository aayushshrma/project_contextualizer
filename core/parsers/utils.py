from typing import List
from datalab_sdk import DatalabClient
from datalab_sdk.models import ConvertOptions
from django.conf import settings

DATALAB_KEY = getattr(settings, "DATALAB_KEY", ".")
# Is a safe way to retrieve a variable from Django settings,
# with a fallback value if the variable does not exist.
# . means current directory


def convert_to_markdown(path_, api_key=DATALAB_KEY):

    marker_client = DatalabClient(api_key=api_key)
    options = ConvertOptions(output_format="markdown", use_llm=True)
    result = marker_client.convert(path_, options=options)
    filepath_md = path_.replace(".pdf", ".md")
    result.save_output(filepath_md)

    print("Conversion to Markdown Completed!")

    return filepath_md

