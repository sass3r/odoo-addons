# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta
from datetime import timedelta, time


class CommissionReport(models.Model):
    _name = "commission.report"
    _description = "Commission Report"
    _rec_name = "order_name"

    employee_id = fields.Many2one("hr.employee", string="Employee")
    parent_id = fields.Many2one(
        "hr.employee",
        string="Manager",
        related="employee_id.parent_id",
        store=True,
        readonly=True,
    )
    commission_type = fields.Selection(
        [("sales", "on Sale"), ("payment", "on Payment")], string="Commission "
    )
    
    commission_by = fields.Selection(
        [
            ("manager", "Manager"), 
            ("salesperson", "Salesperson"),
            ("goal", "Goal")
        ], string="Commission By"
    )

    order_id = fields.Many2one("sale.order", string="Sale Order", readonly=True)
    invoice_id = fields.Many2one("account.move", string="Invoice", readonly=True)
    order_name = fields.Char(string="Order Reference")
    date_order = fields.Date(string="Order Date")
    commission_percentage = fields.Float(string="Commission Percentage")
    company_id = fields.Many2one(
        "res.company",
        store=True,
        copy=False,
        string="Company",
        default=lambda self: self.env.user.company_id.id,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="company_id.currency_id",
        default=lambda self: self.env.user.company_id.currency_id.id,
    )
    amount_total = fields.Monetary(string="Total Amount")
    commission_amount = fields.Monetary(string="Commission Amount")
    month_id = fields.Many2one(
        "commission.report.month", string="Commission Month", ondelete="cascade"
    )
    payment_id = fields.Many2one("account.payment", string="Payment Ref")
    commission_line_id = fields.Many2one("commission.line")
    commission_goal_id = fields.Many2one("commission.goal")

    def exist_commission_record(self, employee_id, month_id, line_id, is_goal):
        domain = [
            ('month_id','=', month_id),
            ('employee_id','=', employee_id),
        ]

        if is_goal:
            domain.append(('commission_goal_id','=', line_id))
        else:
            domain.append(('commission_line_id','=', line_id))

        reports = self.search(domain)
        return reports.exists()

    def create_basic_commission_record(self, month_id, employee, order, line, positive, payment=None):
        commission_percentage = line.commission_percentage
        commission_percentage = (
            commission_percentage or 0.0
            if positive
            else -commission_percentage or 0.0
        )
        commission_report = {
                "employee_id": employee.id,
                "order_id": order.id,
                "order_name": order.name,
                "date_order": order.date_order,
                "amount_total": order.amount_total,
                "commission_amount": order.amount_total
                * (commission_percentage / 100),
                "commission_percentage": commission_percentage,
                "commission_type": line.commission_type,
                "month_id": month_id.id if month_id else False,
                "commission_by": employee.commission_by,
        }

        if payment:
            commission_report["commission_amount"] = payment.amount * (commission_percentage / 100)
            commission_report["payment_id"] = payment.id

        self.env["commission.report"].create(commission_report)

    def create_range_commission_record(self, total_amount, employee, month_id, line, positive):
        commission_percentage = line.commission_percentage
        commission_percentage = (
            commission_percentage or 0.0
            if positive
            else -commission_percentage or 0.0
        )
        if not self.exist_commission_record(employee.id,month_id.id,line.id, False):
            self.create(
                {
                    "employee_id": employee.id,
                    "amount_total": total_amount,
                    "commission_amount": total_amount
                    * (commission_percentage / 100),
                    "commission_percentage": commission_percentage,
                    "commission_type": line.commission_type,
                    "month_id": month_id.id if month_id else False,
                    "commission_by": employee.commission_by,
                    "commission_line_id": line.id
                }
            )

class CommissionReportMonth(models.Model):
    _name = "commission.report.month"
    _description = "Monthly Commission Report"

    name = fields.Char(string="Month", compute="_compute_name", store=True)
    year = fields.Integer(string="Year", required=True)
    month = fields.Selection(
        selection=[(str(i), date(1900, i, 1).strftime("%B")) for i in range(1, 13)],
        string="Month",
        required=True,
    )
    state = fields.Selection(
        [("new", "New"), ("recomputed", "Recomputed"), ("applied", "Approved")],
        string="State",
        default="new",
        readonly=True,
    )

    commission_ids = fields.One2many(
        "commission.report", "month_id", string="Commission Reports"
    )

    def action_view_commission_lines(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Commission",
            "view_mode": "tree",
            "res_model": "commission.report",
            "domain": [("month_id.id", "=", self.id)],
            "context": {"month_id.id": self.id},
            "target": "current",
        }

    @api.depends("month", "year")
    def _compute_name(self):
        for rec in self:
            rec.name = (
                f"{dict(self._fields['month'].selection).get(rec.month)} {rec.year}"
            )

    def action_apply_commissions(self):
        for report in self:
            report.write({"state": "applied"})

    def action_regenerate_commissions(self):
        """Recompute all commissions for this month."""
        self.commission_ids.unlink()

        month_start = date(self.year, int(self.month), 1)
        month_end = month_start + relativedelta(day=31)
        sale_orders = self.env["sale.order"].search(
            [
                ("date_order", ">=", month_start),
                ("date_order", "<=", month_end),
                ("state", "=", "sale"),
            ]
        )

        payment_ids = self.env["account.payment"].search(
            [
                ("date", ">=", month_start),
                ("date", "<=", month_end),
                ("state", "=", "posted")
            ]
        )

        for order_id in sale_orders:
            employee_id = order_id.user_id.employee_id
            report_id = self.get_report_id(order_id)
            if employee_id and len(employee_id.commission_line_ids) > 0:
                order_id._create_commission_on_sale(employee_id, order_id, report_id, True)
                self._handle_payment_commissions(employee_id, order_id, payment_ids, report_id)
        for payment_id in payment_ids:
            # if payment_id.id not in self.commission_ids.ids:
            if payment_id.id not in self.commission_ids.mapped("payment_id.id"):
                if payment_id.sale_id:
                    employee_id = payment_id.sale_id.user_id.employee_id
                    order_id = payment_id.sale_id
                    report_id = self.get_report_id(order_id)
                    self.env["account.payment"].create_commission_on_payment(employee_id, payment_id, order_id, report_id, True)
                else:
                    for invoice in payment_id.reconciled_invoice_ids:
                        order_id = self.env["sale.order"].search(
                            [("name", "=", invoice.invoice_origin)]
                        )
                        employee_id = order_id.user_id.employee_id
                        if order_id:
                            report_id = self.get_report_id(order_id)
                            self.env["account.payment"].create_commission_on_payment(employee_id, payment_id, order_id, report_id, True)
        self.write({"state": "recomputed"})

    def _handle_payment_commissions(self, employee, order_id, payment_ids, report_id):
        for invoice in order_id.invoice_ids.filtered(
            lambda inv: inv.payment_state in ["paid", "partial", "in_payment"]
        ):
            if invoice.id in payment_ids.mapped("reconciled_invoice_ids.id"):
                payments = payment_ids.filtered(
                    lambda x: x.reconciled_invoice_ids in invoice
                )
                move_type = invoice.move_type
                if move_type in ["out_invoice", "out_refund"]:
                    for payment in payments:
                        if move_type == "out_invoice":
                            self.env["account.payment"].create_commission_on_payment(employee, payment, order_id, report_id, True)
                        else:
                            self.env["account.payment"].create_commission_on_payment(employee, payment, order_id, report_id, False)
    
    def get_report_id(self,order):
        # Create a Report if not available for a order date.
        month = str(order.date_order.month)
        year = order.date_order.year
        report_id = self.search(
            [("month", "=", month), ("year", "=", year)], limit=1
        )

        if not report_id:
            report_id = self.create(
                {
                    "month": month,
                    "year": year,
                }
            )
        
        return report_id