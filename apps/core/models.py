
import uuid
from django.conf import settings

from django.db import models


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    class Category(models.TextChoices):
        IT_SUPPORT = "IT_SUPPORT", "IT support"
        WORKPLACE = "WORKPLACE", "Workplace process"
        NETWORK = "NETWORK", "Network / Wi-Fi"
        ACCOUNT = "ACCOUNT", "Account / Login"
        SOFTWARE = "SOFTWARE", "Software / Application"
        HARDWARE = "HARDWARE", "Hardware / Device"
        ACCESS = "ACCESS", "Access / Permissions"
        OTHER = "OTHER", "Other"

    class NotificationStatus(models.TextChoices):
        NOT_CONFIGURED = "NOT_CONFIGURED", "Not configured"
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    ticket_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.OTHER,
    )

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    is_escalated = models.BooleanField(default=False)
    escalation_reason = models.TextField(blank=True, default="")
    escalated_at = models.DateTimeField(null=True, blank=True)

    conversation_history = models.JSONField(default=list, blank=True)
    attempted_steps = models.JSONField(default=list, blank=True)
    source_references = models.JSONField(default=list, blank=True)

    assigned_team = models.CharField(max_length=100, blank=True, default="")
    assigned_to = models.CharField(max_length=150, blank=True, default="")

    notification_status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.NOT_CONFIGURED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.ticket_id} - {self.get_status_display()}"

class ApprovalRequest(models.Model):
    class RequestType(models.TextChoices):
        ACCESS = "ACCESS", "Application / Folder Access"
        LEAVE = "LEAVE", "Leave"
        EXPENSE = "EXPENSE", "Expense Reimbursement"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    request_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approval_requests",
    )

    request_type = models.CharField(
        max_length=20,
        choices=RequestType.choices,
        default=RequestType.OTHER,
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_approval_requests",
        null=True,
        blank=True,
    )

    decision_reason = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ("can_review_approvalrequest", "Can review approval requests"),
        ]

    def __str__(self):
        return f"{self.request_id} - {self.get_status_display()}"
