from django.core.management.base import BaseCommand
from django.utils import timezone
from bs4 import BeautifulSoup
from requests import RequestException
import requests

from company_docs.models import CompanyDocument


HANDBOOK_LICENSE = "CC BY-SA 4.0"
HANDBOOK_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"

SOURCES = [
    {
        "title": "GitLab Handbook Usage",
        "url": "https://handbook.gitlab.com/handbook/about/handbook-usage/",
    },
    {
        "title": "GitLab IT Handbook",
        "url": "https://handbook.gitlab.com/handbook/it/",
    },
    {
        "title": "GitLab Support Handbook",
        "url": "https://handbook.gitlab.com/handbook/support/",
    },
]


class Command(BaseCommand):
    help = "Fetch public GitLab handbook pages into the database."

    def handle(self, *args, **options):
        success_count = 0

        for source in SOURCES:
            url = source["url"]
            self.stdout.write(f"Fetching: {url}")

            try:
                response = requests.get(
                    url,
                    headers={
                        "User-Agent": "ResolveAI educational document indexer"
                    },
                    timeout=20,
                )
                response.raise_for_status()

                content_type = response.headers.get(
                    "Content-Type", ""
                ).lower()

                if "text/html" not in content_type:
                    self.stderr.write(
                        self.style.WARNING(f"Skipped non-HTML page: {url}")
                    )
                    continue

                soup = BeautifulSoup(response.text, "html.parser")

                for element in soup.select(
                    "script, style, nav, footer, header, noscript, svg"
                ):
                    element.decompose()

                main_content = (
                    soup.find("main")
                    or soup.find("article")
                    or soup.body
                )

                if main_content is None:
                    self.stderr.write(
                        self.style.WARNING(f"No readable content: {url}")
                    )
                    continue

                content = main_content.get_text(
                    separator="\n",
                    strip=True,
                )

                if len(content) < 100:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Too little text; skipped: {url}"
                        )
                    )
                    continue

                page_title = (
                    soup.title.get_text(strip=True)
                    if soup.title
                    else source["title"]
                )

                document, created = CompanyDocument.objects.update_or_create(
                    source_url=url,
                    defaults={
                        "title": page_title[:255],
                        "source_name": "GitLab",
                        "license_name": HANDBOOK_LICENSE,
                        "license_url": HANDBOOK_LICENSE_URL,
                        "content": content,
                        "last_fetched_at": timezone.now(),
                        "is_active": True,
                    },
                )

                action = "Created" if created else "Updated"
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{action}: {document.title} "
                        f"({len(content)} characters)"
                    )
                )
                success_count += 1

            except RequestException as exc:
                self.stderr.write(
                    self.style.ERROR(f"Fetch failed for {url}: {exc}")
                )

        self.stdout.write(
            f"Finished. Successfully fetched: {success_count}"
        )
