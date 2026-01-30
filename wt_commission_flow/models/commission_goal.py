# -*- coding: utf-8 -*-
from odoo import models, fields

class CommissionGoal(models.Model):
    _name = "commission.goal"

    goal_name = fields.Char(string="Goal Name")

    commission_type = fields.Selection(
        [("sales", "on Sale"), ("payment", "on Payment")],
        string="Commission ",
        default="sales",
    )

    commission_percentage = fields.Float(string="Commission Percentage(%)")
    commission_start_date = fields.Date(string="Start Date")
    commission_end_date = fields.Date(string="End Date")

    min_amount = fields.Float()
    only_min_value = fields.Boolean(default=True)
    only_start_date = fields.Boolean(default=True)
    max_amount = fields.Float()
    active = fields.Boolean(string="Active", default=False)

    def apply_goals_achieved(self, month_id, by_payment):
        goals = self.search([
            ("active","=",True)
        ])

        for goal in goals:
            if by_payment:
                total_amount = self.env["account.payment"].get_total_payments(self.commission_start_date, self.commission_end_date)
            else:
                total_amount = self.env["sale.order"].get_total_sales(self.commission_start_date, self.commission_end_date)
            commission_percentage = goal.commission_percentage
            condition = True
            if goal.min_amount > 0.0:
                condition &= total_amount >= goal.min_amount
            if goal.max_amount > 0.0:
                condition &= total_amount <= goal.max_amount
            
            if condition:
                employees = self.env["sale.order"].get_sales_employees()
                for employee in employees:
                    if not self.env["commission.report"].exist_commission_record(employee.id,month_id.id,goal.id, True):
                        self.env["commission.report"].create(
                            {
                                "employee_id": employee.id,
                                "amount_total": total_amount,
                                "commission_amount": total_amount
                                * (commission_percentage / 100),
                                "commission_percentage": commission_percentage,
                                "commission_type": goal.commission_type,
                                "month_id": month_id.id if month_id else False,
                                "commission_by": "goal",
                                "commission_goal_id": goal.id
                            }
                        )