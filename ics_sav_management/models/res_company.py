# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    """Extends res.company to add the SAV module activation flag (company-dependent)."""
    _inherit = 'res.company'

    implement_sav_module = fields.Boolean(
        string='Implement SAV Module',
        default=False,
    )
