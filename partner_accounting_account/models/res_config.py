from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    partner_account_configuration = fields.Boolean(string='Auto Partner Account Configuration', default=False, help=
        'This field controls the automatic configuration of partner accounts. When enabled, the system will automatically set up partner accounts based on predefined rules or templates, simplifying the account creation process and ensuring consistency across partner accounts. Make sure to review the configuration settings to ensure they align with your business requirements before enabling this option.')


class ResConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    partner_account_configuration = fields.Boolean(string='Auto Partner Account Configuration', readonly=False, related='company_id.partner_account_configuration', help='This field controls the automatic configuration of partner accounts. When enabled, the system will automatically set up partner accounts based on predefined rules or templates, simplifying the account creation process and ensuring consistency across partner accounts. Make sure to review the configuration settings to ensure they align with your business requirements before enabling this option.')
    


