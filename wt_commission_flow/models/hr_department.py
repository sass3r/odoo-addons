# -*- coding: utf-8 -*-

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = "hr.department"

    is_sales = fields.Boolean("Sales Department")
