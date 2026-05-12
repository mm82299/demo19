from odoo import models, fields

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    state_id = fields.Many2one(
        'res.country.state',
        related='sale_line_id.order_id.partner_shipping_id.state_id',
        string='State',
        store=True,
        readonly=True
    )
