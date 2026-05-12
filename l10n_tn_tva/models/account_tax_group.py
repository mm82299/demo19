from odoo import fields, models, api


class AccountTaxGrou(models.Model):
    _inherit = 'account.tax.group'

    is_tva = fields.Boolean('TVA', default=False)
