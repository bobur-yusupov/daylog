from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import JournalEntry, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "entry_count", "created_at", "updated_at")
    list_display_links = ("name",)
    search_fields = ("name", "user__username", "user__email")
    list_filter = ("user", "created_at")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    list_per_page = 25

    fieldsets = (
        ("Tag Information", {"fields": ("name", "user")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def entry_count(self, obj):
        """Display the number of journal entries using this tag"""
        count = obj.journalentry_set.count()
        if count > 0:
            url = reverse("admin:journal_journalentry_changelist")
            return format_html(
                '<a href="{}?tags__id__exact={}">{} entries</a>', url, obj.id, count
            )
        return "0 entries"

    entry_count.short_description = "Journal Entries"
    entry_count.admin_order_field = "journalentry_count"


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "is_public",
        "tag_list",
        "word_count",
        "created_at",
        "updated_at",
    )
    list_display_links = ("title",)
    search_fields = ("title", "content", "user__username", "user__email", "tags__name")
    list_filter = ("user", "is_public", "tags", "created_at", "updated_at")
    readonly_fields = ("created_at", "updated_at", "content_preview", "word_count")
    filter_horizontal = ("tags",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    list_per_page = 20

    fieldsets = (
        ("Entry Information", {"fields": ("title", "user", "is_public")}),
        ("Content", {"fields": ("content", "content_preview"), "classes": ("wide",)}),
        ("Tags", {"fields": ("tags",), "classes": ("wide",)}),
        ("Statistics", {"fields": ("word_count",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def tag_list(self, obj):
        """Display tags as colored badges"""
        tags = obj.tags.all()
        if tags:
            tag_html = []
            for tag in tags:
                tag_html.append(
                    f'<span style="background-color: #007cba; color: white; '
                    f"padding: 2px 6px; border-radius: 3px; margin-right: 3px; "
                    f'font-size: 11px;">{tag.name}</span>'
                )
            return mark_safe("".join(tag_html))
        return "No tags"

    tag_list.short_description = "Tags"

    def content_preview(self, obj):
        """Display a preview of the content"""
        if obj.content:
            # Content is already a dict (JSONField), no need to parse
            try:
                content_data = obj.content
                if isinstance(content_data, dict) and "blocks" in content_data:
                    text_blocks = []
                    for block in content_data["blocks"]:
                        if block.get("type") == "paragraph" and "data" in block:
                            text_blocks.append(block["data"].get("text", ""))
                        elif block.get("type") == "header" and "data" in block:
                            text_blocks.append(f"# {block['data'].get('text', '')}")
                    preview_text = " ".join(text_blocks)
                else:
                    preview_text = str(obj.content)
            except (KeyError, TypeError):
                preview_text = str(obj.content)

            # Limit preview to 200 characters
            if len(preview_text) > 200:
                preview_text = preview_text[:200] + "..."

            return format_html(
                '<div style="max-width: 400px; padding: 10px; '
                "background-color: #f8f9fa; border-left: 3px solid #007cba; "
                'font-family: monospace; font-size: 12px;">{}</div>',
                preview_text,
            )
        return "No content"

    content_preview.short_description = "Content Preview"

    def word_count(self, obj):
        """Calculate and display word count"""
        if obj.content:
            try:
                # Content is already a dict (JSONField), no need to parse
                content_data = obj.content
                if isinstance(content_data, dict) and "blocks" in content_data:
                    word_count = 0
                    for block in content_data["blocks"]:
                        if "data" in block and "text" in block["data"]:
                            # Simple word count - split by spaces
                            word_count += len(block["data"]["text"].split())
                    return f"{word_count} words"
                else:
                    return f"{len(str(obj.content).split())} words"
            except (KeyError, TypeError):
                return f"{len(str(obj.content).split())} words"
        return "0 words"

    word_count.short_description = "Word Count"

    def get_queryset(self, request):
        """Optimize queries by prefetching related objects"""
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("tags").select_related("user")
