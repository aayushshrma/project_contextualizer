from django.db import models


class Document(models.Model):
    DOC_TYPES = [("SCHEDULE", "Project Schedule"),
                 ("COSTING", "Construction Planning & Costing"),
                 ("URA_GFA", "URA GFA Circular"),
                 ("APPROVAL_FLOW", "Construction Approvals Flow")]

    doc_type = models.CharField(max_length=32, choices=DOC_TYPES)
    name = models.CharField(max_length=255)
    path = models.FilePathField(path="", max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.doc_type})"


class ScheduleTask(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    duration_days = models.IntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    finish_date = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["document", "task_id"])]

    def __str__(self):
        return f"{self.task_id}: {self.name}"


class CostItem(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    item_id = models.CharField(max_length=64, db_index=True, blank=True)
    category = models.CharField(max_length=128, blank=True)
    quantity = models.FloatField(null=True, blank=True)
    unit_cost = models.FloatField(null=True, blank=True)
    total_cost = models.FloatField(null=True, blank=True)
    cost_type = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["document", "item_id"])]

    def __str__(self):
        return f"{self.item_id}:{self.category}"


class RegulationClause(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    question = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    measurement_basis = models.TextField(blank=True)
    clause_ref = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["document", "clause_ref"])]

    def __str__(self):
        return self.clause_ref or (self.question[:40] if self.question else "Clause")


class ProcessStep(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    step_id = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=255)
    actor = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    predecessor_step_ids = models.CharField(max_length=255, blank=True)

    class Meta:
        indexes = [models.Index(fields=["document", "step_id"])]

    def __str__(self):
        return f"{self.step_id}: {self.name}"


class TextChunk(models.Model):
    """
    Metadata for chunks stored in Chroma.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    chunk_id = models.CharField(max_length=64, unique=True)
    order = models.IntegerField()
    text = models.TextField()
    embedding_dim = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document_id}:{self.chunk_id}"

