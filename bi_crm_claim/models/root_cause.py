# -*- coding: utf-8 -*-

from odoo import models, fields

class CrmClaimRootCause(models.Model):
    _name = 'crm.claim.root.cause'
    _description = 'Root Cause'

    name = fields.Char(string='Root Cause', required=True)
    description = fields.Text(string='Description')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    claim_id = fields.Many2one('crm.claim', string='Claim')
