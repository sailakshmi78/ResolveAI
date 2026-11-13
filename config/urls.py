from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from apps.core.views import (
    home,
    search_guidance,
    troubleshoot_issue,
    troubleshoot_chat,
    create_ticket,
    check_ticket_status,
)

from apps.core.approval_views import (
    create_approval_request,
    list_approval_requests,
    decide_approval_request,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("login/", LoginView.as_view(template_name="core/login.html", redirect_authenticated_user=True, next_page="/"), name="login"),
    path("logout/", LogoutView.as_view(next_page="home"), name="logout"),
    path("api/guidance/", search_guidance, name="search_guidance"),
    path("api/solution/", troubleshoot_issue, name="troubleshoot_issue"),
    path("api/solution/chat/", troubleshoot_chat, name="troubleshoot_chat"),
    path("api/tickets/create/", create_ticket, name="create_ticket"),
    path("api/tickets/status/", check_ticket_status, name="check_ticket_status"),

    path("api/approvals/create/", create_approval_request, name="create_approval_request"),
    path("api/approvals/", list_approval_requests, name="list_approval_requests"),
    path("api/approvals/<uuid:request_id>/decide/", decide_approval_request, name="decide_approval_request"),
]
