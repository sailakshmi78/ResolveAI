import re

from django.core.management.base import BaseCommand

from company_docs.models import CompanyDocument, DocumentChunk


def split_into_chunks(text, max_chars=1200, overlap=200):
    text = text.replace("\r\n", "\n")
    paragraphs = [
        re.sub(r"\s+", " ", p).strip()
        for p in text.split("\n")
        if p.strip()
    ]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        while len(paragraph) > max_chars:
            piece = paragraph[:max_chars]
            if current:
                chunks.append(current)
                current = ""

            chunks.append(piece.strip())
            paragraph = paragraph[max_chars - overlap:]

        candidate = f"{current}\n{paragraph}".strip()

        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)

            tail = current[-overlap:] if current else ""
            current = f"{tail}\n{paragraph}".strip()

            if len(current) > max_chars:
                current = current[-max_chars:]

    if current:
        chunks.append(current)

    return [chunk for chunk in chunks if chunk]


class Command(BaseCommand):
    help = "Split stored handbook content into searchable chunks."

    def handle(self, *args, **options):
        documents = CompanyDocument.objects.filter(is_active=True)
        total_chunks = 0

        for document in documents:
            if not document.content.strip():
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipped empty document: {document.title}"
                    )
                )
                continue

            chunks = split_into_chunks(document.content)

            DocumentChunk.objects.filter(document=document).delete()

            DocumentChunk.objects.bulk_create([
                DocumentChunk(
                    document=document,
                    chunk_index=index,
                    content=chunk,
                )
                for index, chunk in enumerate(chunks)
            ])

            total_chunks += len(chunks)

            self.stdout.write(
                self.style.SUCCESS(
                    f"{document.title}: {len(chunks)} chunks created"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished. Total chunks created: {total_chunks}"
            )
        )
