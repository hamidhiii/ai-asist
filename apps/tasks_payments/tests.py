from django.test import TestCase

from apps.orchestrator.models import Client
from apps.tasks_payments.agent import handle_message
from apps.tasks_payments.models import Payment, Task


class TasksPaymentsAgentTests(TestCase):
    def test_creates_payment_from_structured_input(self):
        reply = handle_message(
            telegram_user_id=1,
            text="ignored, structured fields drive behavior",
            kind="payment",
            counterparty="ООО Ромашка",
            amount=150000,
            currency="UZS",
            due_date="2026-09-01",
            note="аванс",
        )

        payment = Payment.objects.get()
        self.assertEqual(payment.counterparty, "ООО Ромашка")
        self.assertEqual(payment.amount, 150000)
        self.assertIn("Ромашка", reply)
        self.assertEqual(Client.objects.get().telegram_user_id, 1)

    def test_creates_task_from_structured_input(self):
        handle_message(
            telegram_user_id=2,
            text="ignored",
            kind="task",
            title="Позвонить клиенту",
            due_date="2026-09-05",
        )

        task = Task.objects.get()
        self.assertEqual(task.title, "Позвонить клиенту")
        self.assertEqual(str(task.due_date), "2026-09-05")

    def test_missing_details_returns_clarifying_reply(self):
        reply = handle_message(telegram_user_id=3, text="что-то про деньги", kind="payment")

        self.assertFalse(Payment.objects.exists())
        self.assertIn("хват", reply.lower())
