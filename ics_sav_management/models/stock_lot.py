# -*- coding: utf-8 -*-
from odoo import fields, models


class StockLot(models.Model):
    """Extends stock.lot (serial number) with a customs file reference."""
    _inherit = 'stock.lot'

    customs_file_ref = fields.Char(
        string='Customs File Reference',
        help='Customs reference automatically copied from the reception move line.',
        tracking=True,
    )
