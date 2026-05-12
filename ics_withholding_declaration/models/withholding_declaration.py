
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


class WithholdingDeclaration(models.Model):
    _name = 'withholding.declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'withholding declaration'

    name = fields.Char(string='Name', required=True, readonly=True, compute='_compute_name', copy=False)
    date = fields.Date(string='Date' , default=date.today(), copy=False)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user , readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company , readonly=True)
    declaration_file = fields.Binary(string='Declaration File', attachment=True, readonly=True, copy=False)
    declaration_file_name = fields.Char(string='Declaration File Name', readonly=True, copy=False)
    generation_type = fields.Selection([('monthly', 'Monthly'), ('period', 'By period')], string="Generation Type", required=True, copy=False)
    date_start = fields.Date('Start Date', copy=False)
    date_end = fields.Date('End Date', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_validate', 'To Validate'),
        ('validated', 'Validated'),
        ('cancel', 'Cancel'),
    ], string='State', default='draft', copy=False)

    period = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string='period',required=True)

    year = fields.Integer(string='Year', required=True)

    category_type = fields.Selection([('PP' ,'Personne Physique'),('PM','Personne Morale')], string='Category Type', required=True,default='PM')

    declaration_line_ids = fields.One2many('withholding.declaration.line', 'declaration_id', string='Declaration Lines', copy=False)

    act_depot = fields.Selection([('initial','Initial'),('rectificatif','Rectificatif')], string='Acte Depot', required=True, help='Acte de Dépôt (initial ou rectificatif) ',default='initial', copy=False)

    declaration_line_ids_edit = fields.One2many('withholding.declaration.line', 'declaration_id_edit', string='Declaration Lines', copy=False)

    declaration_line_ids_delete = fields.One2many('withholding.declaration.line', 'declaration_id_delete', string='Declaration Lines', copy=False)

    declaration_to_modify = fields.Many2one('withholding.declaration', string='Declaration to modify', copy=False)

    @api.constrains('year')
    def _check_year(self):
        for record in self:
            if record.year:
                if len(str(record.year)) != 4:
                    raise ValidationError('Please enter a valid year')


    @api.onchange('year','period')
    def _compute_name (self):
        for record in self:
            if record.period and record.year:
                record.name = f"Declaration-{record.year}/{record.period}"
            else:
                record.name = 'Declaration'

    def first_day_of_month(self, year, month):
        return date(year, month, 1)

    def last_day_of_month(self, year, month):
        last_day_num = calendar.monthrange(year, month)[1]
        return date(year, month, last_day_num)

    def get_witholding_data(self,year,priode):
        first_day_of_mount = self.first_day_of_month(year, int(priode))
        last_day_of_mount = self.last_day_of_month(year, int(priode))
        if self.generation_type == 'monthly':
            withholding = self.env['account.withholding'].sudo().search([('date', '>=', first_day_of_mount),
                                                                     ('date', '<=', last_day_of_mount), ('company_id', '=', self.company_id.id)])
        else:
            if self.date_start and self.date_end:
                withholding = self.env['account.withholding'].sudo().search([('date', '>=', self.date_start ),
                                                                         ('date', '<=', self.date_end), ('company_id', '=', self.company_id.id)])
            elif self.date_start and not self.date_end:
                withholding = self.env['account.withholding'].sudo().search([('date', '=', self.date_start ), ('company_id', '=', self.company_id.id)])
            else:
                raise UserError(_('At least Provide a Start Date to proceed'))

        return withholding

    def get_company_information(self):
        company = self.env['res.company'].sudo().search([('id', '=', self.company_id.id)])
        return company

    def get_declarant_information(self):
        if not self.company_id.vat:
            raise UserError('Please enter the VAT number in the company form')
        vat = self.company_id.vat
        company_vat = vat[2:]
        data = {
            'typeidentifiant': '1',
            'identifiant': company_vat,
            'typecategoriepersonne': self.catergory_type,
        }
        return data

    def get_reference_declaration(self):
        data = {
            'annee_depot': str(self.year),
            'mois_depot': f"{int(self.period):02d}",
        }
        return data

    def get_type_act(self):
        if self.act_depot == 'initial':
            return '0'
        else:
            return '1'

    def get_month_start_end(self,year,month):

        if self.generation_type == 'monthly':
            first_day_this_month = datetime(int(year), int(month), 1)
            last_day = calendar.monthrange(int(year), int(month))[1]
            last_day_this_month = datetime(int(year), int(month), last_day)
            date = {
                'first_day': first_day_this_month.date(),
                'last_day': last_day_this_month.date(),
            }
        else:
            if self.date_start and self.date_end:
                date = {
                    'first_day': self.date_start,
                    'last_day': self.date_end,
                }
            elif self.date_start and not self.date_end:
                date = {
                    'first_day': self.date_start,
                    'last_day': self.date_start,
                }
            else:
                raise UserError(_('At least Provide a Start Date to proceed'))

        return date


    def generate_declaration_line_data(self):
        # Validate required fields before processing
        if not self.year or self.year <= 0:
            raise UserError(_("Please enter a valid year before generating declaration lines."))
        if len(str(self.year)) != 4:
            raise UserError(_("Year must be a 4-digit number (e.g. 2025)."))
        if not self.period:
            raise UserError(_("Please select a period (month) before generating declaration lines."))
        if not self.generation_type:
            raise UserError(_("Please select a generation type before generating declaration lines."))
        if self.generation_type == 'period' and not self.date_start:
            raise UserError(_("Please provide at least a start date to generate declaration lines."))

        if self.declaration_line_ids:
            for line in self.declaration_line_ids:
                for op in line.operation_line_ids:
                    op.sudo().unlink()
                line.sudo().unlink()
        if self.act_depot == 'initial':
            withholding_date = self.get_month_start_end(self.year, self.period)
            data = []
            first_day = withholding_date.get('first_day')
            last_day = withholding_date.get('last_day')
            withholding_data = self.env['account.withholding'].sudo().search([('date', '>=', first_day),('date', '<=', last_day), ('state', '=', 'done'), ('type', '=', 'in_withholding'), ('company_id', '=', self.company_id.id)])

            for rec in withholding_data:
                line = {
                    'name': rec.name if rec.name else '',
                    'company_id': self.company_id.id,
                    'declaration_id': self.id,
                    'withholding_id': rec.id,
                    'payment_date': rec.date,
                    'partner_id': rec.partner_id.id if rec.partner_id else False,
                    'country_id': rec.partner_id.country_id.id if rec.partner_id and rec.partner_id.country_id else False,
                    'operation_type_category': rec.partner_id.operation_type_category.id if rec.partner_id and rec.partner_id.operation_type_category else False,
                    'operation_type': rec.partner_id.operation_type.id if rec.partner_id and rec.partner_id.operation_type else False,
                    'tax_id_type': rec.partner_id.tax_id_type if rec.partner_id and rec.partner_id.tax_id_type else False,
                    'category_type': rec.partner_id.category_type if rec.partner_id and rec.partner_id.category_type else False,
                    'partner_tunisian': True if rec.partner_id and rec.partner_id.country_id and rec.partner_id.country_id.code == "TN" else False,
                    'tax_id' : rec.partner_id.vat if rec.partner_id and rec.partner_id.vat else '',
                    'partner_full_name': rec.partner_id.name if rec.partner_id else '',
                    'partner_address': rec.partner_id.street if rec.partner_id and rec.partner_id.street else '',
                    'partner_mail': rec.partner_id.email if rec.partner_id and rec.partner_id.email else '',
                    'partner_phone': rec.partner_id.phone if rec.partner_id and rec.partner_id.phone else '',
                    'partner_activity': rec.partner_id.industry_id.name if rec.partner_id and rec.partner_id.industry_id else '',
                    'ref_certificate': rec.account_move_id.name if rec.account_move_id else '',
                    'total_amount_ht' : 0.0,
                    'total_amount_ttc': 0.0,
                }

                line_id = self.env['withholding.declaration.line'].sudo().create(line)

                def floor_to3_decimals(number):
                    return math.floor(float(number) * 1000) / 1000

                if rec.account_invoice_ids:
                    for inv in rec.account_invoice_ids:
                        for invoice_line_id in inv.invoice_line_ids:
                            amount_ht = floor_to3_decimals((invoice_line_id.price_total / (1 + (
                                        int(invoice_line_id.tax_ids.filtered(lambda
                                                                                 l: l.include_base_amount == False).amount) / 100)))) if invoice_line_id.price_total and invoice_line_id.tax_ids else invoice_line_id.price_total
                            tva_rate = int(
                                invoice_line_id.tax_ids.filtered(lambda l: l.include_base_amount == False).amount)
                            rs_rate = rec.account_withholding_tax_ids.rate
                            amount_tva = (amount_ht * tva_rate) / 100
                            tva_amount = floor_to3_decimals(amount_tva)
                            ttc_amount = amount_ht + tva_amount
                            amount_ttc = floor_to3_decimals(ttc_amount)
                            rs_amount = (amount_ttc * rs_rate) / 100
                            amount_rs = floor_to3_decimals(rs_amount)
                            net_servi_amount = amount_ttc - amount_rs
                            amount_net_servi = floor_to3_decimals(net_servi_amount)
                            devise_code = invoice_line_id.currency_id.name if inv.company_id.currency_id.id != inv.currency_id.id else ''
                            devise_rate = invoice_line_id.currency_id._get_conversion_rate(self, inv.company_id.currency_id, inv.company_id, inv.invoice_date)  if inv.company_id.currency_id.id != inv.currency_id.id else 0
                            devise_rs =  rec.retenue_amount if inv.company_id.currency_id.id != inv.currency_id.id else 0
                            devise_ttc = invoice_line_id.price_subtotal if inv.company_id.currency_id.id != inv.currency_id.id else 0
                            devise_servi = invoice_line_id.price_subtotal - rec.retenue_amount  if inv.company_id.currency_id.id != inv.currency_id.id else 0

                            operation_line = {
                                'name': inv.name if inv.name else '',
                                'company_id': self.company_id.id,
                                'declaration_line_id': line_id.id,
                                'invoice_date': inv.invoice_date if inv.invoice_date else False,
                                'cnpc': False,
                                'p_charge': False,
                                'amount_ht': floor_to3_decimals(amount_ht),
                                'rs_rate': rs_rate,
                                'tva_rate': tva_rate,
                                'tva_amount' :floor_to3_decimals(tva_amount) ,
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
                            self.env['withholding.declaration.operation.line'].sudo().create(operation_line)
                            self.sudo().write({'state': 'to_validate'})
                else:
                    rate = 19.0
                    tva_rate = rate / 100.0
                    amount_ttc = floor_to3_decimals(rec.amount_total_rs)
                    amount_ht = amount_ttc / (1 + tva_rate)
                    ht_amount = floor_to3_decimals(amount_ht)
                    amount_tva = amount_ttc - ht_amount
                    tva_amount = floor_to3_decimals(amount_tva)
                    amount_net_servi = rec.amount_total_rs - rec.retenue_amount
                    operation_line = {
                        'name': rec.name if rec.name else '',
                        'company_id': self.company_id.id,
                        'declaration_line_id': line_id.id,
                        'invoice_date': rec.date if rec.name else False,
                        'cnpc': False,
                        'p_charge': False,
                        'amount_ht': floor_to3_decimals(ht_amount) if ht_amount else 0.0,
                        'rs_rate': rec.account_withholding_tax_ids.rate,
                        'tva_rate': rate,
                        'tva_amount': tva_amount,
                        'amount_ttc': floor_to3_decimals(rec.amount_total_rs) if rec.amount_total_rs else 0.0,
                        'amount_rs': floor_to3_decimals(rec.retenue_amount) if rec.retenue_amount else 0.0,
                        'taxe_additionnelle_code': False,
                        'taxe_additionnelle_rate': 0,
                        'amount_net_servi': floor_to3_decimals(amount_net_servi) if amount_net_servi else 0.0,
                        'devise_code': '',
                        'devise_rate': 0,
                        'devise_rs': 0,
                        'devise_ttc': 0,
                        'devise_servi': 0,
                    }
                    self.env['withholding.declaration.operation.line'].sudo().create(operation_line)
                    self.sudo().write({'state': 'to_validate'})
                line_id.sudo().write({
                    'total_amount_ht': sum(operations.amount_ht for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_ttc': sum(operations.amount_ttc for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_tva': sum(operations.tva_amount for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_rs': sum(operations.amount_rs for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_amount_servi': sum(operations.amount_net_servi for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_devise': sum(operations.devise_ttc for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_devise_rs': sum(operations.devise_rs for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_devise_ttc': sum(operations.devise_ttc for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                    'total_amount_devise_servi': sum(operations.devise_servi for operations in line_id.operation_line_ids) if line_id.operation_line_ids else 0.0,
                })
        elif self.act_depot == 'rectificatif':
            if self.declaration_to_modify:
                for line in self.declaration_to_modify.declaration_line_ids:
                    copy_line = line.copy()
                    copy_line.sudo().write({'declaration_id': self.id})
            else:
                raise UserError('Please select a declaration to modify')
        else:
            raise UserError('Please select a valid action')

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
        if not line.tax_id:
            raise UserError(_('Please Provide Vendor VAT !!!'))
        cleaned_tax_id = line.tax_id.replace('/', '').replace(' ', '')

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

            declaration_data = {
                'typeidentifiant': '1',
                'identifiant': rec.get_company_matricule_fiscale(),
                'categorie_contribuable' : rec.category_type,
                'acte_depot': 0 if rec.act_depot == 'initial' else 1,
                'annee_depot' : str(rec.year),
                'mois_depot' : f"{int(self.period):02d}",
            }
            for list in rec.declaration_line_ids:
                operation_list = []
                for operation in list.operation_line_ids:
                    if not operation.operation_type:
                        raise UserError(_("Please Provide an Operation Type for %s") % list.name)
                    operation_list.append({
                        'annee_facturation' : str(operation.invoice_date.year),
                        'cnpc' : '1' if operation.cnpc else '0',
                        'P_Charge' : '1' if operation.p_charge else '0',
                        'montant_ht' : str(operation.amount_ht),
                        'taux_rs' : str(operation.rs_rate),
                        'taux_tva' : str(operation.tva_rate),
                        'tva_amount' : str(operation.tva_amount),
                        'amount_ttc' : str(operation.amount_ttc),
                        'amount_rs' : str(operation.amount_rs),
                        'taxe_additionnelle_code' : str(operation.taxe_additionnelle_code.name),
                        'taxe_additionnelle_rate' : str(operation.taxe_additionnelle_rate),
                        'amount_net_servi' : str(operation.amount_net_servi),
                        'devise_code' : str(operation.devise_code.code),
                        'devise_rate' : str(operation.devise_rate),
                        'devise_rs' : str(operation.devise_rs),
                        'devise_ttc' : str(operation.devise_ttc),
                        'devise_servi' : str(operation.devise_servi),
                        'operation_type' : str(list.operation_type.code),
                    })
                certif_list.append({
                    'type_identifiant' : rec.get_ligne_type_identifiant(list),
                    'identifiant' : rec.get_ligne_identifiant(list),
                    'categorie_contribuable' : str(list.category_type),
                    'date_naissance' : list.birth_date,
                    'country_id' : list.country_id.code,
                    'resident' : '1' if list.partner_tunisian else '0',
                    'nom_prenom_raison_sociale' : list.partner_full_name,
                    'adresse' : list.partner_address,
                    'activite' : list.partner_activity,
                    'adresse_mail' : list.partner_mail,
                    'num_tel' : list.partner_phone,
                    'date_payement' : list.payment_date,
                    'ref_certif_chez_declarant' : str(list.ref_certificate),
                    'liste_operations' : operation_list,
                    'total_amount_ht' : str(list.total_amount_ht),
                    'total_amount_tva' : str(list.total_amount_tva),
                    'total_amount_ttc' : str(list.total_amount_ttc),
                    'total_amount_rs' : str(list.total_amount_rs),
                    'total_taxes' : str(list.total_taxes),
                    'total_amount_net_servi' : str(list.total_amount_amount_servi),
                    'total_amount_devise' : str(list.total_amount_devise),
                    'total_amount_devise_rs' : str(list.total_amount_devise_rs),
                    'total_amount_devise_ttc' : str(list.total_amount_devise_ttc),
                    'total_amount_devise_servi' : str(list.total_amount_devise_servi),
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
        year = str(self.year)
        month = f"{int(self.period):02d}"
        if  self.act_depot == 'initial':
            act = '0'
        else :
            act = '1'
        name = f"{mf8}-{year}-{month}-{act}.xml"
        return name


    def action_validate(self):
        for rec in self :
            rec.sudo().write({'state': 'validated'})


    def action_cancel(self):
        for rec in self :
            for line in rec.declaration_line_ids:
                line.operation_line_ids.unlink()
            rec.declaration_line_ids.unlink()
            rec.sudo().write({'state': 'cancel'})

    def action_reset_to_draft(self):
        for rec in self :
            rec.sudo().write({'state': 'draft'})




