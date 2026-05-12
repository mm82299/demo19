from odoo import models, fields, api, _

class IsoRegulation(models.Model):
    _name = 'iso.regulation'
    _description = 'ISO Regulatory Watch (Veille Réglementaire)'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Regulation Title', required=True)
    reference = fields.Char(string='Reference Number')
    date_published = fields.Date(string='Date Published')
    
    source = fields.Char(string='Source / Authority')
    applicability = fields.Text(string='Applicability / Impact on SMQ')
    
    compliance_status = fields.Selection([
        ('compliant', 'Compliant'),
        ('non_compliant', 'Non-Compliant (Action needed)'),
        ('not_applicable', 'Not Applicable'),
        ('pending', 'Under Analysis')
    ], string='Compliance Status', default='pending', tracking=True)
    
    action_id = fields.Many2one('iso.action', string='Related Improvement Action')
    
    last_check_date = fields.Date(string='Last Verification Date', default=fields.Date.context_today)
    next_check_date = fields.Date(string='Next Verification Date')

    active = fields.Boolean(default=True)
