# -*- coding: utf-8 -*-
from odoo import fields, models


class StockMoveLine(models.Model):
    """Extends stock.move.line with a customs file reference for reception traceability."""
    _inherit = 'stock.move.line'

    customs_file_ref = fields.Char(
        string='Customs File Reference',
        help=(
            'Customs file reference number. '
            'Automatically copied to the serial number (lot) record upon reception validation.'
        ),
    )
