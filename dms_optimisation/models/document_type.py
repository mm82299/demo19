# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DmsDocumentType(models.Model):
    _name = 'dms.document.type'
    _description = 'Type de Document DMS'
    _order = 'sequence, name'

    name = fields.Char(string='Nom', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(string='Séquence', default=10)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')
