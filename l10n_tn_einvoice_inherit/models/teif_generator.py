# -*- coding: utf-8 -*-
from odoo import api, fields, models
from lxml import etree
from odoo.exceptions import UserError



class TeifGenerator(models.AbstractModel):

    _inherit = 'teif.generator'

    def _add_invoice_header(self, root, invoice):
        """Add InvoiceHeader section"""
        header = etree.SubElement(root, 'InvoiceHeader')

        # Sender (Company)
        sender_id = etree.SubElement(header, 'MessageSenderIdentifier', type='I-01')
        if invoice.company_id.ttn_vat_number_type == 'vat13':
            sender_id.text = invoice.company_id.get_tn_fiscal_id()
        elif invoice.company_id.ttn_vat_number_type == 'vat8':
            sender_id.text = invoice.company_id.get_tn_fiscal_id()[:8]
        else:
            sender_id.text = invoice.company_id.get_tn_fiscal_id()

        # Receiver (Customer)
        receiver_type = invoice.partner_id.tn_fiscal_id_type or 'I-01'
        receiver_id = etree.SubElement(header, 'MessageRecieverIdentifier', type=receiver_type)
        receiver_id.text = invoice.partner_id.get_tn_fiscal_id()

    def _validate_invoice_for_teif(self, invoice):
        super()._validate_invoice_for_teif(invoice)
        if invoice.public_company and not invoice.teif_description:
            raise UserError('Veuillez saisir la description TEIF avant de générer le fichier pour un établissement public.')

    def _add_line_section(self, body, invoice):
        if invoice.public_company:
            lin_section = etree.SubElement(body, 'LinSection')
            lin = etree.SubElement(lin_section, 'Lin')
            
            item_id = etree.SubElement(lin, 'ItemIdentifier')
            item_id.text = '1'
            
            imd = etree.SubElement(lin, 'LinImd', lang='fr')
            item_code = etree.SubElement(imd, 'ItemCode')
            item_code.text = '1'
            item_desc = etree.SubElement(imd, 'ItemDescription')
            item_desc.text = (invoice.teif_description or '')[:500]
            
            qty = etree.SubElement(lin, 'LinQty')
            quantity = etree.SubElement(qty, 'Quantity', measurementUnit='UNIT')
            quantity.text = '1.000'
            
            if invoice.invoice_date:
                dtm = etree.SubElement(lin, 'LinDtm')
                date_text = etree.SubElement(dtm, 'DateText', functionCode='I-31', format='ddMMyy')
                date_text.text = invoice.invoice_date.strftime('%d%m%y')
                
            tax_line = etree.SubElement(lin, 'LinTax')
            tax_name = etree.SubElement(tax_line, 'TaxTypeName', code='I-1602')
            tax_name.text = 'TVA'
            tax_details = etree.SubElement(tax_line, 'TaxDetails')
            tax_rate = etree.SubElement(tax_details, 'TaxRate')
            tax_rate.text = '19.00'
            
            total_ht = invoice.amount_total / 1.19
            
            moa = etree.SubElement(lin, 'LinMoa')
            moa_details_unit = etree.SubElement(moa, 'MoaDetails')
            moa_unit = etree.SubElement(moa_details_unit, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-183')
            amt_unit = etree.SubElement(moa_unit, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt_unit.text = f"{total_ht:.3f}"
            
            moa_details_total = etree.SubElement(moa, 'MoaDetails')
            moa_total = etree.SubElement(moa_details_total, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-171')
            amt_total = etree.SubElement(moa_total, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt_total.text = f"{total_ht:.3f}"
        else:
            super()._add_line_section(body, invoice)

    def _add_invoice_moa_section(self, body, invoice):
        if invoice.public_company:
            total_ht = invoice.amount_total / 1.19
            total_tax = invoice.amount_total - total_ht
            
            inv_moa = etree.SubElement(body, 'InvoiceMoa')
            
            amt_details_gross = etree.SubElement(inv_moa, 'AmountDetails')
            moa_gross = etree.SubElement(amt_details_gross, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-179')
            amt_gross = etree.SubElement(moa_gross, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt_gross.text = f"{invoice.company_id.capital:.3f}"
            
            amt_details_ht = etree.SubElement(inv_moa, 'AmountDetails')
            moa_ht = etree.SubElement(amt_details_ht, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-176')
            amt_ht = etree.SubElement(moa_ht, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt_ht.text = f"{total_ht:.3f}"
            
            amt_details_tax = etree.SubElement(inv_moa, 'AmountDetails')
            moa_tax = etree.SubElement(amt_details_tax, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-181')
            amt_tax = etree.SubElement(moa_tax, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt_tax.text = f"{total_tax:.3f}"
            
            amt_details_ttc = etree.SubElement(inv_moa, 'AmountDetails')
            moa_ttc = etree.SubElement(amt_details_ttc, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-180')
            amt_ttc = etree.SubElement(moa_ttc, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt_ttc.text = f"{invoice.amount_total:.3f}"
            
            amt_desc = etree.SubElement(moa_ttc, 'AmountDescription', lang='fr')
            amt_desc.text = self._amount_to_words(invoice.amount_total, invoice.currency_id.name)
        else:
            super()._add_invoice_moa_section(body, invoice)

    def _add_invoice_tax_section(self, body, invoice):
        if invoice.public_company:
            total_ht = invoice.amount_total / 1.19
            total_tax = invoice.amount_total - total_ht
            
            inv_tax = etree.SubElement(body, 'InvoiceTax')
            tax_details = etree.SubElement(inv_tax, 'InvoiceTaxDetails')
            
            tax_elem = etree.SubElement(tax_details, 'Tax')
            tax_name = etree.SubElement(tax_elem, 'TaxTypeName', code='I-1602')
            tax_name.text = 'TVA'
            
            tax_det = etree.SubElement(tax_elem, 'TaxDetails')
            rate = etree.SubElement(tax_det, 'TaxRate')
            rate.text = '19.00'
            
            amt_details = etree.SubElement(tax_details, 'AmountDetails')
            moa = etree.SubElement(amt_details, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-177')
            amt = etree.SubElement(moa, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt.text = f"{total_ht:.3f}"
            
            amt_details_tax = etree.SubElement(tax_details, 'AmountDetails')
            moa_tax = etree.SubElement(amt_details_tax, 'Moa', currencyCodeList='ISO_4217', amountTypeCode='I-178')
            amt_tax = etree.SubElement(moa_tax, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amt_tax.text = f"{total_tax:.3f}"
        else:
            super()._add_invoice_tax_section(body, invoice)

