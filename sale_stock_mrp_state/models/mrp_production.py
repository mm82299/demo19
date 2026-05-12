from odoo import models, fields, api

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    state_id = fields.Many2one(
        'res.country.state',
        related='sale_line_id.order_id.partner_shipping_id.state_id',
        string='State',
        store=True,
        readonly=True
    )

    product_weight = fields.Float(related='product_id.weight', string='Product Weight', readonly=True)
    total_weight = fields.Float(compute='_compute_total_weight', string='Total Weight', store=True)

    @api.depends('product_qty', 'product_id.weight')
    def _compute_total_weight(self):
        for production in self:
            production.total_weight = production.product_qty * production.product_id.weight
