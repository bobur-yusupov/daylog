from rest_framework import serializers

from journal.models import Tag, JournalEntry


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'user', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

class JournalEntrySerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = JournalEntry
        fields = ('id', 'title', 'user', 'content', 'is_public', 'tags', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')
