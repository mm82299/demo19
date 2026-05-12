# -*- coding: utf-8 -*-

from odoo import models, fields

class CrmClaimResolutionAction(models.Model):
    _name = 'crm.claim.resolution.action'
    _description = 'Resolution Action'

    action_type = fields.Selection([
        ('correction', 'Corrective Action'),
        ('prevention', 'Preventive Action')
    ], string='Action Type')
    description = fields.Text(string='Description')
    responsable = fields.Char(string='Responsable')
    user_id = fields.Many2one('res.users', string='Responsible User')
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High')
    ], string='Priority', default='1')
    criticality = fields.Selection([
        ('0', 'Minor'),
        ('1', 'Major'),
        ('2', 'Critical')
    ], string='Criticality', default='0')
    claim_id = fields.Many2one('crm.claim', string='Claim')
