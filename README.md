📘 Project Contextualizer Pipeline — README.md

An end-to-end extraction, parsing, embedding, and semantic search pipeline for construction & real-estate documents built with Django, Prefect 3, PostgreSQL, ChromaDB, and Sentence Transformers.

🏗️ 1. Overview

This project provides a full pipeline to:

Upload real estate / construction documents

Parse structured information (schedule tasks, cost items, clauses, process steps)

Generate text chunks + embeddings

Store them in:

PostgreSQL (structured data)

ChromaDB (vector embeddings)

Expose a Semantic Search API (/search/?q=)

⚡ It combines Django (web + DB), Prefect 3 (orchestration), Chroma (vector DB), and Sentence Transformers (embeddings).

📂 2. Project Structure
project_contextualizer/
│
├── core/                 # Models, parsers, vector store
├── flows/                # Prefect extraction flow
├── sample_docs/          # The 4 input PDFs + their .md versions
├── contextualizer/       # Django settings
├── tests/                # Pytest tests
├── manage.py
└── requirements.txt

🛠️ 3. Requirements
Install Python & system packages
sudo apt update
sudo apt install python3.12 python3.12-venv python3-dev build-essential
sudo apt install postgresql postgresql-contrib

Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

Install dependencies
pip install -r requirements.txt

🔐 4. Configure API Keys

## 🔐 Environment Variables

All secrets must be stored in a `.env` file at the project root:

OPENAI_KEY → for LLM extraction of Cost Items

DATALAB_KEY → used internally during parsing & utilities (Currently, markdown versions of files are available in sample_docs, therefore can be skipped)

🔒 Do not commit secrets. Use environment variables in production.

🗄️ 5. Setup PostgreSQL
Create user & database
sudo -u postgres psql


In the psql prompt:

CREATE USER contextualizer_user WITH PASSWORD 'contextualizer_pass';
ALTER ROLE contextualizer_user CREATEDB;
CREATE DATABASE contextualizer_db OWNER contextualizer_user;
\q

Update Django DATABASES

In settings.py:

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "contextualizer_db",
        "USER": "contextualizer_user",
        "PASSWORD": "contextualizer_pass",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

🧱 6. Initialize Database
python manage.py makemigrations
python manage.py migrate


Create admin user:

python manage.py createsuperuser

🤖 7. Running the Extraction Pipeline (Prefect 3)

This project includes a Prefect flow:

flows/extract_documents.py


Run it using the custom Django command:

python manage.py run_extraction_flow


What this does:

Loads 4 sample documents

Applies specific parsers:

Schedule parser

Costing parser (LLM-based)

URA GFA Circular parser

Approval Flow parser

Inserts structured entities into PostgreSQL

Generates chunks + embeddings into ChromaDB

📸 8. Screenshots (Placeholders)

Add actual screenshots when running the project.

📌 Screenshot 1: Django Admin — Documents Loaded
![alt text](<Screenshot from 2025-11-20 02-24-22.png>)

📌 Screenshot 2: Schedule Tasks in PostgreSQL
![alt text](<Screenshot from 2025-11-20 02-25-22.png>)

📌 Screenshot 3: Cost Items Parsed
![alt text](<Screenshot from 2025-11-20 02-26-02.png>)

📌 Screenshot 4: ChromaDB Collection Browser
![alt text](<Screenshot from 2025-11-20 02-32-46.png>)

📌 Screenshot 6: Semantic Search JSON API Response
![alt text](<Screenshot from 2025-11-20 02-28-59.png>)

🔍 9. Semantic Search API

After running the extraction flow, start Django:

python manage.py runserver


Use semantic search:

http://127.0.0.1:8000/search/?q=what%20is%20gfa


Example JSON response:

{
  "results": [
    {
      "id": "chunk_123",
      "text": "Gross Floor Area (GFA) refers to...",
      "metadata": {
        "doc_type": "URA_GFA",
        "order": 4
      }
    }
  ]
}


There is also a search UI:

http://127.0.0.1:8000/search-ui/

🧪 10. Running Tests

Tests use pytest + pytest-django.

Run:

pytest -vv


Tests include:

Ingestion test (test_ingestion.py)

CostItem parser test (test_cost_items.py)

Search API test (test_search_api.py)

🧹 11. Clearing Data Between Runs
Clear PostgreSQL
python manage.py shell

from core.models import *
ScheduleTask.objects.all().delete()
CostItem.objects.all().delete()
RegulationClause.objects.all().delete()
ProcessStep.objects.all().delete()
TextChunk.objects.all().delete()
Document.objects.all().delete()

Clear ChromaDB
python manage.py shell

import shutil, os
from django.conf import settings

shutil.rmtree(os.path.join(settings.BASE_DIR, "chroma_storage"), ignore_errors=True)

🚀 12. Optional: Deploy Prefect Deployment

Create a deployment:

prefect deployment build flows/extract_documents.py:extract_documents_flow -n ingestion
prefect deployment apply extract_documents_flow-deployment.yaml


Run:

prefect deployment run 'extract_documents_flow/ingestion'

🧩 13. Folder Requirements for Parsing

Ensure these files exist under /sample_docs/:

Project schedule document.pdf
Construction planning and costing.pdf
URA-Circular on GFA area definition.pdf
construction approvals -long process chart.pdf


Costing requires matching .md files:

Construction planning and costing.md

🎉 14. You’re Ready!

You now have a fully working:

End-to-end extraction pipeline

Django web application

Prefect orchestration

PostgreSQL relational store

ChromaDB vector store

Semantic search API

Automated pytest test suite