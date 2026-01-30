from odoo import models, api

class AdvancePaymentWizard(models.TransientModel):
    _inherit = "account.payment.wizard"

    def make_advance_payment(self):
        payment = super(AdvancePaymentWizard, self).make_advance_payment()
        order_id = self.env[self._context.get("active_model")].browse(
            self._context.get("active_id")
        )
        sales_person_id = order_id.user_id.employee_id
        report_id = self.env["commission.report.month"].get_report_id(order_id)
        self.env["commission.goal"].apply_goals_achieved(report_id, True)
        self.env["account.payment"].create_commission_on_payment(sales_person_id, payment, order_id, report_id, True)
        return payment