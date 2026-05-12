from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError


class SupplierEvaluation(models.Model):

    _name = 'supplier.evaluation'
    _description = 'Supplier Evaluation'

    name = fields.Char('Name',related='partner_id.name')
    product_conformity = fields.Integer(string='Conformité des produits ',tracking=True, default=0)
    price_respect = fields.Integer(string='Respect des prix proposés' ,tracking=True, default=0)
    delivery_delay_respect = fields.Integer(string='Respect des délais de livraison' ,tracking=True, default=0)
    delivery_mode_respect = fields.Integer(string='Respect des modes de livraison' ,tracking=True, default=0)
    payment_respect = fields.Integer(string='Respect des modalités de paiement')
    score = fields.Integer(string='Note / 25',compute='compute_score')
    date = fields.Date(string='Date',required=True)
    company_id = fields.Many2one('res.company', string='Société', default=lambda self: self.env.company, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Fournisseur', required=True)

    @api.constrains('product_conformity')
    def _check_product_conformity(self):
        for rec in self:
            if rec.product_conformity > 5 or rec.product_conformity < 0  :
                raise UserError('La note doit être comprise entre 0 et 5')

    @api.constrains('price_respect')
    def _check_price_respect(self):
        for rec in self:
            if rec.price_respect > 5 or rec.price_respect < 0:
                raise UserError('La note doit être comprise entre 0 et 5')

    @api.constrains('delivery_delay_respect')
    def _check_delivery_delay_respect(self):
        for rec in self:
            if rec.delivery_delay_respect > 5 or rec.delivery_delay_respect < 0:
                raise UserError('La note doit être comprise entre 0 et 5')

    @api.constrains('delivery_mode_respect')
    def _check_delivery_mode_respect(self):
        for rec in self:
            if rec.delivery_mode_respect > 5 or rec.delivery_mode_respect < 0:
                raise UserError('La note doit être comprise entre 0 et 5')

    @api.constrains('payment_respect')
    def _check_payment_respect(self):
        for rec in self:
            if rec.payment_respect > 5 or rec.payment_respect < 0:
                raise UserError('La note doit être comprise entre 0 et 5')
    def compute_score(self):
        for rec in self:
            rec.score = rec.product_conformity + rec.price_respect + rec.delivery_delay_respect + rec.delivery_mode_respect + rec.payment_respect