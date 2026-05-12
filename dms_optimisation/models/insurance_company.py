# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DmsInsuranceCompany(models.Model):
    _name = 'dms.insurance.company'
    _description = 'Compagnie d\'Assurance'
    _order = 'name'

    name = fields.Char(string='Nom', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True)
    note = fields.Text(string='Notes')
