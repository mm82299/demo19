from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    state_id = fields.Many2one(
        'res.country.state',
        related='partner_id.state_id',
        string='State',
        store=True,
        readonly=True
    )

    total_weight_demanded = fields.Float(compute='_compute_weights', string='Poids Demandé', store=True)
    total_weight_done = fields.Float(compute='_compute_weights', string='Poids Réalisé', store=True)

    @api.depends('move_ids.product_uom_qty', 'move_ids.quantity', 'move_ids.product_id.weight')
    def _compute_weights(self):
        for picking in self:
            demanded = 0.0
            done = 0.0
            for move in picking.move_ids:
                weight = move.product_id.weight
                if weight > 0:
                    demanded += move.product_uom_qty * weight
                    done += move.quantity * weight
            picking.total_weight_demanded = demanded
            picking.total_weight_done = done
