from rest_framework import serializers

from .models import Payment, Task


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "counterparty", "amount", "currency", "due_date", "status", "note", "created_at"]
        read_only_fields = ["id", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "due_date", "status", "created_at"]
        read_only_fields = ["id", "created_at"]
