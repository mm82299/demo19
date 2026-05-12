# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResPartner(models.Model):
    """ This model represents res.partner."""
    _inherit = 'res.partner'

    operation_type_category = fields.Many2one('withholding.declaration.operation.type.category', string="Operation Type Category", copy=False)
    operation_type = fields.Many2one('withholding.declaration.operation.type', string="Operation Type", domain="[('category_id', '=', operation_type_category)]", copy=False)
    tax_id_type = fields.Selection(
        [('vat', 'VAT'), ('cin', 'CIN'), ('passport', 'Passport'), ('residence', 'Residence'), ('other', 'Other')],
        string='Tax ID Type', default='vat', copy=False)
    category_type = fields.Selection([('PP', 'Personne Physique'), ('PM', 'Personne Morale')], string='Category Type', copy=False)

    date_of_birth = fields.Date('Birth Date', copy=False)