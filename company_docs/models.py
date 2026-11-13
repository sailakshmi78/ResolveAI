
from django.db import models


class CompanyDocument(models.Model):
    title = models.CharField(max_length=255)
    source_name = models.CharField(max_length=255)
    source_url = models.URLField(unique=True)
    license_name = models.CharField(max_length=150, blank=True)
    license_url = models.URLField(blank=True)
    content = models.TextField(blank=True)
    last_fetched_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    document = models.ForeignKey(
        CompanyDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()

    class Meta:
        ordering = ["document_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_document_chunk",
            )
        ]

    def __str__(self):
        return f"{self.document.title} - chunk {self.chunk_index}"
