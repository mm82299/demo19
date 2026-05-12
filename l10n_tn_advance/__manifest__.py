{
    'name': "l10n_tn_advance",
    'summary': """
         Gestion des retenues de garantie pour la Tunisie.""",
    'description': """
        Ce module permet de gérer les retenues de garantie (avances) sur les factures clients
        pour les établissements publics en Tunisie.
    """,
    'author': 'Infotech Consulting Services',
    'website': 'https://www.ics-tunisie.com',
    'category': 'Accounting/Localizations',
    'version': '1.0',
    'depends': ['base', 'account', 'l10n_tn'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_withholding_sequence.xml',
        'views/res_partner_views.xml',
        'views/account_withholding_advance_tax_views.xml',
        'views/account_withholding_advance_views.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}