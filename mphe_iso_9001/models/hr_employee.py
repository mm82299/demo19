from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_internal_auditor = fields.Boolean(string='Internal Auditor (ISO)')
    
    skill_ids = fields.One2many('hr.employee.skill.iso', 'employee_id', string='Skills Matrix')
    
    entry_date = fields.Date(string='Company Entry Date')
    
    last_review_date = fields.Date(string='Last Performance/Competence Review')
    next_review_date = fields.Date(string='Next Review Date')
    
    cv_file = fields.Binary(string='CV / Diplomas Attachment', attachment=True)
    filename = fields.Char(string='CV Filename')

class HrEmployeeSkillISO(models.Model):
    _name = 'hr.employee.skill.iso'
    _description = 'Employee Skill - ISO 9001'

    employee_id = fields.Many2one('hr.employee', string='Employee')
    skill_name = fields.Char(string='Skill Description', required=True)
    level = fields.Selection([
        ('none', 'None / Not acquired'),
        ('basic', 'Basic / Learning'),
        ('intermediate', 'Intermediate / Autonomous'),
        ('expert', 'Expert / Trainer')
    ], string='Proficiency Level', default='none', required=True)
    
    evidence = fields.Text(string='Evidence / Observation')
