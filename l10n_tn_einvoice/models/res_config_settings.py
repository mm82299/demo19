# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_short_name = fields.Char(related='company_id.company_short_name', readonly=False)

    # Fiscal Information
    tn_fiscal_id_type = fields.Selection(related='company_id.tn_fiscal_id_type', readonly=False)
    tn_vat_regime = fields.Selection(related='company_id.tn_vat_regime', readonly=False)

    # Bank Information
    tn_bank_account_number = fields.Char(related='company_id.tn_bank_account_number', readonly=False)
    tn_bank_name = fields.Char(related='company_id.tn_bank_name', readonly=False)
    tn_bank_branch_code = fields.Char(related='company_id.tn_bank_branch_code', readonly=False)
    capital = fields.Float(related='company_id.capital', readonly=False)

    # ANCE API Configuration
    ngsign_api_url = fields.Char(related='company_id.ngsign_api_url', readonly=False)
    ngsign_api_token = fields.Char(related='company_id.ngsign_api_token', readonly=False)
    ngsign_seal_passphrase = fields.Char(related='company_id.ngsign_seal_passphrase', readonly=False)
    ngsign_use_seal = fields.Boolean(related='company_id.ngsign_use_seal', readonly=False)

    # TTN SOAP API Configuration
    ttn_soap_url = fields.Char(related='company_id.ttn_soap_url', readonly=False)
    ttn_soap_username = fields.Char(related='company_id.ttn_soap_username', readonly=False)
    ttn_soap_password = fields.Char(related='company_id.ttn_soap_password', readonly=False)
    ttn_soap_timeout = fields.Integer(related='company_id.ttn_soap_timeout', readonly=False)
    ttn_auto_submit = fields.Boolean(related='company_id.ttn_auto_submit', readonly=False)

    # QR Code Configuration
    teif_qr_position_x = fields.Integer(related='company_id.teif_qr_position_x', readonly=False)
    teif_qr_position_y = fields.Integer(related='company_id.teif_qr_position_y', readonly=False)
    teif_qr_position_page = fields.Integer(related='company_id.teif_qr_position_page', readonly=False)
    teif_label_position_x = fields.Integer(related='company_id.teif_label_position_x', readonly=False)
    teif_label_position_y = fields.Integer(related='company_id.teif_label_position_y', readonly=False)
    teif_label_position_page = fields.Integer(related='company_id.teif_label_position_page', readonly=False)
    company_category = fields.Selection(related='company_id.company_category', readonly=False)
    honoraire_use = fields.Boolean(related='company_id.honoraire_use', readonly=False)
    require_einvoice = fields.Boolean(related='company_id.require_einvoice', readonly=False)
    use_custom_product_description = fields.Boolean(related='company_id.use_custom_product_description', readonly=False)
    custom_product_description_template = fields.Text(related='company_id.custom_product_description_template', readonly=False)