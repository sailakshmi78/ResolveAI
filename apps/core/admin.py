from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import ApprovalRequest, SupportTicket


class SupportTicketAdminForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        is_escalated = cleaned_data.get("is_escalated")
        escalation_reason = cleaned_data.get("escalation_reason", "")

        if is_escalated and not escalation_reason.strip():
            self.add_error(
                "escalation_reason",
                "An escalation reason is required."
            )

        return cleaned_data


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    form = SupportTicketAdminForm

    list_display = (
        "ticket_id",
        "category",
        "status",
        "assigned_team",
        "assigned_to",
        "is_escalated",
        "notification_status",
        "created_at",
    )

    list_filter = (
        "status",
        "category",
        "is_escalated",
        "notification_status",
        "created_at",
    )

    search_fields = (
        "ticket_id",
        "description",
        "assigned_team",
        "assigned_to",
        "escalation_reason",
    )

    readonly_fields = (
        "ticket_id",
        "created_at",
        "updated_at",
        "notification_status",
        "escalated_at",
        "conversation_history",
        "attempted_steps",
        "source_references",
    )

    list_editable = (
        "status",
        "assigned_team",
        "assigned_to",
    )

    ordering = ("-created_at",)

    fieldsets = (
        ("Ticket Details", {
            "fields": (
                "ticket_id",
                "category",
                "description",
                "status",
                "created_at",
                "updated_at",
            )
        }),
        ("Assignment", {
            "fields": (
                "assigned_team",
                "assigned_to",
            )
        }),
        ("Escalation", {
            "fields": (
                "is_escalated",
                "escalation_reason",
                "escalated_at",
            )
        }),
        ("Notification", {
            "fields": ("notification_status",)
        }),
        ("Troubleshooting Record", {
            "fields": (
                "conversation_history",
                "attempted_steps",
                "source_references",
            ),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj, form, change):
        if obj.is_escalated and obj.escalated_at is None:
            obj.escalated_at = timezone.now()

        super().save_model(request, obj, form, change)


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "request_id",
        "title",
        "request_type",
        "employee",
        "status",
        "reviewer",
        "created_at",
        "decided_at",
    )

    list_filter = (
        "request_type",
        "status",
        "created_at",
        "decided_at",
    )

    search_fields = (
        "request_id",
        "title",
        "description",
        "employee__username",
        "reviewer__username",
    )

    readonly_fields = (
        "request_id",
        "employee",
        "request_type",
        "title",
        "description",
        "status",
        "reviewer",
        "decision_reason",
        "decided_at",
        "created_at",
        "updated_at",
    )

    ordering = ("-created_at",)

    fieldsets = (
        ("Request Details", {
            "fields": (
                "request_id",
                "employee",
                "request_type",
                "title",
                "description",
                "created_at",
            )
        }),
        ("Decision Record", {
            "fields": (
                "status",
                "reviewer",
                "decision_reason",
                "decided_at",
                "updated_at",
            )
        }),
    )

    def has_view_permission(self, request, obj=None):
        user = request.user
        return (
            user.is_active
            and user.is_staff
            and user.groups.filter(name="Approval Reviewers").exists()
            and user.has_perm("core.can_review_approvalrequest")
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
