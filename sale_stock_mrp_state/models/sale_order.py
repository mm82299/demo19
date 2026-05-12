from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    state_id = fields.Many2one(
        'res.country.state',
        related='partner_shipping_id.state_id',
        string='State',
        store=True,
        readonly=True
    )
