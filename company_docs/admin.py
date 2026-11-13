
from django.contrib import admin
from .models import CompanyDocument


@admin.register(CompanyDocument)
class CompanyDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "source_name",
        "is_active",
        "last_fetched_at",
        "updated_at",
    )

    list_filter = ("is_active", "source_name")

    search_fields = ("title", "source_name", "content")

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Document Information",
            {
                "fields": (
                    "title",
                    "source_name",
                    "source_url",
                    "is_active",
                )
            },
        ),
        (
            "License and Attribution",
            {
                "fields": (
                    "license_name",
                    "license_url",
                )
            },
        ),
        (
            "Document Content",
            {
                "fields": (
                    "content",
                    "last_fetched_at",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
            },
        ),
    )
