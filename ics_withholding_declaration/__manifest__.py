# -*- coding: utf-8 -*-
{
    'name': "Ics Withholding Declaration",
    'summary': "Ics Withholding Declaration",
    'description': """
        Ics Withholding Declaration
        Déclaration des retenues fournisseurs sur TEJ Tunisie
    """,
    'author': "Infotech Consulting Services",
    'website': "https://website.ics-tn.com/",
    'category': 'Financial Accounting',
    'version': '19.0.0.1',
    'depends': ['base','mail','account','l10n_tn_ras'],
    'data': [
        'security/withholding_declaration_group.xml',
        'security/ir.model.access.csv',
        'security/multi_company.xml',
        'views/res_partner_views.xml',
        'views/withholding_declaration_views.xml',
        'views/withholding_declaration_operation_type_view.xml',
        'views/withholding_declaration_operation_line_view.xml',
        'views/withholding_declaration_line_view.xml',
        'views/withholding_declaration_country.xml',
        'views/withholding_declaration_operation_type_category_view.xml',
        'views/menu.xml',
        'data/withholding_declaration_data.xml',
        'data/withholding_declaration_operation_type_category.xml',
        'data/withholding_declaration_operation_type_data.xml',
    ],
    'images': [
        'static/description/ics_tej.png'
    ],
    'license': 'OPL-1',
    'price': 166.666,
    'currency': 'USD',

}

