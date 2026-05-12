from odoo import models, fields, api, _
from datetime import date
from odoo.exceptions import UserError


class AccountWithholdingTax(models.Model):
    _name = 'account.withholding.tax'
    _description = 'Account Withholding Tax'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    name = fields.Char(string='Nom de la taxe', required=True, tracking=True)

    rate = fields.Float(string='Taux %', required=True, digits='Discount', tracking=True)

    account_id = fields.Many2one('account.account', string='Compte Fiscal',
                                 ondelete='restrict', required=True, readonly=False, tracking=True)
    refund_account_id = fields.Many2one('account.account', string='Compte Fiscal sur les Remboursements', ondelete='restrict',
                                        readonly=False, required=True, tracking=True)
    type_withholding = fields.Selection([
        ('vente', 'Vente'),
        ('achat', 'Achat'),
    ], 'Type taxe', required=True, default='vente', tracking=True)

    journal_id = fields.Many2one('account.journal', string='Journal', required=True, tracking=True)

    company_id = fields.Many2one(
        'res.company', string='Entreprise', change_default=True,
        required=True,
        default=lambda self: self.env.company
    )

class AccountWithholding(models.Model):
    _name = 'account.withholding'
    _description = 'Account Withholding'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']

    def _set_name(self):
        return self.env['ir.sequence'].next_by_code('account.withholding')

    def get_account_tax(self):
        for rec in self:
            rec.tax = rec.account_withholding_tax_ids.name

    name = fields.Char(string='Name', index=True)
    tax = fields.Char(compute='get_account_tax', string='Type de retenue à la source', tracking=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('done', 'Fait'),
        ('cancel', 'Annuler')
    ], string='Statut', default='draft', readonly=True)
    type = fields.Selection([
        ('out_withholding', 'Retenue du Client'),
        ('in_withholding', 'Retenue du Fournisseur')
    ], readonly=True, tracking=True)
    date = fields.Date(string='Date', default=fields.Date.context_today, required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', required=True, tracking=True)
    account_invoice_ids = fields.One2many('account.move', inverse_name='withholding_id', string='Factures')
    account_withholding_tax_ids = fields.Many2one('account.withholding.tax', string='Type de retenue', domain="[('company_id', '=', company_id)]", required=True, tracking=True)
    account_withholding_tax_type = fields.Selection(string='Type taxe', related='account_withholding_tax_ids.type_withholding',
        readonly=True, store=True
    )
    journal_id = fields.Many2one('account.journal', string='Journal', related="account_withholding_tax_ids.journal_id", required=True, tracking=True)
    
    company_id = fields.Many2one(
        'res.company', string='Entreprise', change_default=True,
        required=True,
        default=lambda self: self.env.company
    )
    company_currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id',
        string="Devise de l'entreprise",
        readonly=True
    )
    amount_total_rs = fields.Monetary(string='Montant Total', compute="_compute_amount_total_rs")

    def _compute_amount_total_rs(self):
        if self.withholding_advance:
            for record in self:
                lst_price = 0.0
                lst_price_rs = 0.0
                if record.account_withholding_tax_ids:
                    invoice_sum = 0.0
                    for invoice in record.account_invoice_ids:
                        if invoice.move_type == 'out_refund':
                            invoice_sum -= invoice.amount_total
                        if invoice.move_type == 'out_invoice':
                            invoice_sum += invoice.amount_total
                        if invoice.move_type == 'in_refund':
                            invoice_sum -= invoice.amount_total
                        if invoice.move_type == 'in_invoice':
                            invoice_sum += invoice.amount_total
                    lst_price += invoice_sum
                    lst_price_rs = lst_price + record.amount_advance

            self.amount_total_rs = round(lst_price_rs, 3)
        else:
            for record in self:
                lst_price = 0.0
                if record.account_withholding_tax_ids:
                    invoice_sum = 0.0
                    for invoice in record.account_invoice_ids:
                        if invoice.move_type == 'out_refund':
                            invoice_sum -= invoice.amount_total
                        if invoice.move_type == 'out_invoice':
                            invoice_sum += invoice.amount_total
                        if invoice.move_type == 'in_refund':
                            invoice_sum -= invoice.amount_total
                        if invoice.move_type == 'in_invoice':
                            invoice_sum += invoice.amount_total
                    lst_price += invoice_sum
                record.amount_total_rs = round(lst_price, 3)
                print('test', record.amount_total_rs)

    def _compute_currency_id(self):
        self.currency_id = self.journal_id.company_id.currency_id

    currency_id = fields.Many2one('res.currency', compute='_compute_currency_id')
    retenue_amount = fields.Float(
        string='Retenue à la source', compute='_compute_amount',
        digits='Product Price'
    )
    amount_advance = fields.Float(string='Montant avance', digits='Product Price')
    withholding_advance = fields.Boolean(string='Retenue sur avance', default=0)
    account_move_id = fields.Many2one('account.move')

    @api.onchange('partner_id')
    def _partner_id_onchange(self):
        for invoice in self.account_invoice_ids:
            invoice.write({'withholding_id': False})
        self.account_invoice_ids = []


    def _compute_amount(self):
        for record in self:
            sum = 0.0
            for tax in record.account_withholding_tax_ids:
                invoice_sum = 0.0
                for invoice in record.account_invoice_ids:
                    if invoice.move_type == 'out_refund':
                        invoice_sum -= invoice.amount_total
                    if invoice.move_type == 'out_invoice':
                        invoice_sum += invoice.amount_total
                    if invoice.move_type == 'in_refund':
                        invoice_sum -= invoice.amount_total
                    if invoice.move_type == 'in_invoice':
                        invoice_sum += invoice.amount_total
                sum += (invoice_sum * 0.01 * tax.rate)

        if record.withholding_advance:
            rs_sum = 0.0
            rs_sum = sum + (record.amount_advance * 0.01 * tax.rate)
            record.retenue_amount = round(rs_sum, 3)
        else:
            record.retenue_amount = round(sum, 3)

    def button_validate_withholding(self):
        self.ensure_one()

        if self.amount_advance == 0.0 and not all(obj.account_invoice_ids for obj in self):
            raise UserError(
                _("Vous ne pouvez pas valider: Vous devez ajouter au moins une Ligne de facture ou entrer "
                  "un Montant d'avance.")
            )

        today = self.date
        ref_name = f"{self.name} {self.partner_id.name}"
        journal = self.journal_id
        company_id = journal.company_id.id
        partner_id = self.partner_id.id

        vals = {
            'ref': ref_name,
            'journal_id': journal.id,
            'narration': False,
            'date': today,
            'partner_id': partner_id,
            'line_ids': [],
        }

        partner_account_id = (
            self.partner_id.property_account_payable_id.id
            if self.type == 'in_withholding'
            else self.partner_id.property_account_receivable_id.id
        )

        if self.withholding_advance:
            credit = abs(self.retenue_amount) if self.type == 'in_withholding' else 0.0
            debit = abs(self.retenue_amount) if self.type == 'out_withholding' else 0.0
            debit_wth = credit
            credit_wth = debit
        else:
            debit = abs(self.retenue_amount) if self.type == 'in_withholding' else 0.0
            credit = abs(self.retenue_amount) if self.type == 'out_withholding' else 0.0
            debit_wth = credit  # flipped
            credit_wth = debit  # flipped

        # Partner line dict
        partner_line = {
            'name': ref_name,
            'journal_id': journal.id,
            'company_id': company_id,
            'credit': credit,
            'debit': debit,
            'date': today,
            'partner_id': partner_id,
            'account_id': partner_account_id,
        }
        vals['line_ids'].append([0, False, partner_line])

        withholding_line = {
            'name': ref_name,
            'journal_id': journal.id,
            'company_id': company_id,
            'credit': credit_wth,
            'debit': debit_wth,
            'date': today,
            'partner_id': partner_id,
            'account_id': self.account_withholding_tax_ids.account_id.id,
        }
        vals['line_ids'].append([0, False, withholding_line])

        self.account_move_id = self.env['account.move'].create(vals)

        self.account_move_id.action_post()
        self.state = 'done'


    def unlink(self):
        for move in self:
            if move.account_move_id and move.account_move_id.state == 'draft':
                self.account_move_id.with_context(force_delete=True).unlink()
            elif move.account_move_id and move.account_move_id.state != 'draft':
                raise UserError(_("You cannot delete an entry which has been posted once."))
        return super(AccountWithholding, self).unlink()

    def button_cancel(self):
        self.account_move_id.button_draft()
        self.state = 'draft'

    def button_draft(self):
        self.account_move_id.with_context(force_delete=True).unlink()
        self.state = 'cancel'

    def button_account_move(self):
        return {
            'name': 'Pièce Comptable',
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'res_id': self.account_move_id.id,
        }

    def __modify_account_withholding_name(self, values):
        print('VALUE', values)
        for val in values:
            account_holding_type = val.get('account_withholding_tax_type', False)
            if not account_holding_type and val.get('account_withholding_tax_ids'):
                withholding_id = self.env['account.withholding.tax'].browse([val.get('account_withholding_tax_ids')])
                if withholding_id.exists():
                    account_holding_type = withholding_id.type_withholding
            if val.get('name', 'New') == 'New':
                if account_holding_type == 'vente':
                    val['name'] = self.env['ir.sequence'].next_by_code('account.withholding')
                if account_holding_type == 'achat':
                    val['name'] = self.env['ir.sequence'].next_by_code('account.withholding.achat')
            return val

    @api.model_create_multi
    def create(self, values):
        values = self.__modify_account_withholding_name(values)
        result = super(AccountWithholding, self).create(values)
        return result
