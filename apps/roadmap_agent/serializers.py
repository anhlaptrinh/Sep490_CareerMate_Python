from rest_framework import serializers

class TestSerializer(serializers.Serializer):
    message = serializers.CharField()
    user = serializers.CharField()
