{
    'name': "Participation aux Appels d'offres",
    'summary': "Gérer la participation aux appels d'offres et consultations",
    'description': """
        Ce module permet de:
        - Gérer les dossiers d'appels d'offres et consultations.
        - Lier les devis et bons de commande (sale.order) aux dossiers d'appels d'offres.
        - Ajouter un menu dans l'application Ventes.
    """,
    'author': "Amatab",
    'category': 'Sales/Sales',
    'version': '19.0.1.0.0',
    'depends': ['sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_tender_participation_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
