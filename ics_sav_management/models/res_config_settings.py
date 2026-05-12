# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Exposes the SAV module activation flag in General Settings."""
    _inherit = 'res.config.settings'

    implement_sav_module = fields.Boolean(
        string='Activate SAV Module',
        readonly=False,
        related='company_id.implement_sav_module',
        help=(
            'When enabled, the After-Sales Service (SAV) module is activated for this company. '
            'Product lifecycle tracking, warranty management, and customs traceability features '
            'will become available.'
        ),
    )