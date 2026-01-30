# -*- coding: utf-8 -*-

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    commission_by = fields.Selection(
        [
            ("manager", "Manager"), 
            ("salesperson", "Salesperson"),
        ], string="Commission By"
    )

    commission_type = fields.Selection(
        [("sales", "on Sale"), ("payment", "on Payment")],
        string="Commission ",
        default="sales",
    )

    commission_percentage = fields.Float(string="Commission Percentage(%)")
    commission_start_date = fields.Date(string="Start Date")

    commission_apply_on = fields.Selection(
        [("all_sales", "All Sales"), ("my_sales", "My Sales")],
        string="Commission Apply On",
        default="all_sales",
    )

    commission_line_ids = fields.One2many(
        comodel_name="commission.line",
        inverse_name="employee_id",
        string="Commission lines"
    )
