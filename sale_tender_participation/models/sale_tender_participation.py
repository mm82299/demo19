from odoo import models, fields, api

class SaleTenderParticipation(models.Model):
    _name = 'sale.tender.participation'
    _description = "Dossier d'Appel d'Offres / Consultation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Référence de l'appel d'offres", required=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Client / Organisme', tracking=True)
    date = fields.Date(string='Date de soumission', default=fields.Date.context_today, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsable', default=lambda self: self.env.user, tracking=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('won', 'Gagné'),
        ('lost', 'Perdu'),
        ('cancelled', 'Annulé')
    ], string='Statut', default='draft', tracking=True)
    description = fields.Text(string='Description / Remarques')
    
    sale_order_ids = fields.One2many('sale.order', 'tender_participation_id', string='Devis / Commandes')
    sale_order_count = fields.Integer(string='Nombre de devis', compute='_compute_sale_order_count')

    @api.depends('sale_order_ids')
    def _compute_sale_order_count(self):
        for record in self:
            record.sale_order_count = len(record.sale_order_ids)
            
    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Devis et Commandes',
            'view_mode': 'list,form',
            'res_model': 'sale.order',
            'domain': [('tender_participation_id', '=', self.id)],
            'context': {'default_tender_participation_id': self.id, 'default_partner_id': self.partner_id.id},
        }

    def action_submit(self):
        for record in self:
            record.state = 'submitted'

    def action_won(self):
        for record in self:
            record.state = 'won'

    def action_lost(self):
        for record in self:
            record.state = 'lost'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_draft(self):
        for record in self:
            record.state = 'draft'
