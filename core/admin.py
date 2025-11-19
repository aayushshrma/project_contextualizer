from django.contrib import admin
from .models import (Document, ScheduleTask, CostItem,
                     RegulationClause, ProcessStep, TextChunk)

admin.site.register(Document)
admin.site.register(ScheduleTask)
admin.site.register(CostItem)
admin.site.register(RegulationClause)
admin.site.register(ProcessStep)
admin.site.register(TextChunk)
