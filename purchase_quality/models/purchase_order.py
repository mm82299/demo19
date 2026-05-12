from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    delay_creation_confirmation = fields.Integer(
        string='Delay Order to Confirmation (Days)',
        compute='_compute_delay_creation_confirmation',
        store=True,
        help="Delay in days between Purchase Order date and confirmation."
    )

    delay_expected_effective_receipt = fields.Integer(
        string='Delay Expected vs Effective Receipt (Days)',
        compute='_compute_delay_expected_effective_receipt',
        store=True,
        help="Delay in days between Expected Receipt Date and Effective Receipt Date."
    )

    delivery_average_days = fields.Float(
        string='Delivery Average Days',
        compute='_compute_delivery_average_days',
        store=True,
        help="Average delivery days from PO confirmation to effective receipt of pickings."
    )

    @api.depends('date_order', 'date_approve')
    def _compute_delay_creation_confirmation(self):
        for order in self:
            delay = 0
            if order.date_order and order.date_approve:
                delay = (order.date_approve.date() - order.date_order.date()).days
            order.delay_creation_confirmation = delay

    @api.depends('date_planned', 'effective_date')
    def _compute_delay_expected_effective_receipt(self):
        for order in self:
            delay = 0
            if order.date_planned and order.effective_date:
                delay = (order.effective_date.date() - order.date_planned.date()).days
            order.delay_expected_effective_receipt = delay

    @api.depends('date_approve', 'picking_ids.state', 'picking_ids.date_done')
    def _compute_delivery_average_days(self):
        for order in self:
            delay = 0.0
            if order.date_approve:
                done_pickings = order.picking_ids.filtered(lambda p: p.state == 'done' and p.date_done)
                if done_pickings:
                    total_days = sum((p.date_done.date() - order.date_approve.date()).days for p in done_pickings)
                    delay = total_days / len(done_pickings)
            order.delivery_average_days = delay
