from odoo import models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    def get_total_payments(self, start_date, end_date):
        domain = [
            ('payment_type','=', 'inbound'),
            ('partner_type','=', 'customer'),
            ('state', '=', 'posted')
        ]

        if start_date:
            domain.append(('date','>=', start_date))
        
        if end_date:
            domain.append(('date','<=', end_date))

        payments = self.search(domain)
        total = sum(p.amount for p in payments)
        return total

    def get_total_payments_by_manager(self, manager_id, start_date, end_date):
        employees = self.env["sale.order"].get_sales_employees()
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

        sales = self.env["sale.order"].search(sale_domain)

        payments = sales.mapped("sh_amount_paid")
        total = sum(p for p in payments if p)
        return total
    
    def create_commission_on_payment(self, sales_person_id, payment, order_id, report_id, positive):
        """
        Recursively create commission for the employee and all managers up the hierarchy based on sales commission.
        """
        commission_lines = sales_person_id.commission_line_ids
        for line in commission_lines:
            if line.commission_type == "payment":
                if not line._is_range_commission():
                    self.env["commission.report"].create_basic_commission_record(report_id,sales_person_id,order_id,line,positive,payment=payment)
                else:
                    if sales_person_id.commission_by == "manager":
                        total_amount = self.env["account.payment"].get_total_payments_by_manager(sales_person_id,line.commission_start_date, line.commission_end_date)
                        condition = True
                        if line.min_amount > 0.0:
                            condition &= total_amount >= line.min_amount
                        if line.max_amount > 0.0:
                            condition &= total_amount <= line.max_amount
                        if condition:
                            self.env["commission.report"].create_range_commission_record(total_amount,sales_person_id,report_id,line,positive)

        if (
            sales_person_id.parent_id
            and sales_person_id.parent_id.commission_by == "manager"
        ):
            self.create_commission_on_payment(
                sales_person_id.parent_id, payment, order_id, report_id, positive
            )