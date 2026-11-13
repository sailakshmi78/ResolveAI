import json

from django.contrib.auth.models import Group
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import ApprovalRequest


def _is_authenticated(request):
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Authentication required."},
            status=401,
        )
    return None


def _is_approval_reviewer(user):
    return (
        user.groups.filter(name="Approval Reviewers").exists()
        and user.has_perm("core.can_review_approvalrequest")
    )


@require_POST
def create_approval_request(request):
    auth_error = _is_authenticated(request)
    if auth_error:
        return auth_error

    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "JSON body must be an object."}, status=400)

    request_type = data.get("request_type", "OTHER")
    title = data.get("title")
    description = data.get("description")

    valid_types = ApprovalRequest.RequestType.values

    if request_type not in valid_types:
        return JsonResponse({"error": "Invalid request type."}, status=400)

    if not isinstance(title, str) or not title.strip():
        return JsonResponse({"error": "Title is required."}, status=400)

    if len(title.strip()) > 200:
        return JsonResponse({"error": "Title cannot exceed 200 characters."}, status=400)

    if not isinstance(description, str) or not description.strip():
        return JsonResponse({"error": "Description is required."}, status=400)

    if len(description.strip()) > 10000:
        return JsonResponse({"error": "Description cannot exceed 10000 characters."}, status=400)

    approval = ApprovalRequest.objects.create(
        employee=request.user,
        request_type=request_type,
        title=title.strip(),
        description=description.strip(),
    )

    return JsonResponse(
        {
            "message": "Approval request submitted successfully.",
            "request_id": str(approval.request_id),
            "request_type": approval.request_type,
            "title": approval.title,
            "status": approval.status,
            "created_at": approval.created_at.isoformat(),
        },
        status=201,
    )


@require_GET
def list_approval_requests(request):
    auth_error = _is_authenticated(request)
    if auth_error:
        return auth_error

    if _is_approval_reviewer(request.user):
        requests = ApprovalRequest.objects.select_related(
            "employee", "reviewer"
        ).all()
    else:
        requests = ApprovalRequest.objects.select_related(
            "employee", "reviewer"
        ).filter(employee=request.user)

    requests = requests.order_by("-created_at")[:100]

    results = []
    for approval in requests:
        results.append(
            {
                "request_id": str(approval.request_id),
                "request_type": approval.request_type,
                "request_type_display": approval.get_request_type_display(),
                "title": approval.title,
                "description": approval.description,
                "status": approval.status,
                "status_display": approval.get_status_display(),
                "employee": approval.employee.username,
                "reviewer": (
                    approval.reviewer.username if approval.reviewer else None
                ),
                "decision_reason": approval.decision_reason,
                "created_at": approval.created_at.isoformat(),
                "decided_at": (
                    approval.decided_at.isoformat() if approval.decided_at else None
                ),
            }
        )

    return JsonResponse({"requests": results})


@require_POST
def decide_approval_request(request, request_id):
    auth_error = _is_authenticated(request)
    if auth_error:
        return auth_error

    if not _is_approval_reviewer(request.user):
        return JsonResponse(
            {"error": "You are not authorized to review approval requests."},
            status=403,
        )

    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "JSON body must be an object."}, status=400)

    action = data.get("action")
    reason = data.get("reason", "")

    if action not in ("approve", "reject"):
        return JsonResponse(
            {"error": "Action must be 'approve' or 'reject'."},
            status=400,
        )

    if not isinstance(reason, str):
        return JsonResponse({"error": "Reason must be text."}, status=400)

    reason = reason.strip()

    if len(reason) > 5000:
        return JsonResponse({"error": "Reason cannot exceed 5000 characters."}, status=400)

    if action == "reject" and not reason:
        return JsonResponse(
            {"error": "A reason is required when rejecting a request."},
            status=400,
        )

    with transaction.atomic():
        approval = (
            ApprovalRequest.objects.select_for_update()
            .select_related("employee")
            .filter(request_id=request_id)
            .first()
        )

        if approval is None:
            return JsonResponse(
                {"error": "Approval request not found."},
                status=404,
            )

        if approval.employee_id == request.user.id:
            return JsonResponse(
                {"error": "You cannot approve or reject your own request."},
                status=403,
            )

        if approval.status != ApprovalRequest.Status.PENDING:
            return JsonResponse(
                {"error": "This request has already been decided."},
                status=409,
            )

        approval.status = (
            ApprovalRequest.Status.APPROVED
            if action == "approve"
            else ApprovalRequest.Status.REJECTED
        )
        approval.reviewer = request.user
        approval.decision_reason = reason
        approval.decided_at = timezone.now()

        approval.save(
            update_fields=[
                "status",
                "reviewer",
                "decision_reason",
                "decided_at",
                "updated_at",
            ]
        )

    return JsonResponse(
        {
            "message": "Approval request decision recorded.",
            "request_id": str(approval.request_id),
            "status": approval.status,
            "reviewer": request.user.username,
            "decision_reason": approval.decision_reason,
            "decided_at": approval.decided_at.isoformat(),
        }
    )
