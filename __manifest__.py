# -*- coding: utf-8 -*-
{
    'name': "Repair Request",

    'summary': "Repair Request",

    'description': """
Repair Request
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Portal',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'portal', 'mail'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/repair_request.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

