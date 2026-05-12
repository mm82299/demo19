# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class ExemptionCertificate(models.Model):
    _inherit = 'exemption.certificate'
    _description = 'Exemption Certificate'

    active = fields.Boolean('Active', default=True, store=True)
    is_used = fields.Boolean('Active', default=False, store=True)
    fiscal_position_type = fields.Many2one('account.fiscal.position', 'Fiscal Position', required=True, store=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _onchange_property_account_fiscal_position(self, vat_exemption):
        default_fiscal_position = self.env['account.fiscal.position'].browse(1)
        for partner in self:
            if partner.exemption_certificate_ids:
                for exemption_vat in partner.exemption_certificate_ids:
                    if exemption_vat.is_used and vat_exemption:
                        exemption = exemption_vat.fiscal_position_type
                        partner.sudo().update({
                            'property_account_position_id': exemption.id
                        })

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            fiscal_position = val.get('property_account_position_id')
            if fiscal_position:
                pass
            else:
                val['property_account_position_id'] = self.env['account.fiscal.position'].browse(1).id
        return super(ResPartner, self).create(vals)

    @api.depends('exemption_certificate_ids')
    def _is_vat_exemption(self):
        today = datetime.today()
        for partner in self:
            vat_exemption = False
            for certificate in partner.exemption_certificate_ids:
                if not certificate.end_date:
                    if today >= datetime.strptime(str(certificate.start_date), '%Y-%m-%d') and certificate.is_used:
                        vat_exemption = True
                        break
                elif datetime.strptime(str(certificate.end_date), '%Y-%m-%d') >= today >= datetime.strptime(
                        str(certificate.start_date), '%Y-%m-%d') and certificate.is_used:
                    vat_exemption = True
                    break
            partner.vat_exemption = vat_exemption
            partner._onchange_property_account_fiscal_position(vat_exemption)

    def get_certificate(self, date):
        vat_exemption = False
        for certificate in self.exemption_certificate_ids:
            if not certificate.end_date:
                if date >= certificate.start_date and certificate.is_used:
                    vat_exemption = certificate
                    break
            elif date <= certificate.end_date and date >= certificate.start_date and certificate.is_used:
                vat_exemption = certificate
                break
        return vat_exemption
