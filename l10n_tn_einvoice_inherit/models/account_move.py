from odoo import api, fields, models

class AccountMove(models.Model):

    _inherit = 'account.move'

    teif_description = fields.Text(string='Description TEIF' , copy=False)

