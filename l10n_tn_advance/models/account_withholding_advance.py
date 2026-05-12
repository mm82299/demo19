# -*- coding: utf-8 -*-
#############################################################################
#
#    Infotech Consulting Services Pvt. Ltd.
#
#    Copyright (C) 2020-TODAY Infotech Consulting Services(<https://www.ics-tunisie.com>)
#    Author: Infotech Consulting Services(<http://www.ics-tunisie.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################


from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError


class AccountWithholdingAdvanceTax(models.Model):
    _name = 'account.withholding.advance.tax'
    _description = 'Account Withholding Advance Tax'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Nom de la Retenue', required=True)
    rate = fields.Float(string='Taux %', required=True, digits='Discount')
    account_id = fields.Many2one('account.account', string='Compte Fiscal',
                                 ondelete='restrict', required=True, readonly=False)
    refund_account_id = fields.Many2one('account.account', string='Compte Fiscal sur les Remboursements', ondelete='restrict',
                                        readonly=False, required=True)
    type_withholding = fields.Selection([
        ('vente', 'Vente'),
    ], 'Type taxe', required=True, default='vente', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    company_id = fields.Many2one(
        'res.company', string='Entreprise', change_default=True,
        required=True, readonly=False,
        default=lambda self: self.env.company
    )


class AccountWithholdingAdvance(models.Model):
    _name = 'account.withholding.advance'
    _description = 'Account Withholding Advance'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Nom', index=True, default='/')
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Fait'),
        ('cancel', 'Annuler')
    ], string='Statut', default='draft', readonly=True)
    type = fields.Selection([
        ('out_withholding', 'Retenue du Client'),
    ], readonly=True, default='out_withholding')
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True)

    partner_id = fields.Many2one('res.partner', string='Partenaire', required=True, domain="[('is_state', '=', True)]")
    invoice_ids = fields.One2many('account.move', inverse_name='withholding_advance_id', string='Factures')
    tax_id = fields.Many2one('account.withholding.advance.tax', string='Type de retenue', domain="[('company_id', '=', company_id)]", required=True, tracking=True)
    journal_id = fields.Many2one('account.journal', string='Journal', related='tax_id.journal_id', readonly=True, store=True)
    company_id = fields.Many2one(
        'res.company', string='Entreprise', change_default=True,
        required=True, readonly=False,
        default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
        string="Devise de l'entreprise",
        readonly=True
    )
    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')
    amount_total_rs = fields.Monetary(string='Montant Total', compute="_compute_amount_total_rs")
    retenue_amount = fields.Monetary(
        string='Montant Retenue', compute='_compute_amount',
        digits='Product Price'
    )
    amount_advance = fields.Monetary(string='Montant avance', digits='Product Price')
    withholding_advance = fields.Boolean(string='Retenue sur avance', default=False)
    account_move_id = fields.Many2one('account.move', string='Pièce Comptable', readonly=True)

    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.journal_id.company_id.currency_id or record.company_id.currency_id

    @api.depends('invoice_ids', 'tax_id', 'withholding_advance')
    def _compute_amount_total_rs(self):
        for record in self:
            invoice_sum = 0.0
            if record.tax_id:
                for invoice in record.invoice_ids:
                    invoice_totals = invoice.tax_totals
                    for amount_by_group_list in invoice_totals.get('groups_by_subtotal', {}).values():
                        for amount_by_group in amount_by_group_list:
                            tax_group_id = amount_by_group['tax_group_id']
                            tax_group = self.env['account.tax.group'].sudo().browse(tax_group_id)
                            if tax_group.is_tva:
                                if invoice.move_type == 'out_refund':
                                    invoice_sum -= amount_by_group['tax_group_amount']
                                else:
                                    invoice_sum += amount_by_group['tax_group_amount']
            record.amount_total_rs = round(invoice_sum, 3)

    @api.depends('amount_total_rs', 'tax_id')
    def _compute_amount(self):
        for record in self:
            if record.tax_id:
                record.retenue_amount = round(record.amount_total_rs * 0.01 * record.tax_id.rate, 3)
            else:
                record.retenue_amount = 0.0

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        self.invoice_ids = False

    def button_validate_withholding(self):
        self.ensure_one()
        if self.retenue_amount <= 0:
            raise UserError(_("Le montant de la retenue doit être supérieur à zéro."))

        if self.name == '/' or not self.name:
            self.name = self.env['ir.sequence'].next_by_code('account.withholding.advance') or '/'

        today = self.date
        vals = {
            'ref': self.name + " " + self.partner_id.name,
            'journal_id': self.journal_id.id,
            'date': today,
            'partner_id': self.partner_id.id,
            'move_type': 'entry',
            'line_ids': [],
        }
        
        partner_account_id = self.partner_id.property_account_receivable_id.id
        debit = 0.0
        credit = self.retenue_amount
        
        # Line for Partner
        vals['line_ids'].append((0, 0, {
            'name': self.name + " " + self.partner_id.name,
            'partner_id': self.partner_id.id,
            'account_id': partner_account_id,
            'debit': debit,
            'credit': credit,
        }))

        # Line for Withholding Account
        vals['line_ids'].append((0, 0, {
            'name': self.name + " " + self.partner_id.name,
            'partner_id': self.partner_id.id,
            'account_id': self.tax_id.account_id.id,
            'debit': credit,
            'credit': debit,
        }))

        self.account_move_id = self.env['account.move'].create(vals)
        self.account_move_id.action_post()
        self.state = 'done'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Vous ne pouvez pas supprimer une retenue validée ou annulée."))
        return super(AccountWithholdingAdvance, self).unlink()

    def button_cancel(self):
        self.write({'state': 'cancel'})
        if self.account_move_id:
            self.account_move_id.button_cancel()

    def button_draft(self):
        self.write({'state': 'draft'})

    def button_account_move(self):
        return {
            'name': _('Écritures comptables'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'res_id': self.account_move_id.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                 vals['name'] = self.env['ir.sequence'].next_by_code('account.withholding.advance') or '/'
        return super(AccountWithholdingAdvance, self).create(vals_list)
