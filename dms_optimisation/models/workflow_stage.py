# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DmsWorkflowStage(models.Model):
    _name = 'dms.workflow.stage'
    _description = 'Étape du Workflow DMS'
    _order = 'sequence, id'

    name = fields.Char(string='Nom', required=True, translate=True)
    sequence = fields.Integer(string='Séquence', default=10)
    fold = fields.Boolean(string='Replié dans le Kanban', default=False)
    state_mapping = fields.Selection([
        ('brouillon', 'Brouillon'),
        ('reception', 'Réception'),
        ('en_cours', 'En cours'),
        ('approbation', 'Approbation'),
        ('termine', 'Terminé'),
        ('archive', 'Archivé'),
    ], string='État correspondant', default='en_cours')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
