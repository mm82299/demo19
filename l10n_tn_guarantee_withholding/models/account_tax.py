# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountTax(models.Model):
    """ This model represents account.tax."""
    _inherit = 'account.tax'

    is_guarantee_withholding = fields.Boolean(string='Retenu de garantie')
