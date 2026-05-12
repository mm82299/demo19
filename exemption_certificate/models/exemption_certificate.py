# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime


class exemption_certificate(models.Model):
    _name = 'exemption.certificate'
    _description = 'Exemption Certificate'

    name = fields.Char('Number', required=True)
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date')
    certificate = fields.Binary(string='Certificate', attachment=True)
    file_name = fields.Char("file name",  size=64)
    partner_id = fields.Many2one('res.partner', 'Partner')


class res_partner(models.Model):
    _inherit = 'res.partner'

    exemption_certificate_ids = fields.One2many('exemption.certificate', 'partner_id', 'Exemption Certificate')
    vat_exemption = fields.Boolean(string="VAT Exemption", compute='_is_vat_exemption')


    @api.depends('exemption_certificate_ids')
    def _is_vat_exemption(self):
        vat_exemption = False
        today = datetime.today()
        for certificate in self.exemption_certificate_ids:
            if not certificate.end_date and certificate.active:
                if today >= datetime.strptime(str(certificate.start_date), '%Y-%m-%d'):
                    vat_exemption = True
                    break
            elif today <= datetime.strptime(str(certificate.end_date), '%Y-%m-%d') and today >= datetime.strptime(
                    str(certificate.start_date), '%Y-%m-%d') and certificate.active:
                vat_exemption = True
                break
        self.vat_exemption = vat_exemption

    def get_certificate(self, date):
        vat_exemption = False
        date = datetime.strptime(date[:10], '%Y-%m-%d')
        for certificate in self.exemption_certificate_ids:
            if not certificate.end_date:
                if date >= datetime.strptime(certificate.start_date, '%Y-%m-%d'):
                    vat_exemption = certificate
                    break
            elif date <= datetime.strptime(certificate.end_date, '%Y-%m-%d') and date >= datetime.strptime(
                    certificate.start_date, '%Y-%m-%d'):
                vat_exemption = certificate
                break
        return vat_exemption
