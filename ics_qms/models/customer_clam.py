from odoo import api, fields, models, _

class CustomerClam(models.Model):
    _name = 'customer.clam'
    _description = 'Customer Clam'
    _order = 'date desc, id desc'

    name = fields.Char('N°', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    date = fields.Date('Date', required=True, default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', 'Client', required=True)
    description = fields.Text('Objet de la réclamation')
    action = fields.Many2one('mgmtsystem.action', 'Action')
    responsible_id = fields.Many2one('res.users', 'Responsable', default=lambda self: self.env.user)
    date_limit = fields.Date('Échéance')
    date_close = fields.Date('Date de clôture', readonly=True)
    num_nc_file = fields.Char('Numéro du fichier NC')
    state = fields.Selection(
        [('new', 'New'), ('in_progress', 'In Progress'), ('closed', 'Closed'),
         ('rejected', 'Rejected')], string="State", default='new', tracking=True)

    def action_in_progress(self):
        for record in self:
            record.state = 'in_progress'

    def action_closed(self):
        for record in self:
            record.state = 'closed'
            record.date_close = fields.Date.context_today(self)

    def action_rejected(self):
        for record in self:
            record.state = 'rejected'

    def action_draft(self):
        for record in self:
            record.state = 'new'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('customer.clam') or _('New')
        return super().create(vals_list)

