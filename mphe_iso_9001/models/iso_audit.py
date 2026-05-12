from odoo import models, fields, api, _

class IsoAudit(models.Model):
    _name = 'iso.audit'
    _description = 'ISO Internal Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    audit_program = fields.Char(string='Audit Program', required=True)
    audit_type = fields.Selection([
        ('internal', 'Internal Audit'),
        ('external', 'External Audit (Certification)'),
        ('supplier', 'Supplier Audit')
    ], string='Audit Type', default='internal', required=True)
    
    planned_start_date = fields.Date(string='Planned Start Date')
    planned_end_date = fields.Date(string='Planned End Date')
    
    lead_auditor_id = fields.Many2one('res.users', string='Lead Auditor')
    auditor_ids = fields.Many2many('res.users', 'iso_audit_auditor_rel', 'audit_id', 'user_id', string='Audit Team')
    
    scope = fields.Text(string='Audit Scope')
    finding_ids = fields.One2many('iso.audit.finding', 'audit_id', string='Audit Findings')
    
    summary = fields.Html(string='Executive Summary')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('reporting', 'Reporting'),
        ('closed', 'Closed'),
        ('cancel', 'Canceled')
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('iso.audit') or _('New')
        return super(IsoAudit, self).create(vals)

    def action_schedule(self):
        self.write({'state': 'scheduled'})

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_report(self):
        self.write({'state': 'reporting'})

    def action_close(self):
        self.write({'state': 'closed'})


class IsoAuditFinding(models.Model):
    _name = 'iso.audit.finding'
    _description = 'ISO Audit Finding'

    audit_id = fields.Many2one('iso.audit', string='Audit', ondelete='cascade')
    finding_type = fields.Selection([
        ('major_nc', 'Major Non-Conformity'),
        ('minor_nc', 'Minor Non-Conformity'),
        ('ofi', 'Opportunity for Improvement'),
        ('remark', 'Remark')
    ], string='Finding Type', required=True)
    
    process_id = fields.Many2one('iso.process', string='Audited Process')
    description = fields.Text(string='Description', required=True)
    action_id = fields.Many2one('iso.action', string='Related Improvement Action')

class IsoProcess(models.Model):
    _name = 'iso.process'
    _description = 'ISO Processes'
    
    name = fields.Char(string='Process Name', required=True)
    owner_id = fields.Many2one('res.users', string='Process Owner')
    description = fields.Text(string='Objectives and Scope')
    active = fields.Boolean(default=True)
