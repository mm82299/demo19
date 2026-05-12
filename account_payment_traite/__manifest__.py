{
    'name': 'Account Payment Traite',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'summary': 'Ajouter Date d\'échéance et Numéro de traite quand Mode de paiement est Traite',
    'author': "Infotech Consulting Services Tunisie",
    'website': "http://www.ics-tunisie.com",
    'description': """
        Ce module ajoute deux champs :
        - Date d'échéance
        - Numéro de traite
        au niveau des paiements (account.payment) et du wizard d'enregistrement de paiement (account.payment.register).
        Ces champs ne s'affichent que lorsque le mode de paiement sélectionné s'appelle "Traite".
    """,
    'depends': ['account'],
    'data': [
        'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
