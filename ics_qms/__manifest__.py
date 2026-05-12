{
    'name': "Ics Qms",
    'summary': "Ics Qms",
    'description': """Ics Qms
    """,
    'author': "Infotech Consulting Services",
    'website': "https://website.ics-tn.com/",
    'category': 'Uncategorized',
    'version': '19.0.0.1',
    'depends': ['base', 'contacts', 'purchase', 'sale', 'mgmtsystem_action', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'reports/customer_clam_xlsx_report.xml',
        'views/supplier_evaluation.xml',
        'views/res_partner.xml',
        'views/customer_clam_view.xml',
        'wizard/customer_clam_report_wizard_view.xml',
    ],
}
