
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from company_docs.models import CompanyDocument, DocumentChunk


HANDBOOK_PATH = (
    Path("knowledge_base")
    / "ResolveAI_Consolidated_Enterprise_Knowledge_Handbook_V1.md"
)

DOCUMENT_URL = (
    "https://resolveai.local/knowledge-base/consolidated-v1/"
)

MAX_CHUNK_SIZE = 1200


def split_handbook(text):
    """Split Markdown into chunks while retaining section headings."""
    sections = re.split(r"(?m)(?=^#{1,6}\s+)", text)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        heading, _, body = section.partition("\n")
        heading = heading.strip()
        paragraphs = re.split(r"\n\s*\n", body.strip())
        current = heading

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            limit = MAX_CHUNK_SIZE - len(heading) - 2

            while len(paragraph) > limit:
                piece = paragraph[:limit]
                paragraph = paragraph[limit:]

                if current.strip() != heading:
                    chunks.append(current.strip())

                chunks.append(f"{heading}\n{piece}".strip())
                current = heading

            candidate = f"{current}\n\n{paragraph}".strip()

            if len(candidate) > MAX_CHUNK_SIZE and current.strip() != heading:
                chunks.append(current.strip())
                current = f"{heading}\n\n{paragraph}"
            else:
                current = candidate

        if current.strip():
            chunks.append(current.strip())

    return chunks


class Command(BaseCommand):
    help = "Import consolidated ResolveAI Handbook V1 as the only active source."

    def handle(self, *args, **options):
        path = HANDBOOK_PATH.resolve()

        if not path.is_file():
            raise CommandError(f"Handbook file not found: {path}")

        text = path.read_text(encoding="utf-8-sig").strip()

        if not text:
            raise CommandError("The handbook file is empty.")

        chunks = split_handbook(text)

        if not chunks:
            raise CommandError("No handbook chunks were extracted.")

        with transaction.atomic():
            document, _ = CompanyDocument.objects.update_or_create(
                source_url=DOCUMENT_URL,
                defaults={
                    "title": "ResolveAI Consolidated Enterprise Knowledge Handbook V1",
                    "source_name": "Local ResolveAI Consolidated Handbook V1",
                    "license_name": "",
                    "license_url": "",
                    "content": text,
                    "last_fetched_at": timezone.now(),
                    "is_active": True,
                },
            )

            # Deactivate every other source.
            CompanyDocument.objects.exclude(
                pk=document.pk
            ).update(is_active=False)

            # Replace only V1's chunks.
            document.chunks.all().delete()

            DocumentChunk.objects.bulk_create([
                DocumentChunk(
                    document=document,
                    chunk_index=index,
                    content=content,
                )
                for index, content in enumerate(chunks)
            ])

        self.stdout.write(self.style.SUCCESS(
            f"Import successful!\n"
            f"Document ID: {document.id}\n"
            f"Document: {document.title}\n"
            f"Characters: {len(text):,}\n"
            f"Chunks created: {len(chunks)}\n"
            f"Other documents: Inactive"
        ))
