# -*- coding: utf-8 -*-
from odoo import models, fields

class CommissionLine(models.Model):
    _name = "commission.line"

    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="employee"
    )

    commission_name = fields.Char(string="Commission Name")

    commission_type = fields.Selection(
        [("sales", "on Sale"), ("payment", "on Payment")],
        string="Commission ",
        default="sales",
    )

    commission_percentage = fields.Float(string="Commission Percentage(%)")
    commission_start_date = fields.Date(string="Start Date")
    commission_end_date = fields.Date(string="End Date")

    commission_apply_on = fields.Selection(
        [("all_sales", "All Sales"), ("my_sales", "My Sales")],
        string="Commission Apply On",
        default="all_sales",
    )

    min_amount = fields.Float()
    max_amount = fields.Float()

        
    def _is_range_commission(self):
        condition = False
        if self.min_amount > 0.0:
            condition |= True
        if self.max_amount > 0.0:
            condition |= True
        return condition