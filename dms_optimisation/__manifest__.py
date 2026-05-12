# -*- coding: utf-8 -*-
{
    'name': "DMS Optimisation CTAMA",
    'summary': "Optimisation du workflow de gestion documentaire pour CTAMA",
    'description': """
        Module d'optimisation du système de gestion documentaire pour CTAMA.
        Gestion des dossiers sinistres avec workflow configurable,
        intégration avec Odoo Documents, et suivi des approbations.
    """,
    'author': "Infotech Consulting Services (ICS)",
    'website': "",
    'category': 'Productivity/Documents',
    'version': '19.0.1.0.0',
    'depends': ['documents', 'mail'],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # Data
        'data/workflow_stage_data.xml',
        'data/insurance_company_data.xml',
        'data/document_type_data.xml',
        # Views
        'views/sinistre_dossier_views.xml',
        'views/insurance_company_views.xml',
        'views/document_type_views.xml',
        'views/documents_document_views.xml',
        # Wizards
        'wizards/dossier_reception_wizard_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
