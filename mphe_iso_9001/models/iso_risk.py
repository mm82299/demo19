from odoo import models, fields, api, _

class IsoRisk(models.Model):
    _name = 'iso.risk'
    _description = 'ISO Risk Assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference/Title', required=True, tracking=True)
    process_id = fields.Many2one('iso.process', string='Related Process')
    category = fields.Selection([
        ('strategic', 'Strategic'),
        ('operational', 'Operational'),
        ('financial', 'Financial'),
        ('compliance', 'Compliance / Legal'),
        ('technical', 'Technical'),
        ('other', 'Other')
    ], string='Category', required=True, default='operational')
    
    description = fields.Text(string='Description / Scenario')
    
    probability = fields.Selection([
        ('1', '1 - Rare'),
        ('2', '2 - Unlikely'),
        ('3', '3 - Possible'),
        ('4', '4 - Likely'),
        ('5', '5 - Almost Certain')
    ], string='Probability (P)', default='3')
    
    impact = fields.Selection([
        ('1', '1 - Minimal'),
        ('2', '2 - Minor'),
        ('3', '3 - Medium'),
        ('4', '4 - Major'),
        ('5', '5 - Critical')
    ], string='Impact (I)', default='3')
    
    score = fields.Integer(string='Risk Score (PxI)', compute='_compute_score', store=True)
    
    treatment_strategy = fields.Selection([
        ('accept', 'Accept'),
        ('avoid', 'Avoid'),
        ('mitigate', 'Mitigate'),
        ('transfer', 'Transfer')
    ], string='Strategy', tracking=True)
    
    treatment_plan = fields.Text(string='Treatment / Action Plan')
    
    action_id = fields.Many2one('iso.action', string='Related Improvement Action')
    
    active = fields.Boolean(default=True)

    @api.depends('probability', 'impact')
    def _compute_score(self):
        for rec in self:
            rec.score = int(rec.probability or 0) * int(rec.impact or 0)

class IsoInterestedParty(models.Model):
    _name = 'iso.interested.party'
    _description = 'ISO Interested Party'
    
    name = fields.Char(string='Name / Category', required=True)
    expectations = fields.Text(string='Requirements and Expectations')
    influence = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], string='Influence level', default='medium')
    treatment = fields.Text(string='Management / Communication Action')
    active = fields.Boolean(default=True)
