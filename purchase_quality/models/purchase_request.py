from odoo import models, fields, api

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'

    delay_request_po = fields.Integer(
        string='Delay PR to PO (Days)',
        compute='_compute_delay_request_po',
        store=True,
        help="Delay in days between Purchase Request creation and the earliest Purchase Order creation."
    )

    @api.depends('date_start', 'line_ids.purchase_lines.order_id.date_order')
    def _compute_delay_request_po(self):
        for request in self:
            delay = 0
            if request.date_start:
                # Find all related POs
                orders = request.line_ids.mapped('purchase_lines.order_id')
                if orders:
                    # Filter out orders without date_order just in case
                    valid_orders = orders.filtered(lambda o: o.date_order)
                    if valid_orders:
                        min_date = min(valid_orders.mapped('date_order'))
                        # date_start is Date, date_order is Datetime
                        delay = (min_date.date() - request.date_start).days
            request.delay_request_po = delay
