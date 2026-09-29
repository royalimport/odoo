# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_authorize.tests.common import AuthorizeCommon


@tagged("post_install", "-at_install")
class TestPaymentTransaction(AuthorizeCommon):
    def test_search_by_reference_finds_transaction_from_webhook_data(self):
        """Test that a transaction is correctly found from webhook data using invoiceNumber."""
        tx = self._create_transaction("direct")
        found_tx = self.env["payment.transaction"]._search_by_reference(
            "authorize", self.webhook_authcapture_data
        )
        self.assertEqual(tx, found_tx)

    def _apply_decline(self, reason_code="2", avs_result_code="Y", cvv_result_code="M"):
        tx = self._create_transaction("direct")
        tx.with_context(payment_safe_write=True)._apply_updates({
            "response": {
                "x_response_code": "2",
                "x_response_reason_code": reason_code,
                "x_response_reason_text": "This transaction has been declined.",
                "x_avs_result_code": avs_result_code,
                "x_cvv_result_code": cvv_result_code,
                "x_trans_id": "60000000001",
                "x_type": "auth_capture",
                "payment_method_code": "Visa",
            },
        })
        self.assertEqual(tx.state, "cancel")
        return tx.state_message

    def test_decline_without_avs_or_cvv_mismatch_keeps_reason(self):
        self.assertEqual(self._apply_decline(), "This transaction has been declined.")

    def test_decline_with_cvv_mismatch_adds_hint(self):
        message = self._apply_decline(cvv_result_code="N")
        self.assertTrue(message.startswith("This transaction has been declined.\n"))
        self.assertIn("security code (CVV) does not match", message)

    def test_decline_with_avs_mismatch_adds_hint(self):
        message = self._apply_decline(avs_result_code="N")
        self.assertIn("billing address or postal code", message)

    def test_decline_with_avs_and_cvv_filter_adds_combined_hint(self):
        message = self._apply_decline(reason_code="45")
        self.assertIn("billing address and the card security code", message)

    def test_explicit_avs_decline_reason_is_not_duplicated(self):
        message = self._apply_decline(reason_code="27", avs_result_code="N")
        self.assertEqual(message, "This transaction has been declined.")
