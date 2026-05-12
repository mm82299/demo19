{
    'name': 'ICS Debranding',
    'summary': 'Remove Odoo branding from Backend and Emails',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'license': 'LGPL-3',
    'author': 'ICS',
    'depends': [
        'base',
        'web',
        'mail',
    ],
    'data': [
        'views/web_layout.xml',
        # 'views/res_config_settings.xml',
        'data/mail_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ics_debranding/static/src/js/**/*.js',
            'ics_debranding/static/src/scss/**/*.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
