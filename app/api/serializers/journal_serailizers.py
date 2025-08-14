from rest_framework import serializers
import json

from journal.models import Tag, JournalEntry


class TagSerializer(serializers.ModelSerializer):
    entry_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ('id', 'name', 'user', 'entry_count', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at', 'user', 'entry_count')

    def get_entry_count(self, obj):
        """Get the number of journal entries using this tag"""
        return obj.journalentry_set.count()


class JournalEntrySerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=100),
        write_only=True,
        required=False,
        help_text="List of tag names to assign to this entry"
    )
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalEntry
        fields = (
            'id', 'title', 'user', 'content', 'is_public', 
            'tags', 'tag_names', 'content_preview',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at', 'user', 'content_preview')
    
    def get_content_preview(self, obj):
        """Generate a text preview from EditorJS content"""
        try:
            content = obj.content
            if isinstance(content, dict) and 'blocks' in content:
                text_blocks = []
                for block in content['blocks']:
                    if 'data' in block:
                        # Handle paragraph and header blocks
                        if 'text' in block['data']:
                            text_blocks.append(block['data']['text'])
                        # Handle list blocks
                        elif 'items' in block['data']:
                            for item in block['data']['items']:
                                if isinstance(item, str):
                                    text_blocks.append(f"• {item}")
                
                preview_text = ' '.join(text_blocks)
                # Limit preview to 200 characters
                if len(preview_text) > 200:
                    preview_text = preview_text[:200] + "..."
                return preview_text
            else:
                # Fallback for plain text content
                preview = str(content)
                if len(preview) > 200:
                    preview = preview[:200] + "..."
                return preview
        except:
            return "No preview available"
    
    def validate_content(self, value):
        """Validate EditorJS content structure"""
        if not value:
            raise serializers.ValidationError("Content cannot be empty")
        
        try:
            if isinstance(value, str):
                content_data = json.loads(value)
            else:
                content_data = value
            
            # Basic EditorJS structure validation
            if not isinstance(content_data, dict):
                raise serializers.ValidationError("Content must be a valid EditorJS object")
            
            if 'blocks' not in content_data:
                raise serializers.ValidationError("Content must contain blocks array")
            
            if not isinstance(content_data['blocks'], list):
                raise serializers.ValidationError("Blocks must be an array")
            
            # Validate each block has required fields
            for i, block in enumerate(content_data['blocks']):
                if not isinstance(block, dict):
                    raise serializers.ValidationError(f"Block {i} must be an object")
                
                required_fields = ['id', 'type', 'data']
                for field in required_fields:
                    if field not in block:
                        raise serializers.ValidationError(f"Block {i} missing required field: {field}")
            
            return content_data
            
        except json.JSONDecodeError:
            raise serializers.ValidationError("Invalid JSON content")
        except Exception as e:
            raise serializers.ValidationError(f"Content validation error: {str(e)}")
    
    def create(self, validated_data):
        """Handle journal entry creation with tags"""
        tag_names = validated_data.pop('tag_names', [])
        entry = JournalEntry.objects.create(**validated_data)
        
        # Handle tags
        for tag_name in tag_names:
            if tag_name.strip():
                tag, created = Tag.objects.get_or_create(
                    user=entry.user,
                    name=tag_name.strip()
                )
                entry.tags.add(tag)
        
        return entry
    
    def update(self, instance, validated_data):
        """Handle journal entry updates with tags"""
        tag_names = validated_data.pop('tag_names', None)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Handle tags if provided
        if tag_names is not None:
            instance.tags.clear()
            for tag_name in tag_names:
                if tag_name.strip():
                    tag, created = Tag.objects.get_or_create(
                        user=instance.user,
                        name=tag_name.strip()
                    )
                    instance.tags.add(tag)
        
        return instance


class JournalEntryCreateSerializer(JournalEntrySerializer):
    """Specialized serializer for creating journal entries"""
    
    class Meta(JournalEntrySerializer.Meta):
        fields = (
            'title', 'content', 'is_public', 'tag_names'
        )


class JournalEntryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing journal entries"""
    tags = TagSerializer(many=True, read_only=True)
    word_count = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = JournalEntry
        fields = (
            'id', 'title', 'is_public', 'tags', 
            'word_count', 'content_preview', 'created_at', 'updated_at'
        )
    
    def get_word_count(self, obj):
        """Calculate word count from EditorJS content"""
        return JournalEntrySerializer().get_word_count(obj)
    
    def get_content_preview(self, obj):
        """Generate a text preview from EditorJS content"""
        return JournalEntrySerializer().get_content_preview(obj)
