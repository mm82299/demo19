from odoo import fields, models, api


class Partner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean('Is Customer', default=False)
    is_supplier = fields.Boolean('Is Supplier', default=False)

    supplier_location = fields.Selection([('local', 'Local'), ('foreign', 'Foreign')],'Supplier Location', default='local')

    def create_customer_accounting_account(self):
        for partner in self:
            if partner.is_customer:
                if partner.property_account_receivable_id and partner.property_account_receivable_id.name != partner.name and not partner.parent_id:
                    group_account_id = self.env['account.group'].sudo().search([('code_prefix_start', '=', '411')], limit=1).id
                    already_account = self.env['account.account'].sudo().search([('name', '=', partner.name), ('group_id', '=', group_account_id)], limit=1)
                    if already_account:
                        partner.property_account_receivable_id = already_account.id
                    else:
                        account = self.env['account.account'].sudo().create({
                                'name': partner.name,
                                'code': self.env['ir.sequence'].next_by_code('receivable.account.seq'),
                                'account_type': 'asset_receivable',
                                'reconcile': True,
                                'group_id': group_account_id,
                            })
                        partner.property_account_receivable_id = account.id
                elif partner.property_account_receivable_id and partner.property_account_receivable_id.name != partner.name and partner.parent_id:
                    group_account_id = self.env['account.group'].sudo().search([('code_prefix_start', '=', '411')], limit=1).id
                    already_account = self.env['account.account'].sudo().search([('name', '=', partner.parent_id.name), ('group_id', '=', group_account_id)], limit=1)
                    if already_account:
                        partner.property_account_receivable_id = already_account.id
                        partner.parent_id.property_account_receivable_id = already_account.id
                    else:
                        account = self.env['account.account'].sudo().create({
                                'name': partner.parent_id.name,
                                'code': self.env['ir.sequence'].next_by_code('receivable.account.seq'),
                                'account_type': 'asset_receivable',
                                'reconcile': True,
                                'group_id': group_account_id,
                            })
                        partner.property_account_receivable_id = account.id
                        partner.parent_id.property_account_receivable_id = account.id

    def create_vendor_accounting_account(self):
        for partner in self:
            if partner.is_supplier:
                if partner.property_account_payable_id and partner.property_account_payable_id.name != partner.name and not partner.parent_id:
                    group_account_id = self.env['account.group'].sudo().search([('code_prefix_start', '=', '401')], limit=1).id
                    already_account = self.env['account.account'].sudo().search([('name', '=', partner.name), ('group_id', '=', group_account_id)], limit=1)
                    if already_account:
                        partner.property_account_payable_id = already_account.id
                    else:
                        account = self.env['account.account'].sudo().create({
                                'name': partner.name,
                                'code': self.env['ir.sequence'].next_by_code('payable.account.seq'),
                                'account_type': 'liability_payable',
                                'reconcile': True,
                                'group_id': group_account_id,
                            })
                        partner.property_account_payable_id = account.id
                elif partner.property_account_receivable_id and partner.property_account_payable_id.name != partner.name and partner.parent_id:
                    group_account_id = self.env['account.group'].sudo().search([('code_prefix_start', '=', '401')], limit=1).id
                    already_account = self.env['account.account'].sudo().search([('name', '=', partner.parent_id.name), ('group_id', '=', group_account_id)], limit=1)
                    if already_account:
                        partner.property_account_payable_id = already_account.id
                        partner.parent_id.property_account_payable_id = already_account.id
                    else:
                        account = self.env['account.account'].sudo().create({
                                'name': partner.parent_id.name,
                                'code': self.env['ir.sequence'].next_by_code('payable.account.seq'),
                                'account_type': 'liability_payable',
                                'reconcile': True,
                                'group_id': group_account_id,
                            })
                        partner.property_account_payable_id = account.id
                        partner.parent_id.property_account_payable_id = account.id

    @api.model_create_multi
    def create(self, vals):
        res = super(Partner, self).create(vals)
        if self.env.company.partner_account_configuration:
            res.create_customer_accounting_account()
            res.create_vendor_accounting_account()
        return res