from django.contrib import admin
from .models import (
    Developer, IssueAssignmentHistory,
    Category, IssueType, Status, QAStatus, DeliveryStatus, QAMember,
    QAAssignmentHistory,
)


@admin.register(Developer)
class DeveloperAdmin(admin.ModelAdmin):
    list_display  = ('name', 'is_active', 'is_default', 'linked_user')
    list_filter   = ('is_active', 'is_default')
    search_fields = ('name',)
    # linked_user/is_default are role-driven — keep them visible but
    # discourage manual edits here since AppUser signals own this state.
    readonly_fields = ('linked_user',)


@admin.register(IssueAssignmentHistory)
class IssueAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display  = ('issue', 'developer', 'assigned_at', 'unassigned_at')
    list_filter   = ('developer',)
    readonly_fields = ('issue', 'developer', 'assigned_at', 'unassigned_at')

    def has_add_permission(self, request):
        return False


@admin.register(QAAssignmentHistory)
class QAAssignmentHistoryAdmin(admin.ModelAdmin):
    list_display  = ('issue', 'qa_member', 'assigned_at', 'unassigned_at')
    list_filter   = ('qa_member',)
    readonly_fields = ('issue', 'qa_member', 'assigned_at', 'unassigned_at')

    def has_add_permission(self, request):
        return False


admin.site.register(Category)
admin.site.register(IssueType)
admin.site.register(Status)
admin.site.register(QAStatus)
admin.site.register(DeliveryStatus)
admin.site.register(QAMember)