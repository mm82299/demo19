from odoo import models, fields, api, _

class IsoAction(models.Model):
    _name = 'iso.action'
    _description = 'ISO Non-Conformity and Improvement Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    type = fields.Selection([
        ('nc', 'Non-Conformity'),
        ('improvement', 'Improvement Action'),
        ('preventive', 'Preventive Action')
    ], string='Type', required=True, default='nc', tracking=True)
    
    origin = fields.Selection([
        ('audit_internal', 'Internal Audit'),
        ('audit_external', 'External Audit'),
        ('complaint', 'Customer Complaint'),
        ('internal', 'Internal Detection'),
        ('indicator', 'KPI Analysis'),
        ('review', 'Management Review'),
        ('other', 'Other')
    ], string='Origin', required=True, tracking=True)
    
    date_detected = fields.Date(string='Detection Date', default=fields.Date.context_today)
    detected_by_id = fields.Many2one('res.users', string='Detected By', default=lambda self: self.env.user)
    
    description = fields.Text(string='Description', required=True)
    root_cause = fields.Text(string='Root Cause Analysis')
    
    action_line_ids = fields.One2many('iso.action.line', 'action_id', string='Planned Actions')
    
    verification_date = fields.Date(string='Effectiveness Verification Date')
    verification_comment = fields.Text(string='Verification Comment')
    is_effective = fields.Boolean(string='Is Effective', tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('analysis', 'Under Analysis'),
        ('progress', 'In Progress'),
        ('verification', 'Under Verification'),
        ('done', 'Closed'),
        ('cancel', 'Canceled')
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('iso.action') or _('New')
        return super(IsoAction, self).create(vals)

    def action_confirm(self):
        self.write({'state': 'analysis'})

    def action_start(self):
        self.write({'state': 'progress'})

    def action_verify(self):
        self.write({'state': 'verification'})

    def action_close(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancel'})


class IsoActionLine(models.Model):
    _name = 'iso.action.line'
    _description = 'ISO Action Detail Line'

    action_id = fields.Many2one('iso.action', string='Action', ondelete='cascade')
    description = fields.Char(string='Description', required=True)
    responsible_id = fields.Many2one('res.users', string='Responsible', required=True)
    target_date = fields.Date(string='Target Date')
    completion_date = fields.Date(string='Completion Date')
    state = fields.Selection([
        ('todo', 'To Do'),
        ('done', 'Done'),
        ('cancel', 'Canceled')
    ], string='Status', default='todo')

    def action_done(self):
        self.write({'state': 'done', 'completion_date': fields.Date.context_today(self)})
