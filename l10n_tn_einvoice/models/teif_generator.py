# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
from datetime import datetime
from lxml import etree
import logging
from calendar import monthrange

_logger = logging.getLogger(__name__)


class TeifGenerator(models.AbstractModel):
    _name = 'teif.generator'
    _description = 'TEIF XML Generator v1.8.8'

    @api.model
    def generate_teif_xml(self, invoice):
        """
        Generate TEIF v1.8.8 XML from invoice
        According to Tunisian Electronic Invoice Format specifications
        """

        # Validate invoice before generation
        self._validate_invoice_for_teif(invoice)

        # Create root element with namespaces
        root = self._create_root_element()

        # Build XML structure
        self._add_invoice_header(root, invoice)
        body = self._add_invoice_body(root)
        self._add_bgm_section(body, invoice)
        self._add_dtm_section(body, invoice)
        self._add_partner_section(body, invoice)
        self._add_location_section(body, invoice)
        self._add_payment_section(body, invoice)
        self._add_free_text_section(body, invoice)
        self._add_special_conditions(body, invoice)
        self._add_line_section(body, invoice)
        self._add_invoice_moa_section(body, invoice)
        self._add_invoice_tax_section(body, invoice)
        self._add_invoice_alc_section(body, invoice)

        # Format and return XML
        xml_string = etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        ).decode('utf-8')

        _logger.info("TEIF XML generated successfully for invoice %s", invoice.name)
        return xml_string

    def _validate_invoice_for_teif(self, invoice):
        """Validate invoice data before TEIF generation"""
        errors = []

        # Company validation
        company_fiscal_id = invoice.company_id.get_tn_fiscal_id()
        print('company_fiscal_id', company_fiscal_id)
        if not company_fiscal_id:
            errors.append(_("Le matricule fiscal de la société est requis (champ NIF/TVA)"))

        if not invoice.company_id.country_id or invoice.company_id.country_id.code != 'TN':
            errors.append(_("Le pays de la société doit être Tunisie"))

        # Partner validation
        partner_fiscal_id = invoice.partner_id.get_tn_fiscal_id()
        if not partner_fiscal_id:
            errors.append(_("Le matricule fiscal du client est requis (champ NIF/TVA)"))

        if not invoice.partner_id.tn_fiscal_id_type:
            errors.append(_("Le type d'identifiant fiscal du client est requis"))

        # Invoice validation
        if not invoice.invoice_line_ids:
            errors.append(_("La facture doit contenir au moins une ligne"))

        if invoice.amount_total <= 0:
            errors.append(_("Le montant total doit être supérieur à 0"))

        # Tax validation
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type in ('product', 'epd', 'discount')):
            if not line.tax_ids:
                errors.append(_("La ligne '%s' doit avoir au moins une taxe configurée") % line.name)

        if errors:
            raise UserError("\n".join(errors))

    def _create_root_element(self):
        """Create TEIF root element with proper namespaces"""
        nsmap = {
            None: 'http://www.tunisietradenet.tn/TEIF',  # Default namespace
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',  # xsi namespace
            'ds': 'http://www.w3.org/2000/09/xmldsig#'
        }
        attrib = {
        }
        root = etree.Element(
            'TEIF',
            controlingAgency='TTN',
            version='1.8.9'
        )

        return root

    def _add_invoice_header(self, root, invoice):
        """Add InvoiceHeader section"""
        header = etree.SubElement(root, 'InvoiceHeader')

        # Sender (Company)
        sender_id = etree.SubElement(header, 'MessageSenderIdentifier', type='I-01')
        sender_id.text = invoice.company_id.get_tn_fiscal_id()[:8]

        # Receiver (Customer)
        receiver_type = invoice.partner_id.tn_fiscal_id_type or 'I-01'
        receiver_id = etree.SubElement(header, 'MessageRecieverIdentifier', type=receiver_type)
        receiver_id.text = invoice.partner_id.get_tn_fiscal_id()

    def _add_invoice_body(self, root):
        """Add InvoiceBody section"""
        return etree.SubElement(root, 'InvoiceBody')

    def _add_bgm_section(self, body, invoice):
        """Add BGM (Beginning of Message) section"""
        bgm = etree.SubElement(body, 'Bgm')

        # Document Identifier (Invoice Number)
        doc_id = etree.SubElement(bgm, 'DocumentIdentifier')
        doc_id.text = invoice._get_ttn_invoice_name()

        # Document Type
        doc_code = invoice.teif_document_type or ('I-11' if invoice.move_type == 'out_invoice' else 'I-12')
        doc_type = etree.SubElement(bgm, 'DocumentType', code=doc_code)
        doc_type.text = self._get_document_type_name(doc_code)

        # Document References (for credit notes)
        if invoice.move_type == 'out_refund' and invoice.reversed_entry_id:
            doc_refs = etree.SubElement(bgm, 'DocumentReferences')
            doc_ref = etree.SubElement(doc_refs, 'DocumentReference')
            ref = etree.SubElement(doc_ref, 'Reference', refID='I-817')
            ref.text = invoice.reversed_entry_id.name

    def _get_document_type_name(self, code):
        """Get document type name from code"""
        doc_types = {
            'I-11': 'Facture',
            'I-12': 'Avoir',
            'I-13': 'Note d’honoraire',
            'I-14': 'Décompte (marché public)',
            'I-15': 'Facture Export',
            'I-16': 'Bon de commande',
        }
        return doc_types.get(code, 'Facture')

    def _add_dtm_section(self, body, invoice):
        """Add DTM (Date/Time) section"""
        dtm = etree.SubElement(body, 'Dtm')

        # Invoice Date (I-31)
        invoice_date = etree.SubElement(dtm, 'DateText',
                                        functionCode='I-31',
                                        format='ddMMyy')
        invoice_date.text = invoice.invoice_date.strftime('%d%m%y')

        first_day = invoice.invoice_date.replace(day=1)
        last_day_num = monthrange(invoice.invoice_date.year, invoice.invoice_date.month)[1]
        last_day = invoice.invoice_date.replace(day=last_day_num)

        period_date = etree.SubElement(dtm, 'DateText',
                                       functionCode='I-36',
                                       format='ddMMyy-ddMMyy')
        period_date.text = f"{first_day.strftime('%d%m%y')}-{last_day.strftime('%d%m%y')}"

        # Due Date (I-32)
        if invoice.invoice_date_due:
            due_date = etree.SubElement(dtm, 'DateText',
                                        functionCode='I-32',
                                        format='ddMMyy')
            due_date.text = invoice.invoice_date_due.strftime('%d%m%y')

        # Delivery Date (I-35) if available
        if hasattr(invoice, 'delivery_date') and invoice.delivery_date:
            delivery_date = etree.SubElement(dtm, 'DateText',
                                             functionCode='I-35',
                                             format='ddMMyy')
            delivery_date.text = invoice.delivery_date.strftime('%d%m%y')

    def _add_partner_section(self, body, invoice):
        """Add PartnerSection with supplier and customer details"""
        partner_section = etree.SubElement(body, 'PartnerSection')

        # Supplier (I-62 - Fournisseur)
        self._add_partner_details(partner_section, invoice.company_id, 'I-62', is_company=True, invoice=invoice)

        # Customer (I-64 - Client)
        self._add_partner_details(partner_section=partner_section, partner=invoice.partner_id, function_code='I-64', is_company=False, invoice=invoice)

        # Invoice recipient if different (I-63)
        if invoice.partner_shipping_id and invoice.partner_shipping_id != invoice.partner_id:
            self._add_partner_details(partner_section=partner_section, partner=invoice.partner_shipping_id, function_code='I-63', is_company=False, invoice=invoice)

    def _add_partner_details(self, partner_section, partner, function_code, is_company=False, invoice=False):
        """Add detailed partner information"""
        details = etree.SubElement(partner_section, 'PartnerDetails', functionCode=function_code)
        nad = etree.SubElement(details, 'Nad')

        # Partner Identifier
        id_type = 'I-01' if is_company else (partner.tn_fiscal_id_type or 'I-01')
        pid = etree.SubElement(nad, 'PartnerIdentifier', type=id_type)
        pid.text = partner.get_tn_fiscal_id()

        # Partner Name
        if hasattr(partner, 'tn_partner_name_type'):
            name_type = partner.tn_partner_name_type or 'Qualification'
        else:
            name_type = 'Qualification' if (is_company or partner.is_company) else 'Physical'

        pname = etree.SubElement(nad, 'PartnerName', nameType=name_type)
        pname.text = partner.name

        # Partner Address
        if partner.street or partner.city:
            paddress = etree.SubElement(nad, 'PartnerAdresses', lang='fr')

            # Address Description
            addr_desc = etree.SubElement(paddress, 'AdressDescription')
            addr_desc.text = partner.street or ''

            # Street (optional)
            if partner.street2:
                street = etree.SubElement(paddress, 'Street')
                street.text = partner.street2

            # City Name (optional but recommended)
            if partner.city:
                city = etree.SubElement(paddress, 'CityName')
                city.text = partner.city

            # Postal Code (optional)
            if partner.zip:
                postal = etree.SubElement(paddress, 'PostalCode')
                postal.text = partner.zip

            # Country (required)
            country = etree.SubElement(paddress, 'Country', codeList='ISO_3166-1')
            country.text = partner.country_id.code or 'TN'

        # Reference Section (Matricule fiscal, etc.)
        self._add_partner_references(details, partner, is_company, function_code, invoice)

        # Contact Section
        self._add_contact_section(details, partner)

    def _add_partner_references(self, details, partner, is_company, function_code, invoice):
        """Add partner references (fiscal ID, codes)"""
        # Fiscal ID Reference

        if is_company and hasattr(partner, 'company_registry') and partner.company_registry:
            rff_section = etree.SubElement(details, 'RffSection')
            ref = etree.SubElement(rff_section, 'Reference', refID='I-815')
            ref.text = partner.company_registry

        # VAT regime for companies
        if is_company and hasattr(partner, 'company_category') and partner.company_category:
            rff_section = etree.SubElement(details, 'RffSection')
            ref = etree.SubElement(rff_section, 'Reference', refID='I-816')
            ref.text = partner.company_category

        if function_code == 'I-64':

            if partner.get_tn_fiscal_id():
                rff_section = etree.SubElement(details, 'RffSection')
                ref = etree.SubElement(rff_section, 'Reference', refID='I-81')
                ref.text = partner.get_tn_fiscal_id()[:8]

            rff_section = etree.SubElement(details, 'RffSection')
            ref = etree.SubElement(rff_section, 'Reference', refID='I-811')
            ref.text = "SMTP"

            if hasattr(partner, 'industry_id') and partner.industry_id:
                rff_section = etree.SubElement(details, 'RffSection')
                ref = etree.SubElement(rff_section, 'Reference', refID='I-813')
                ref.text = partner.industry_id.name

            rff_section = etree.SubElement(details, 'RffSection')
            ref = etree.SubElement(rff_section, 'Reference', refID='I-812')
            ref.text = "P"

            if hasattr(partner, 'ref') and partner.ref:
                rff_section = etree.SubElement(details, 'RffSection')
                ref = etree.SubElement(rff_section, 'Reference', refID='I-814')
                ref.text = partner.ref


            if hasattr(invoice, 'saleorder_number') and invoice.saleorder_number:
                rff_section = etree.SubElement(details, 'RffSection')
                ref = etree.SubElement(rff_section, 'Reference', refID='I-83')
                ref.text = invoice.saleorder_number
                if hasattr(invoice, 'suspension_number') and invoice.suspension_number:
                    rff_section = etree.SubElement(details, 'RffSection')
                    ref = etree.SubElement(rff_section, 'Reference', refID='I-84')
                    ref.text = invoice.suspension_number

            if hasattr(invoice, 'decompte_number') and invoice.decompte_number:
                rff_section = etree.SubElement(details, 'RffSection')
                ref = etree.SubElement(rff_section, 'Reference', refID='I-86')
                ref.text = invoice.decompte_number

            if hasattr(invoice, 'public_procuerement') and invoice.public_procuerement:
                rff_section = etree.SubElement(details, 'RffSection')
                ref = etree.SubElement(rff_section, 'Reference', refID='I-87')
                ref.text = invoice.public_procuerement

            # if hasattr(invoice, 'public_procuerement_name') and invoice.public_procuerement_name:
            #     rff_section = etree.SubElement(details, 'RffSection')
            #     ref = etree.SubElement(rff_section, 'Reference', refID='I-871')
            #     ref.text = invoice.public_procuerement_name

        # Additional references from partner
    def _add_contact_section(self, details, partner):
        """Add contact information"""
        # Use TEIF contact fields if available, otherwise standard fields
        short_name = getattr(partner, 'company_short_name', None) or partner.name
        contact_person = getattr(partner, 'tn_contact_person', None) or partner.name
        contact_phone = getattr(partner, 'tn_contact_phone', None) or partner.phone
        contact_email = getattr(partner, 'tn_contact_email', None) or partner.email

        if contact_person or contact_phone or contact_email:

            # Phone
            if contact_phone:
                cta_section = etree.SubElement(details, 'CtaSection')
                contact = etree.SubElement(cta_section, 'Contact', functionCode='I-94')

                cid = etree.SubElement(contact, 'ContactIdentifier')
                cid.text = short_name[:17] if short_name else 'N/A'

                cname = etree.SubElement(contact, 'ContactName')
                cname.text = contact_person[:200] if contact_person else 'N/A'
                comm = etree.SubElement(cta_section, 'Communication')
                means = etree.SubElement(comm, 'ComMeansType')
                means.text = 'I-101'  # Telephone
                addr = etree.SubElement(comm, 'ComAdress')
                addr.text = contact_phone[:500]



            # Email
            if contact_email:
                cta_section = etree.SubElement(details, 'CtaSection')
                contact = etree.SubElement(cta_section, 'Contact', functionCode='I-94')

                cid = etree.SubElement(contact, 'ContactIdentifier')
                cid.text = short_name[:17] if short_name else 'N/A'

                cname = etree.SubElement(contact, 'ContactName')
                cname.text = contact_person[:200] if contact_person else 'N/A'
                comm = etree.SubElement(cta_section, 'Communication')
                means = etree.SubElement(comm, 'ComMeansType')
                means.text = 'I-103'  # Email
                addr = etree.SubElement(comm, 'ComAdress')
                addr.text = contact_email[:500]

            # Website
            if partner.website:
                cta_section = etree.SubElement(details, 'CtaSection')
                contact = etree.SubElement(cta_section, 'Contact', functionCode='I-94')

                cid = etree.SubElement(contact, 'ContactIdentifier')
                cid.text = short_name[:17] if short_name else 'N/A'

                cname = etree.SubElement(contact, 'ContactName')
                cname.text = contact_person[:200] if contact_person else 'N/A'
                comm = etree.SubElement(cta_section, 'Communication')
                means = etree.SubElement(comm, 'ComMeansType')
                means.text = 'I-104'  # Website
                addr = etree.SubElement(comm, 'ComAdress')
                addr.text = partner.website[:500]

    def _add_location_section(self, body, invoice):
        """Add LocSection for delivery/service locations"""
        if invoice.partner_shipping_id and invoice.partner_shipping_id != invoice.partner_id:
            loc_section = etree.SubElement(body, 'LocSection')
            loc_details = etree.SubElement(loc_section, 'LocDetails', functionCode='I-57')  # Delivery location

            location_text = invoice.partner_shipping_id.contact_address or invoice.partner_shipping_id.name
            loc_details.text = location_text[:200]

    def _add_payment_section(self, body, invoice):
        """Add PytSection with payment terms and conditions"""
        payment_info = invoice.get_ttn_payment_info()

        if not payment_info['payment_terms_code'] and not invoice.partner_bank_id.acc_number:
            return  # Skip if no payment information

        pyt_section = etree.SubElement(body, 'PytSection')
        pyt_details = etree.SubElement(pyt_section, 'PytSectionDetails')

        # Payment Terms
        if payment_info['payment_terms_code']:
            pyt = etree.SubElement(pyt_details, 'Pyt')
            code = etree.SubElement(pyt, 'PaymentTearmsTypeCode')
            code.text = payment_info['payment_terms_code']

            if payment_info['payment_description']:
                desc = etree.SubElement(pyt, 'PaymentTearmsDescription')
                desc.text = payment_info['payment_description'][:500]

        # Payment Date
        if invoice.invoice_date_due:
            pyt_dtm = etree.SubElement(pyt_details, 'PytDtm')
            date_text = etree.SubElement(pyt_dtm, 'DateText',
                                         functionCode='I-32',
                                         format='ddMMyy')
            date_text.text = invoice.invoice_date_due.strftime('%d%m%y')

        # Payment Amount
        if invoice.amount_residual:
            pyt_moa = etree.SubElement(pyt_details, 'PytMoa',
                                       currencyCodeList='ISO_4217',
                                       amountTypeCode='I-180')
            amount = etree.SubElement(pyt_moa, 'Amount', currencyIdentifier=invoice.currency_id.name)
            amount.text = f"{invoice.amount_residual:.3f}"

        # Payment Instructions
        if payment_info['payment_means_code']:
            pai = etree.SubElement(pyt_details, 'PytPai')
            cond = etree.SubElement(pai, 'PaiConditionCode')
            cond.text = payment_info['payment_condition_code'] or 'I-124'
            means = etree.SubElement(pai, 'PaiMeansCode')
            means.text = payment_info['payment_means_code'] or "I-137"

        # Financial Institution Information
        if invoice.partner_bank_id and payment_info['payment_terms_code'] and payment_info['payment_terms_code'] in ["I-114", "I-111"]:
            fii = etree.SubElement(pyt_details, 'PytFii', functionCode=payment_info['financial_institution_code'] or 'I-141')
            if payment_info['financial_institution_code'] in ("I-141", "I-142"):

                # Account Holder
                acc_holder = etree.SubElement(fii, 'AccountHolder')
                acc_num = etree.SubElement(acc_holder, 'AccountNumber')
                acc_num.text = invoice.partner_bank_id.acc_number[:20]

                owner_id = etree.SubElement(acc_holder, 'OwnerIdentifier')
                owner_id.text = invoice.partner_bank_id.acc_number[7:18]

                # Institution Identification
                if invoice.partner_bank_id.acc_number:
                    inst = etree.SubElement(fii, 'InstitutionIdentification', nameCode=invoice.partner_bank_id.acc_number[:5])

                    if invoice.partner_bank_id:
                        branch = etree.SubElement(inst, 'BranchIdentifier')
                        branch.text = invoice.partner_bank_id.acc_number[:5]

                    inst_name = etree.SubElement(inst, 'InstitutionName')
                    inst_name.text = invoice.partner_bank_id.bank_id.name[:70]

            # Country
            country = etree.SubElement(fii, 'Country', codeList='ISO_3166-1')
            country.text = invoice.company_id.country_id.code or 'TN'

    def _add_free_text_section(self, body, invoice):
        """Add Ftx (Free Text) section for additional information"""
        texts_to_add = []

        # Narration/Comment
        if invoice.narration:
            texts_to_add.append(('I-41', invoice.narration))  # General information

        # Payment reference
        if invoice.payment_reference:
            texts_to_add.append(('I-42', invoice.payment_reference))  # Payment instructions

        # Invoice origin
        if invoice.invoice_origin:
            texts_to_add.append(('I-43', f"Origine: {invoice.invoice_origin}"))

        if texts_to_add:
            ftx = etree.SubElement(body, 'Ftx')

            for subject_code, text in texts_to_add:
                ftx_detail = etree.SubElement(ftx, 'FreeTextDetail', subjectCode=subject_code)
                free_text = etree.SubElement(ftx_detail, 'FreeTexts')
                free_text.text = text[:500]

    def _add_special_conditions(self, body, invoice):
        """Add SpecialConditions section"""
        if invoice.teif_special_conditions:
            special = etree.SubElement(body, 'SpecialConditions')

            # Split by lines if multiple conditions
            conditions = invoice.teif_special_conditions.split('\n')
            for condition in conditions[:10]:  # Max 10 conditions
                if condition.strip():
                    cond = etree.SubElement(special, 'SpecialCondition')
                    cond.text = condition.strip()[:200]

    def _add_line_section(self, body, invoice):
        """Add LinSection with all invoice lines"""
        lin_section = etree.SubElement(body, 'LinSection')

        line_number = 1
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type in ('product', 'epd', 'discount')):
            self._add_line_item(lin_section, line, line_number, invoice)
            line_number += 1

    def _add_line_item(self, lin_section, line, line_number, invoice):
        """Add individual line item"""
        lin = etree.SubElement(lin_section, 'Lin')
        # Item Identifier (Line Number)
        item_id = etree.SubElement(lin, 'ItemIdentifier')
        item_id.text = str(line_number)

        # Item Description (LinImd)
        imd = etree.SubElement(lin, 'LinImd', lang='fr')
        item_code = etree.SubElement(imd, 'ItemCode')
        item_code.text = line.product_id.default_code or str(line_number)

        item_desc = etree.SubElement(imd, 'ItemDescription')
        if invoice.company_id.use_custom_product_description:
            template = invoice.company_id.custom_product_description_template or ""
            custom_text = template.replace("{product_name}", line.product_id.name or "").replace("{description}", line.name or "")
            item_desc.text = custom_text[:500]
        else:
            item_desc.text = (line.name or line.product_id.name)[:500]

        # Additional Product Information (LinApi) - optional
        if line.product_id and line.product_id.barcode:
            api_section = etree.SubElement(lin, 'LinApi')
            api_details = etree.SubElement(api_section, 'ApiDetails', lang='fr')
            api_code = etree.SubElement(api_details, 'ApiCode')
            api_code.text = line.product_id.barcode[:50]
            api_desc = etree.SubElement(api_details, 'ApiDescription')
            api_desc.text = 'Code-barres'[:500]

        # Quantity (LinQty)
        qty = etree.SubElement(lin, 'LinQty')
        quantity = etree.SubElement(qty, 'Quantity', measurementUnit='UNIT')
        quantity.text = f"{line.quantity:.3f}"

        # Date (LinDtm) - optional
        if invoice.invoice_date:
            dtm = etree.SubElement(lin, 'LinDtm')
            date_text = etree.SubElement(dtm, 'DateText',
                                         functionCode='I-31',
                                         format='ddMMyy')
            date_text.text = invoice.invoice_date.strftime('%d%m%y')

        # Tax (LinTax)
        self._add_line_tax(lin, line)

        # Allowances/Charges (LinAlc) - if discount
        if line.discount > 0:
            self._add_line_allowance(lin, line)

        # Monetary Amounts (LinMoa)
        self._add_line_monetary_amounts(lin, line, invoice)

        # Free Text (LinFtx) - optional
        if line.name and len(line.name) > 500:
            ftx = etree.SubElement(lin, 'LinFtx')
            ftx_detail = etree.SubElement(ftx, 'FreeTextDetail', subjectCode='I-41')
            free_text = etree.SubElement(ftx_detail, 'FreeTexts')
            free_text.text = line.name[500:1000]

    def _add_line_tax(self, lin, line):
        """Add tax information to line"""
        # Filter taxes to keep only the main tax (exclude taxes included in base amount like Fodec)
        # because TTN does not accept multiple taxes in one line
        taxes = line.tax_ids.filtered(lambda t: not t.include_base_amount)
        if taxes:
            rec = taxes[0]

            tax_line = etree.SubElement(lin, 'LinTax')

            # Tax Type Name with TTN code
            tax_code = rec.ttn_code or 'I-1602'  # Default to TVA
            tax_name_text = rec.get_ttn_tax_name()

            tax_name = etree.SubElement(tax_line, 'TaxTypeName', code=tax_code)
            tax_name.text = tax_name_text

            # Tax Category (optional)
            if rec.ttn_tax_category:
                tax_cat = etree.SubElement(tax_line, 'TaxCategory')
                tax_cat.text = rec.ttn_tax_category

            # Tax Details
            tax_details = etree.SubElement(tax_line, 'TaxDetails')
            tax_rate = etree.SubElement(tax_details, 'TaxRate')

            if rec.amount_type == 'percent':
                tax_rate.text = f"{rec.amount:.2f}"
            elif rec.amount_type == 'fixed':
                amount = rec.amount * line.quantity
                tax_rate.text = f"{amount:.2f}"
            else:
                tax_rate.text = "0.00"

    def _add_line_allowance(self, lin, line):
        """Add allowance/discount to line"""
        lin_alc = etree.SubElement(lin, 'LinAlc')

        # Allowance
        alc = etree.SubElement(lin_alc, 'Alc', allowanceCode='I-151')  # Discount

        alc_id = etree.SubElement(alc, 'AllowanceIdentifier')
        alc_id.text = f"DISC-{line.id}"

        special_service = etree.SubElement(alc, 'SpecialServices', lang='fr')
        special_service.text = f"Remise {line.discount}%"

        # Percentage
        pcd = etree.SubElement(lin_alc, 'Pcd')
        percentage = etree.SubElement(pcd, 'Percentage')
        percentage.text = f"{line.discount:.2f}"

        percentage_basis = etree.SubElement(pcd, 'PercentageBasis')
        percentage_basis.text = "Montant HT"

    def _add_line_monetary_amounts(self, lin, line, invoice):
        """Add monetary amounts to line"""
        moa = etree.SubElement(lin, 'LinMoa')

        # Unit Price (I-183)
        moa_details_unit = etree.SubElement(moa, 'MoaDetails')
        moa_unit = etree.SubElement(moa_details_unit, 'Moa',
                                    currencyCodeList='ISO_4217',
                                    amountTypeCode='I-183')
        amt_unit = etree.SubElement(moa_unit, 'Amount',
                                    currencyIdentifier=invoice.currency_id.name)
        amt_unit.text = f"{line.price_unit:.3f}"

        # Line Total HT (I-171)
        moa_details_total = etree.SubElement(moa, 'MoaDetails')
        moa_total = etree.SubElement(moa_details_total, 'Moa',
                                     currencyCodeList='ISO_4217',
                                     amountTypeCode='I-171')
        amt_total = etree.SubElement(moa_total, 'Amount',
                                     currencyIdentifier=invoice.currency_id.name)
        amt_total.text = f"{line.price_subtotal:.3f}"

    def _add_invoice_moa_section(self, body, invoice):
        """Add InvoiceMoa with total amounts"""
        inv_moa = etree.SubElement(body, 'InvoiceMoa')

        # Total HT avant remise (I-179)
        amt_details_gross = etree.SubElement(inv_moa, 'AmountDetails')
        moa_gross = etree.SubElement(amt_details_gross, 'Moa',
                                     currencyCodeList='ISO_4217',
                                     amountTypeCode='I-179')
        amt_gross = etree.SubElement(moa_gross, 'Amount',
                                     currencyIdentifier=invoice.currency_id.name)
        amt_gross.text = f"{invoice.company_id.capital:.3f}"

        # Total HT (I-176)
        amt_details_ht = etree.SubElement(inv_moa, 'AmountDetails')
        moa_ht = etree.SubElement(amt_details_ht, 'Moa',
                                  currencyCodeList='ISO_4217',
                                  amountTypeCode='I-176')
        amt_ht = etree.SubElement(moa_ht, 'Amount',
                                  currencyIdentifier=invoice.currency_id.name)
        amt_ht.text = f"{invoice.amount_untaxed:.3f}"

        # Total Tax (I-181)
        amt_details_tax = etree.SubElement(inv_moa, 'AmountDetails')
        moa_tax = etree.SubElement(amt_details_tax, 'Moa',
                                   currencyCodeList='ISO_4217',
                                   amountTypeCode='I-181')
        amt_tax = etree.SubElement(moa_tax, 'Amount',
                                   currencyIdentifier=invoice.currency_id.name)
        amt_tax.text = f"{invoice.amount_tax:.3f}"

        # Total TTC (I-180)
        amt_details_ttc = etree.SubElement(inv_moa, 'AmountDetails')
        moa_ttc = etree.SubElement(amt_details_ttc, 'Moa',
                                   currencyCodeList='ISO_4217',
                                   amountTypeCode='I-180')
        amt_ttc = etree.SubElement(moa_ttc, 'Amount',
                                   currencyIdentifier=invoice.currency_id.name)
        amt_ttc.text = f"{invoice.amount_total:.3f}"

        # Amount in letters
        amt_desc = etree.SubElement(moa_ttc, 'AmountDescription', lang='fr')
        amt_desc.text = self._amount_to_words(invoice.amount_total, invoice.currency_id.name)

    def _add_invoice_tax_section(self, body, invoice):
        """Add InvoiceTax with tax details grouped by tax"""
        inv_tax = etree.SubElement(body, 'InvoiceTax')

        # Group taxes
        tax_data = self._compute_tax_totals(invoice)
        print('Tax Data', tax_data)
        for tax_info in tax_data:
            tax_details = etree.SubElement(inv_tax, 'InvoiceTaxDetails')

            # Tax information
            tax_elem = etree.SubElement(tax_details, 'Tax')

            tax_code = tax_info['tax'].ttn_code or 'I-1602'
            tax_name_text = tax_info['tax'].get_ttn_tax_name()

            tax_name = etree.SubElement(tax_elem, 'TaxTypeName', code=tax_code)
            tax_name.text = tax_name_text

            if tax_info['tax'].ttn_tax_category:
                tax_cat = etree.SubElement(tax_elem, 'TaxCategory')
                tax_cat.text = tax_info['tax'].ttn_tax_category

            tax_det = etree.SubElement(tax_elem, 'TaxDetails')
            rate = etree.SubElement(tax_det, 'TaxRate')
            rate.text = f"{tax_info['rate']:.2f}"

            # Tax Base Amount (I-177)
            if tax_info['base'] > 0.0:
                amt_details = etree.SubElement(tax_details, 'AmountDetails')
                moa = etree.SubElement(amt_details, 'Moa',
                                       currencyCodeList='ISO_4217',
                                       amountTypeCode='I-177')
                amt = etree.SubElement(moa, 'Amount',
                                       currencyIdentifier=invoice.currency_id.name)
                amt.text = f"{tax_info['base']:.3f}"

            # Tax Amount (I-178)
            amt_details_tax = etree.SubElement(tax_details, 'AmountDetails')
            moa_tax = etree.SubElement(amt_details_tax, 'Moa',
                                       currencyCodeList='ISO_4217',
                                       amountTypeCode='I-178')
            amt_tax = etree.SubElement(moa_tax, 'Amount',
                                       currencyIdentifier=invoice.currency_id.name)
            amt_tax.text = f"{tax_info['amount']:.3f}"

    def _compute_tax_totals(self, invoice):
        """Compute tax totals grouped by tax"""
        tax_groups = {}
        # From tax lines
        if not invoice.line_ids.filtered(lambda l: l.tax_line_id):
            tax = self.env['account.tax'].sudo().search([('amount', '=', 0.0), ('amount_type', '=', 'percent'), ('type_tax_use', '=', 'sale')], limit=1)
            tax_groups[tax.id] = {
                'tax': tax,
                'base': 0.0,
                'amount': 0.0,
                'rate': tax.amount if tax.amount_type == 'percent' else 0.0
            }
        for line in invoice.line_ids.filtered(lambda l: l.tax_line_id):
            tax = line.tax_line_id

            if tax.id not in tax_groups:
                tax_groups[tax.id] = {
                    'tax': tax,
                    'base': 0.0,
                    'amount': 0.0,
                    'rate': tax.amount if tax.amount_type == 'percent' else 0.0
                }
            tax_groups[tax.id]['amount'] += abs(line.balance)

        # Compute base for each tax
        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type in ('product', 'epd', 'discount')):
            for tax in line.tax_ids:
                if tax.id in tax_groups:
                    tax_groups[tax.id]['base'] += line.price_subtotal
        return list(tax_groups.values())

    def _add_invoice_alc_section(self, body, invoice):
        """Add InvoiceAlc for global allowances/charges"""
        # Only add if there are global discounts or charges
        # This is optional and depends on your invoice configuration
        pass

    def _amount_to_words(self, amount, currency='TND'):
        """Convert amount to words in French"""
        try:
            from num2words import num2words

            if currency == 'TND':
                dinars = int(amount)
                millimes = int((amount - dinars) * 1000)

                words = num2words(dinars, lang='fr').upper()
                words += " DINARS"
                if millimes > 0:
                    words += " ET " + num2words(millimes, lang='fr').upper() + " MILLIMES"
                return words
            elif currency == 'EUR':
                euros = int(amount)
                cents = int((amount - euros) * 100)
                words = num2words(euros, lang='fr').upper() + " EUROS"
                if cents > 0:
                    words += " ET " + num2words(cents, lang='fr').upper() + " CENTIMES"
                return words
            else:
                return f"{amount:.3f} {currency}"
        except ImportError:
            # Fallback if num2words not installed
            return f"{amount:.3f} {currency}"
        except Exception as e:
            _logger.warning("Error converting amount to words: %s", str(e))
            return f"{amount:.3f} {currency}"
