# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        compute="_compute_user_id",
        store=True,
        readonly=False,
        precompute=True,
        index=True,
        tracking=2,
        domain=lambda self: self._get_user_domain(),
    )

    def _get_user_domain(self):
        sales_department = self.env["hr.department"].search([("is_sales", "=", True)])
        sales_employee_ids = (
            self.env["hr.employee"]
            .search([("department_id", "in", sales_department.ids)])
            .mapped("user_id.id")
        )
        return [("id", "in", sales_employee_ids)]

    def action_confirm(self):
        """
        Override the sale order confirmation action to create commission records based on employee commission types.
        """
        for order in self:
            if not order.user_id:
                raise ValidationError(
                    "Please assign a Salesperson before confirming the sale order."
                )

            sales_department = self.env["hr.department"].search(
                [("is_sales", "=", True)]
            )
            if order.user_id.employee_id.department_id.id not in sales_department.ids:
                raise ValidationError(
                    "The selected Salesperson is not part of the Sales department."
                )

            employee = order.user_id.employee_id
            report_id = self.env["commission.report.month"].get_report_id(order)
            self.env["commission.goal"].apply_goals_achieved(report_id, False)
            if employee:
                order._create_commission_on_sale(employee, order, report_id, True)
        return super(SaleOrder, self).action_confirm()


    def _create_commission_on_sale(self, employee, order, report_id, positive):
        """
        Recursively create commission for the employee and all managers up the hierarchy based on sales commission.
        """

        commission_lines = employee.commission_line_ids
        for line in commission_lines:
            if line.commission_type == "sales":
                if not line._is_range_commission():
                    self.env["commission.report"].create_basic_commission_record(report_id,employee,order,line,positive)
                else:
                    if employee.commission_by == "manager":
                        total_amount = self.get_total_sales_by_manager(employee,line.commission_start_date, line.commission_end_date)
                        condition = True
                        if line.min_amount > 0.0:
                            condition &= total_amount >= line.min_amount
                        if line.max_amount > 0.0:
                            condition &= total_amount <= line.max_amount
                        if condition:
                            self.env["commission.report"].create_range_commission_record(total_amount,employee,report_id,line,positive)

        if employee.parent_id and employee.parent_id.commission_by == "manager":
            self._create_commission_on_sale(employee.parent_id, order, report_id, positive)
        
    def get_sales_employees(self):
        sales_department = self.env["hr.department"].search([
            ("is_sales","=",True)
        ])

        employees = self.env["hr.employee"].search([
            ("department_id","in",sales_department.ids)
        ])

        return employees

    def get_total_sales(self, start_date, end_date):
        domain = [
            ('state','=', 'sale'),
        ]

        if start_date:
            domain.append(('date_order','>=', start_date))
        
        if end_date:
            domain.append(('date_order','<=', end_date))

        sales = self.search(domain)
        total = sum(s.amount_total for s in sales)
        return total
    
    def get_total_sales_by_manager(self, manager_id, start_date, end_date):
        employees = self.get_sales_employees()
        manager_employees = employees.filtered(lambda e: e.parent_id.id == manager_id.id)

        if not manager_employees:
            return 0.0

        employee_users_ids = manager_employees.mapped("user_id").ids

        sale_domain = [
            ("user_id","in",employee_users_ids)
        ]

        if start_date:
            sale_domain.append(("date_order", ">=", start_date))
        if end_date:
            sale_domain.append(("date_order", "<=", end_date))

        sales = self.search(sale_domain)

        total = sum(s.amount_total for s in sales if s)
        return total