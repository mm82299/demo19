# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrderLine(models.Model):

    _inherit = 'sale.order.line'

    lot_id = fields.Many2one(
        comodel_name='stock.lot',
        string='Serial Number',
        domain="[('product_id', '=', product_id)]",
        help=(
            'Select the specific serial number to be delivered. '
            'It will be automatically assigned to the delivery order.'
        ),
    )
