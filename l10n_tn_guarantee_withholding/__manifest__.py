{
    'name': "Retenue de Garantie Tunisien",
    'summary': """
         Gestion des retenues de garantie selon les normes tunisiennes""",
    'description': """
        Ce module permet de calculer et d'afficher la retenue de garantie sur les factures, 
        avec une ventilation pro-rata sur le montant HT et la TVA.
    """,
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['base', 'account', 'l10n_tn', 'l10n_tn_tva'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/account_move_view.xml',
        'views/account_tax.xml',
        'views/res_partner_views.xml',
        'views/report_invoice.xml',
    ],
    'installable': True,
    'application': False,
}