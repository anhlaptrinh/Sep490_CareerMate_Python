from rest_framework import serializers


class ResumeUploadSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True,
        help_text="PDF file containing the resume to analyze"
    )

    def validate_file(self, value):
        """Validate that the uploaded file is a PDF"""
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError("Only PDF files are supported")

        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be less than 10MB")

        return value
