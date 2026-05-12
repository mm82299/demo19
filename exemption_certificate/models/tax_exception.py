# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

#
# class SaleOrder(models.Model):
#     _inherit = 'sale.order'
#
#     tax_exception_certif = fields.Binary(related='partner_id.exemption_certificate_ids.certificate', string="Attestation de dérogation fiscale" , attachment=True)
#     file_name = fields.Char("file name",related='partner_id.exemption_certificate_ids.file_name', size=64)
#
#
# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'
#
#     tax_exception_certif = fields.Binary(related='partner_id.exemption_certificate_ids.certificate', string="Attestation de dérogation fiscale")
#     file_name = fields.Char("file name", related='partner_id.exemption_certificate_ids.file_name', size=64)
#

class AccountMove(models.Model):
    _inherit = 'account.move'

    tax_exception_certif = fields.Binary(related='partner_id.exemption_certificate_ids.certificate', string="Attestation de dérogation fiscale")
    file_name = fields.Char("file name", related='partner_id.exemption_certificate_ids.file_name', size=64)