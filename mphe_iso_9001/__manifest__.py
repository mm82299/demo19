{
    'name': 'MPHE ISO 9001 Management System',
    'version': '19.0.1.0.0',
    'category': 'Quality Management',
    'summary': 'Integrated ISO 9001 quality management system for MPHE',
    'description': """
ISO 9001 Quality Management System (SMQ)
=========================================
Consolidates all processes defined in the ISO 9001 documents:
- Document Control
- Non-Conformities & Improvement Actions (NC/CAR)
- Internal Audits & Programs
- Risk Management & Context Analysis
- Indicator Tracking & KPI
- HR Competencies & Skills Matrix
- Vendor Evaluation & Purchase Requests
- Customer Complaints & Satisfaction surveys
    """,
    'author': 'Antigravity / Montassar',
    'depends': [
        'base',
        'mail',
        'hr',
        'purchase',
        'sale',
        'crm',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/iso_sequences.xml',
        'data/iso_data.xml',
        'views/iso_action_views.xml',
        'views/iso_audit_views.xml',
        'views/iso_document_views.xml',
        'views/iso_complaint_views.xml',
        'views/iso_risk_views.xml',
        'views/iso_indicator_views.xml',
        'views/iso_regulation_views.xml',
        'views/res_partner_views.xml',
        'views/hr_employee_views.xml',
        'views/menu_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
