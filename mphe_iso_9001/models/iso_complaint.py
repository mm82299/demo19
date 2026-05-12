from odoo import models, fields, api, _

class IsoComplaint(models.Model):
    _name = 'iso.complaint'
    _description = 'ISO Customer Complaint'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Complaint Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    
    reception_date = fields.Date(string='Reception Date', default=fields.Date.context_today)
    reception_mode = fields.Selection([
        ('phone', 'Phone Call'),
        ('email', 'Email'),
        ('visit', 'Client Visit'),
        ('social', 'Social Media'),
        ('survey', 'Satisfaction Survey'),
        ('other', 'Other')
    ], string='Reception Mode', required=True, default='email')
    
    subject = fields.Char(string='Subject', required=True)
    description = fields.Text(string='Description', required=True)
    
    immediate_correction = fields.Text(string='Immediate Correction / Curative Action')
    
    action_id = fields.Many2one('iso.action', string='Related Improvement Action', domain=[('origin', '=', 'complaint')])
    
    state = fields.Selection([
        ('draft', 'Draft / Received'),
        ('investigating', 'Analysis & Investigation'),
        ('resolving', 'Action set / Resolving'),
        ('validating', 'Closure / Validation'),
        ('closed', 'Closed'),
        ('cancel', 'Canceled')
    ], string='Status', default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('iso.complaint') or _('New')
        return super(IsoComplaint, self).create(vals)

    def action_investigate(self):
        self.write({'state': 'investigating'})

    def action_resolve(self):
        self.write({'state': 'resolving'})

    def action_validate(self):
        self.write({'state': 'validating'})

    def action_close(self):
        self.write({'state': 'closed'})
