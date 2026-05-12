from odoo import models, api, _, fields
from odoo.tools import format_date


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    withholding_id = fields.Many2one('account.withholding', string='Retenue à la Source', copy=False, tracking=True)


