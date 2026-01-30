# -*- coding: utf-8 -*-
from odoo import models, api


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        self.ensure_one()
        payment = super(AccountPaymentRegister, self)._create_payments()

        inv_id = self.env["account.move"].search(
            [("id", "=", self.env.context.get("active_id"))]
        )
        order_id = self.env["sale.order"].search([("name", "=", inv_id.invoice_origin)])

        sales_person_id = inv_id.invoice_user_id.employee_id

        if (
            sales_person_id
            and inv_id.move_type in ["out_invoice", "out_refund"]
            and order_id
        ):
            move_type = inv_id.move_type
            self._create_commission_on_payment(
                sales_person_id, payment, move_type, order_id
            )
        return payment

    def _create_commission_on_payment(
        self, sales_person_id, payment, move_type, order_id
    ):
        """
        Recursively create commission for the employee and all managers up the hierarchy based on sales commission.
        """
        if sales_person_id.commission_type == "payment" or move_type == "out_refund":
            month = str(payment.date.month)
            year = payment.date.year
            report_id = self.env["commission.report.month"].search(
                [("month", "=", month), ("year", "=", year)], limit=1
            )

            if not report_id:
                report_id = self.env["commission.report.month"].create(
                    {
                        "month": month,
                        "year": year,
                    }
                )
            commission_percentage = (
                sales_person_id.commission_percentage or 0.0
                if move_type == "out_invoice"
                else -sales_person_id.commission_percentage or 0.0
            )
            self.env["commission.report"].create(
                {
                    "employee_id": sales_person_id.id,
                    "order_id": order_id.id,
                    "order_name": order_id.name,
                    "date_order": order_id.date_order,
                    "amount_total": order_id.amount_total,
                    "commission_amount": payment.amount * (commission_percentage / 100),
                    "commission_percentage": commission_percentage,
                    "payment_id": payment.id,
                    "commission_type": sales_person_id.commission_type,
                    "month_id": report_id.id if report_id else False,
                }
            )

        if (
            sales_person_id.parent_id
            and sales_person_id.parent_id.commission_by == "manager"
        ):
            self._create_commission_on_payment(
                sales_person_id.parent_id, payment, move_type, order_id
            )
