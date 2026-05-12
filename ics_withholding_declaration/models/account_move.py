
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
import calendar
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom import minidom
import os
import base64
from io import BytesIO
import re
import html
import math


class AccountMove(models.Model):
    _inherit = 'account.move'

    declaration_file = fields.Binary(string='Declaration File', attachment=True, readonly=True, copy=False)
    declaration_file_name = fields.Char(string='Declaration File Name', readonly=True, copy=False)

    def get_company_matricule_fiscale(self):
        for rec in self:
            if rec.company_id.vat:
                cleaned_tax_id = str(rec.company_id.vat).replace('/', '').replace(' ', '')
                nmf = cleaned_tax_id[:8]
                return nmf
            else:
                raise UserError(_('Please enter the VAT number in the company form'))

    def get_ligne_type_identifiant(self, line):
        type_map = {
            'vat': '1',
            'cin': '2',
            'passport': '3',
            'residence': '4',
            'other': '5'
        }

        code = type_map.get(line.tax_id_type)
        if code:
            return code
        else:
            raise UserError(_('Please enter the Tax ID Type'))

    def get_ligne_identifiant(self, line):
        # Clean tax_id by removing '/' and spaces
        if not line.vat:
            raise UserError(_('Please Provide Vendor VAT !!!'))
        cleaned_tax_id = line.vat.replace('/', '').replace(' ', '')

        if line.tax_id_type == 'vat':
            if len(cleaned_tax_id) == 8:
                return cleaned_tax_id
            elif len(cleaned_tax_id) == 13:
                return cleaned_tax_id[:8]
            else:
                raise UserError(_('VAT Tax ID must be either 8 or 13 characters long'))
        elif line.tax_id_type in ['cin', 'passport', 'residence']:
            return cleaned_tax_id
        else:
            raise UserError(_('Please enter the Tax ID'))

    def generate_data_for_xml(self):
        for rec in self :
            certif_list = []

            date_val = rec.withholding_id.date
            year = date_val.year
            month = date_val.month

            declaration_data = {
                'typeidentifiant': '1',
                'identifiant': rec.get_company_matricule_fiscale(),
                'categorie_contribuable' : "PM",
                'acte_depot': 0,
                'annee_depot' : str(year),
                'mois_depot' : f"{int(month):02d}",
            }

            def floor_to3_decimals(number):
                return math.floor(float(number) * 1000) / 1000

            operation_lines = []
            if rec.withholding_id and rec.withholding_id.account_invoice_ids:
                for inv in rec.withholding_id.account_invoice_ids:
                    if inv.invoice_line_ids:
                        for invoice_line_id in inv.invoice_line_ids:
                            tax_id =  invoice_line_id.tax_ids.filtered(lambda l: l.include_base_amount == False and l.amount_type == 'percent')
                            amount_ht = floor_to3_decimals((invoice_line_id.price_total / (1 + (
                                        int(tax_id.amount) / 100)))) if invoice_line_id.price_total and tax_id else invoice_line_id.price_total
                            tva_rate = int(tax_id.amount) if tax_id else 0.0
                            rs_rate = inv.withholding_id.account_withholding_tax_ids.rate
                            amount_tva = (amount_ht * tva_rate) / 100
                            tva_amount = floor_to3_decimals(amount_tva)
                            ttc_amount = amount_ht + tva_amount
                            amount_ttc = floor_to3_decimals(ttc_amount)
                            rs_amount = (amount_ttc * rs_rate) / 100
                            amount_rs = floor_to3_decimals(rs_amount)
                            net_servi_amount = amount_ttc - amount_rs
                            amount_net_servi = floor_to3_decimals(net_servi_amount)
                            devise_code = invoice_line_id.currency_id.name if inv.company_id.currency_id.id != inv.currency_id.id else ''
                            devise_rate = invoice_line_id.currency_id._get_conversion_rate(self, inv.company_id.currency_id,
                                                                                           inv.company_id,
                                                                                           inv.invoice_date) if inv.company_id.currency_id.id != inv.currency_id.id else 0
                            devise_rs = rec.withholding_id.retenue_amount if inv.company_id.currency_id.id != inv.currency_id.id else 0
                            devise_ttc = invoice_line_id.price_subtotal if inv.company_id.currency_id.id != inv.currency_id.id else 0
                            devise_servi = invoice_line_id.price_subtotal - inv.withholding_id.retenue_amount if inv.company_id.currency_id.id != inv.currency_id.id else 0


                            operation_line = {
                                'name': inv.name if inv.name else '',
                                'company_id': self.company_id.id,
                                'declaration_line_id': invoice_line_id.id,
                                'invoice_date': inv.invoice_date if inv.invoice_date else False,
                                'cnpc': False,
                                'p_charge': False,
                                'amount_ht': floor_to3_decimals(amount_ht),
                                'rs_rate': rs_rate,
                                'tva_rate': tva_rate,
                                'tva_amount': floor_to3_decimals(tva_amount),
                                'amount_ttc': floor_to3_decimals(amount_ttc),
                                'amount_rs': floor_to3_decimals(amount_rs),
                                'taxe_additionnelle_code': False,
                                'taxe_additionnelle_rate': 0,
                                'amount_net_servi': floor_to3_decimals(amount_net_servi),
                                'devise_code': devise_code,
                                'devise_rate': floor_to3_decimals(devise_rate),
                                'devise_rs': floor_to3_decimals(devise_rs),
                                'devise_ttc': floor_to3_decimals(devise_ttc),
                                'devise_servi': floor_to3_decimals(devise_servi),
                            }
                            operation_lines.append(operation_line)
                line = {
                    'name': rec.name if rec.name else '',
                    'company_id': self.company_id.id,
                    'birth_date': False,
                    'withholding_id': rec.withholding_id.id,
                    'payment_date': rec.withholding_id.date,
                    'partner_id': rec.partner_id.id if rec.partner_id else False,
                    'country_id': rec.partner_id.country_id.id if rec.partner_id and rec.partner_id.country_id else False,
                    'operation_type_category': rec.partner_id.operation_type_category.id if rec.partner_id and rec.partner_id.operation_type_category else False,
                    'operation_type': rec.partner_id.operation_type.id if rec.partner_id and rec.partner_id.operation_type else False,
                    'tax_id_type': rec.partner_id.tax_id_type if rec.partner_id and rec.partner_id.tax_id_type else False,
                    'category_type': rec.partner_id.category_type if rec.partner_id and rec.partner_id.category_type else False,
                    'partner_tunisian': True if rec.partner_id and rec.partner_id.country_id and rec.partner_id.country_id.code == "TN" else False,
                    'tax_id': rec.partner_id.vat if rec.partner_id and rec.partner_id.vat else '',
                    'partner_full_name': rec.partner_id.name if rec.partner_id else '',
                    'partner_address': rec.partner_id.street if rec.partner_id and rec.partner_id.street else '',
                    'partner_mail': rec.partner_id.email if rec.partner_id and rec.partner_id.email else '',
                    'partner_phone': rec.partner_id.phone if rec.partner_id and rec.partner_id.phone else '',
                    'partner_activity': rec.partner_id.industry_id.name if rec.partner_id and rec.partner_id.industry_id else '',
                    'ref_certificate': rec.name if rec.name != '/' else '',
                    'total_amount_ht': sum(op['amount_ht'] for op in operation_lines) if operation_lines else 0.0,
                    'total_amount_ttc': sum(op['amount_ttc'] for op in operation_lines) if operation_lines else 0.0,
                    'total_amount_tva': sum(op['tva_amount'] for op in operation_lines) if operation_lines else 0.0,
                    'total_amount_rs': sum(op['amount_rs'] for op in operation_lines) if operation_lines else 0.0,
                    'total_taxes': 0.0,
                    'total_amount_amount_servi': sum(
                        op['amount_net_servi'] for op in operation_lines) if operation_lines else 0.0,
                    'total_amount_devise': sum(op['devise_ttc'] for op in operation_lines) if operation_lines else 0.0,
                    'total_amount_devise_rs': sum(
                        op['devise_rs'] for op in operation_lines) if operation_lines else 0.0,
                    'total_amount_devise_ttc': sum(
                        op['devise_ttc'] for op in operation_lines) if operation_lines else 0.0,
                    'total_amount_devise_servi': sum(
                        op['devise_servi'] for op in operation_lines) if operation_lines else 0.0,
                }

                if line and operation_lines:
                    operation_list = []
                    for operation in operation_lines:
                        if not rec.partner_id.operation_type:
                            raise UserError(_("Please Provide an Operation Type for vendor %s") % rec.partner_id.name)
                        operation_list.append({
                            'annee_facturation' : str(rec.invoice_date.year),
                            'cnpc' : '1' if operation['cnpc'] else '0',
                            'P_Charge' : '1' if operation['p_charge'] else '0',
                            'montant_ht' : str(operation['amount_ht']),
                            'taux_rs' : str(operation['rs_rate']),
                            'taux_tva' : str(operation['tva_rate']),
                            'tva_amount' : str(operation['tva_amount']),
                            'amount_ttc' : str(operation['amount_ttc']),
                            'amount_rs' : str(operation['amount_rs']),
                            'taxe_additionnelle_code' : str(operation['taxe_additionnelle_code']),
                            'taxe_additionnelle_rate' : str(operation['taxe_additionnelle_rate']),
                            'amount_net_servi' : str(operation['amount_net_servi']),
                            'devise_code' : str(operation['devise_code']),
                            'devise_rate' : str(operation['devise_rate']),
                            'devise_rs' : str(operation['devise_rs']),
                            'devise_ttc' : str(operation['devise_ttc']),
                            'devise_servi' : str(operation['devise_servi']),
                            'operation_type' : str(rec.partner_id.operation_type.code),
                        })
                    certif_list.append({
                        'type_identifiant' : rec.get_ligne_type_identifiant(rec.partner_id),
                        'identifiant' : rec.get_ligne_identifiant(rec.partner_id),
                        'categorie_contribuable' : str(rec.partner_id.category_type),
                        'date_naissance' : line['birth_date'],
                        'country_id' : rec.partner_id.country_id.code,
                        'resident' : '1' if line['partner_tunisian'] else '0',
                        'nom_prenom_raison_sociale' : line['partner_full_name'],
                        'adresse' : line['partner_address'],
                        'activite' : line['partner_activity'],
                        'adresse_mail' : line['partner_mail'],
                        'num_tel' : line['partner_phone'],
                        'date_payement' : line['payment_date'],
                        'ref_certif_chez_declarant' : str(line['ref_certificate']),
                        'liste_operations' : operation_list,
                        'total_amount_ht' : str(line['total_amount_ht']),
                        'total_amount_tva' : str(line['total_amount_tva']),
                        'total_amount_ttc' : str(line['total_amount_ttc']),
                        'total_amount_rs' : str(line['total_amount_rs']),
                        'total_taxes' : str(line['total_taxes']),
                        'total_amount_net_servi' : str(line['total_amount_amount_servi']),
                        'total_amount_devise' : str(line['total_amount_devise']),
                        'total_amount_devise_rs' : str(line['total_amount_devise_rs']),
                        'total_amount_devise_ttc' : str(line['total_amount_devise_ttc']),
                        'total_amount_devise_servi' : str(line['total_amount_devise_servi']),
                    })
                declaration_data['certif_list'] = certif_list
            return declaration_data

    def create_xml_file(self):
        def safe_text(value):
            return html.escape(str(value)) if value is not None else ""

        def format_rate(value):
            if value is None or value == "":
                return ""
            try:
                amount_str = f"{float(value):.2f}"
                return amount_str
            except (ValueError, TypeError):
                return ""

        def format_amount(value):
            def floor_to_3_decimals(amount):
                return math.floor(amount * 1000) / 1000

            if value is None or value == "":
                return ""
            try:
                print('Value', value)
                amount_float = floor_to_3_decimals(float(value))
                print('Value', amount_float)
                amount_str = f"{float(amount_float):.3f}"
                print('Value', amount_str)
                return amount_str.replace('.', '')
            except (ValueError, TypeError):
                return ""
        for rec in self:
            if not rec.withholding_id:
                raise UserError(_('This Invoice has no withholding Tax Applied, Please add one and regenerate !!!'))

        generated_data = self.generate_data_for_xml()

        root = Element("DeclarationsRS")

        root.set("VersionSchema", "1.0")

        Declarant = SubElement(root, 'Declarant')
        SubElement(Declarant, 'TypeIdentifiant').text = safe_text(generated_data.get('typeidentifiant'))
        SubElement(Declarant, 'Identifiant').text = safe_text(generated_data.get('identifiant'))
        SubElement(Declarant, 'CategorieContribuable').text =  safe_text(generated_data.get('categorie_contribuable'))

        ReferenceDeclaration = SubElement(root, 'ReferenceDeclaration')
        SubElement(ReferenceDeclaration, 'ActeDepot').text = safe_text(generated_data.get('acte_depot'))
        SubElement(ReferenceDeclaration, 'AnneeDepot').text = safe_text(generated_data.get('annee_depot'))
        SubElement(ReferenceDeclaration, 'MoisDepot').text = safe_text(generated_data.get('mois_depot'))

        acte_depot = generated_data.get('acte_depot')
        certif_list = generated_data.get('certif_list', [])

        container_node = None
        if acte_depot == 0:
            container_node = SubElement(root, 'AjouterCertificats')
        elif acte_depot == 1:
            container_node = SubElement(root, 'ModifierCertificats')
        else:
            raise UserError(_('Invalid Acte Depot CODE'))

        for certif in certif_list:
            Certificat = SubElement(container_node, 'Certificat')
            Beneficiaire = SubElement(Certificat, 'Beneficiaire')
            IdTaxpayer = SubElement(Beneficiaire, 'IdTaxpayer')
            type_identifiant = certif.get('type_identifiant')

            type_mapping = {
                '1': 'MatriculeFiscal',
                '2': 'CIN',
                '3': 'Passeport',
                '4': 'CarteSejour',
                '5': 'AutreIdentifiantFiscal',
            }

            # Get the node name from mapping, default to 'UnknownIdentifiant' if not found
            node_name = type_mapping.get(certif.get('type_identifiant'), 'UnknownIdentifiant')
            node = SubElement(IdTaxpayer, node_name)

            SubElement(node, 'TypeIdentifiant').text = safe_text(certif.get('type_identifiant'))
            SubElement(node, 'Identifiant').text = safe_text(certif.get('identifiant'))

            if type_identifiant in ['2', '3', '4', '5']:
                SubElement(node, 'DateNaissance').text = safe_text(certif.get('date_naissance'))
                SubElement(node, 'Pays').text = safe_text(certif.get('country_id'))
            SubElement(node, 'CategorieContribuable').text = safe_text(certif.get('categorie_contribuable'))

            SubElement(Beneficiaire, 'Resident').text = safe_text(certif.get('resident'))
            SubElement(Beneficiaire, 'NometprenonOuRaisonsociale').text = safe_text(
                certif.get('nom_prenom_raison_sociale'))
            SubElement(Beneficiaire, 'Adresse').text = safe_text(certif.get('adresse'))
            SubElement(Beneficiaire, 'Activite').text = safe_text(certif.get('activite'))

            InfosContact = SubElement(Beneficiaire, 'InfosContact')
            SubElement(InfosContact, 'AdresseMail').text = safe_text(certif.get('adresse_mail'))
            SubElement(InfosContact, 'NumTel').text = safe_text(certif.get('num_tel'))
            payment_date = certif.get('date_payement')

            # Vérifie si c'est déjà un datetime.date
            if isinstance(payment_date, (datetime, date)):
                dt = payment_date
            else:
                dt = datetime.strptime(payment_date, "%Y-%m-%d")

            date_pay = dt.strftime("%d/%m/%Y")
            SubElement(Certificat, 'DatePayement').text = safe_text(date_pay)
            SubElement(Certificat, 'Ref_certif_chez_declarant').text = safe_text(
                certif.get('ref_certif_chez_declarant'))

            ListeOperations = SubElement(Certificat, 'ListeOperations')
            for operation in certif.get('liste_operations', []):
                Operation = SubElement(ListeOperations, 'Operation')
                Operation.set("IdTypeOperation", safe_text(operation.get('operation_type')))
                SubElement(Operation, 'AnneeFacturation').text = safe_text(operation.get('annee_facturation'))
                SubElement(Operation, 'CNPC').text = safe_text(operation.get('cnpc'))
                SubElement(Operation, 'P_Charge').text = safe_text(operation.get('P_Charge'))
                SubElement(Operation, 'MontantHT').text = format_amount(operation.get('montant_ht'))
                SubElement(Operation, 'TauxRS').text = format_rate(operation.get('taux_rs'))
                SubElement(Operation, 'TauxTVA').text = format_rate(operation.get('taux_tva'))
                SubElement(Operation, 'MontantTVA').text = format_amount(operation.get('tva_amount'))
                SubElement(Operation, 'MontantTTC').text = format_amount(operation.get('amount_ttc'))
                SubElement(Operation, 'MontantRS').text = format_amount(operation.get('amount_rs'))
                taxe_code = operation.get('taxe_additionnelle_code')
                if taxe_code not in [None, '', False, 0, 'False']:
                    TaxeAdditionnelle = SubElement(Operation, 'TaxeAdditionnelle')
                    TaxeAdditionnelle.set("Code", safe_text(taxe_code))
                    TaxeAdditionnelle.set("Taux", operation.get('taxe_additionnelle_rate', 0))

                SubElement(Operation, 'MontantNetServi').text = format_amount(operation.get('amount_net_servi'))
                # Devise
                devise_code = operation.get('devise_code')
                if devise_code not in [None, '', False, 0, 'False']:
                    Devise = SubElement(Operation, 'Devise')
                    SubElement(Devise, 'CodeDevise').text = safe_text(devise_code)
                    SubElement(Devise, 'TauxChange').text = format_amount(operation.get('devise_rate'))
                    SubElement(Devise, 'MontantRSDevise').text = format_amount(operation.get('devise_rs'))
                    SubElement(Devise, 'MontantTTCDevise').text = format_amount(operation.get('devise_ttc'))
                    SubElement(Devise, 'MontantNetServiDevise').text = format_amount(operation.get('devise_servi'))

            TotalPayement = SubElement(Certificat, 'TotalPayement')
            SubElement(TotalPayement, 'TotalMontantHT').text = format_amount(certif.get('total_amount_ht'))
            SubElement(TotalPayement, 'TotalMontantTVA').text = format_amount(certif.get('total_amount_tva'))
            SubElement(TotalPayement, 'TotalMontantTTC').text = format_amount(certif.get('total_amount_ttc'))
            SubElement(TotalPayement, 'TotalMontantRS').text = format_amount(certif.get('total_amount_rs'))
            if taxe_code not in [None, '', False, 0, 'False']:
                SubElement(TotalPayement, 'TotalTaxes').text = format_amount(certif.get('total_taxes'))
            SubElement(TotalPayement, 'TotalMontantNetServi').text = format_amount(certif.get('total_amount_net_servi'))

        # Génération XML
        tree = ElementTree(root)
        file_obj = BytesIO()
        tree.write(file_obj, encoding='utf-8', xml_declaration=True)
        file_obj.seek(0)
        xml_content = file_obj.read().decode('utf-8')
        # Remplacer l'en-tête XML
        lines = xml_content.splitlines()
        if lines[0].startswith('<?xml'):
            lines[0] = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        xml_content = "\n".join(lines)

        dom = minidom.parseString(xml_content)
        # formatted_xml = dom.toprettyxml(indent=" ")
        pretty_xml = dom.toprettyxml(indent=" ", encoding="utf-8").decode('utf-8')

        # Supprimer l'en-tête par défaut généré par minidom et remettre le tien
        pretty_lines = pretty_xml.splitlines()
        if pretty_lines[0].startswith('<?xml'):
            pretty_lines[0] = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        formatted_xml = '\n'.join(pretty_lines)
        encoded_file = base64.b64encode(formatted_xml.encode('utf-8'))

        self.sudo().write({
            'declaration_file': encoded_file,
            'declaration_file_name': self.get_declaration_file_name(),
        })

    def get_declaration_file_name(self):
        mf = str(self.company_id.vat).replace('/', '').replace(' ', '')
        if len(mf) < 13:
            mf = mf.zfill(13)  # Ajoute des zéros au début jusqu'à 13 caractères
        elif len(mf) > 13:
            raise UserError(_('Company VAT ID is wrong'))

        # À ce stade, len(mf) == 13
        mf8 = mf[:8]  # Récupère les 8 premiers caractères
        year = str(self.invoice_date.year)
        month = f"{int(self.invoice_date.month):02d}"
        act = '1'
        name = f"{mf8}-{year}-{month}-{act}.xml"
        return name

