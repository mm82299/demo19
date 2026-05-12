# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """ This model represents res.config.settings."""
    _inherit = 'res.config.settings'

    ttn_vat_number_type = fields.Selection(related='company_id.ttn_vat_number_type', readonly=False)
