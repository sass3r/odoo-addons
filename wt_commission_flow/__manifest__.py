# -*- coding: utf-8 -*-
{
    "name": "Commission Process",
    "version": "16.0.2",
    "category": "Sale",
    "summary": "",
    "description": """
        Generate commission report based on commission configration.
    """,
    "author": "Clingdata LLC",
    "website": "https://clingdata.com",
    "support": "support@clingdata.com",
    "depends": ["base", "sale_management", "hr", "account", "sh_register_payment_so"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee.xml",
        "views/he_department.xml",
        "views/commission_report_monthly.xml",
        "views/commission_goal_views.xml",
    ],
    "application": True,
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
}
