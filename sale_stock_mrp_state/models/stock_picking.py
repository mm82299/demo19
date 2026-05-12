from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state_id = fields.Many2one(
        'res.country.state',
        related='partner_id.state_id',
        string='State',
        store=True,
        readonly=True
    )
