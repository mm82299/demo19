from odoo import models, fields, api, _

class IsoDocument(models.Model):
    _name = 'iso.document'
    _description = 'ISO Quality Management Document Control'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Document Name', required=True, tracking=True)
    reference = fields.Char(string='Document Code', required=True, tracking=True)
    type = fields.Selection([
        ('pcs', 'Process (PCS)'),
        ('pro', 'Procedure (PRO)'),
        ('enr', 'Form / Record (ENR)'),
        ('ins', 'Work Instruction (INS)'),
        ('ext', 'External Document'),
        ('other', 'Other')
    ], string='Document Type', required=True, default='enr')
    
    process_id = fields.Many2one('iso.process', string='Related Process')
    version = fields.Char(string='Current Version', default='01', required=True, tracking=True)
    
    issue_date = fields.Date(string='Current Issue Date', default=fields.Date.context_today)
    approved_by_id = fields.Many2one('res.users', string='Approved By')
    
    file = fields.Binary(string='File Content', attachment=True)
    filename = fields.Char(string='File Name')
    
    next_review_date = fields.Date(string='Scheduled Review Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approval', 'Under Approval'),
        ('active', 'Released'),
        ('obsolete', 'Obsolete')
    ], string='Status', default='draft', tracking=True)

    def action_request_approval(self):
        self.write({'state': 'approval'})

    def action_release(self):
        self.write({'state': 'active', 'issue_date': fields.Date.context_today(self)})

    def action_obsolete(self):
        self.write({'state': 'obsolete'})
