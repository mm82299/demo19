# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ResCompany(models.Model):
    _inherit = 'res.company'

    company_short_name = fields.Char('Company Short Name')
    company_category = fields.Selection([
        ('SARL', 'SARL : Société à Responsabilité Limitée'),
        ('SUARL', 'SUARL : Société Unipersonnelle à Responsabilité Limitée'),
        ('SA', 'SA : Société Anonyme'),
        ('SNC', 'SNC : Société en Nom Collectif'),
        ('SCS', 'SCS : Société en Commandite Simple'),
        ('SCA', 'SCA : Société en Commandite par Actions'),
        ('GIE', 'GIE : Groupement d’Intérêt Économique'),
        ('SEP', 'SEP : Société en Participation'),
        ('HOLDING', 'HOLDING : Société de Groupement')
    ], string="Forme Juridique (Code)", default='SARL', help="Sélectionnez la catégorie selon le Code des Sociétés Commerciales")
    # Fiscal Information - Using standard VAT field
    tn_fiscal_id_type = fields.Selection(
        [('I-01', 'Matricule Fiscal')],
        string='Type Identifiant',
        default='I-01',
        required=True
    )
    tn_vat_regime = fields.Selection([
        ('A', 'Assujetti Obligatoire'),
        ('P', 'Assujetti Partiel'),
        ('B', 'Assujetti par Option'),
        ('F', 'Assujetti Forfaitaire'),
        ('N', 'Non Assujetti'),
    ], string='Régime TVA', compute='_compute_vat_regime', store=True)

    # Bank Information for TEIF
    tn_bank_account_number = fields.Char(
        string='RIB/IBAN',
        help="Numéro de compte bancaire pour paiement"
    )
    tn_bank_name = fields.Char(string='Nom de la Banque')
    tn_bank_branch_code = fields.Char(string='Code Agence')
    capital = fields.Float('Capital', digits=(16, 3))
    # ANCE API Configuration (SIGNATURE ONLY)
    ngsign_api_url = fields.Char(
        string='ANCE API URL',
        default='https://sandbox.ng-sign.com/server/protected/invoice',
        help="URL de l'API ANCE pour signature uniquement"
    )
    ngsign_api_token = fields.Char(
        string='ANCE API Token',
        help="Token JWT généré depuis l'interface ANCE"
    )
    ngsign_seal_passphrase = fields.Char(
        string='SEAL Passphrase',
        help="Passphrase pour déchiffrer le PIN du certificat SEAL"
    )
    ngsign_use_seal = fields.Boolean(
        string='Utiliser SEAL',
        default=False,
        help="Signature automatique avec certificat SEAL (recommandé)"
    )
    honoraire_use = fields.Boolean(
        string="Honoraire",
        default=False,
        help="Utiliser note d'honoraire au lieu du facture"
    )
    require_einvoice = fields.Boolean(
        string="Require E-Invoice",
        default=False,
        help="If checked, e-invoice features will be available."
    )
    use_custom_product_description = fields.Boolean(
        string="Use custom description for product",
        default=False,
        help="If checked, the product line in TEIF XML will use a custom description."
    )
    custom_product_description_template = fields.Text(
        string="Product Description Template",
        default="Nous avons l'honneur de vous présenter notre note d'honoraires relative à notre intervention au titre \"{product_name}\"",
        help="Template for the product description in TEIF XML. Use {product_name} and {description} as placeholders."
    )

    # TTN SOAP API Configuration (VALIDATION)
    ttn_soap_url = fields.Char(
        string='TTN SOAP URL',
        default='https://test.elfatoora.tn/ElfatouraServices/EfactService',
        help="URL de votre serveur SOAP pour validation TTN"
    )
    ttn_soap_username = fields.Char(
        string='TTN SOAP Username',
        help="Nom d'utilisateur pour authentification SOAP TTN"
    )
    ttn_soap_password = fields.Char(
        string='TTN SOAP Password',
        help="Mot de passe pour authentification SOAP TTN"
    )
    ttn_soap_timeout = fields.Integer(
        string='TTN SOAP Timeout (secondes)',
        default=30,
        help="Timeout pour les appels SOAP vers TTN"
    )
    ttn_auto_submit = fields.Boolean(
        string='Soumission Automatique à TTN',
        default=False,
        help="Soumettre automatiquement à TTN après signature"
    )

    # QR Code Configuration
    teif_qr_position_x = fields.Integer(
        string='QR Position X',
        default=450,
        help="Position X du QR code (0 = gauche de la page)"
    )
    teif_qr_position_y = fields.Integer(
        string='QR Position Y',
        default=50,
        help="Position Y du QR code (0 = bas de la page)"
    )
    teif_qr_position_page = fields.Integer(
        string='QR Page',
        default=0,
        help="Page où insérer le QR code (0 = première page)"
    )
    teif_label_position_x = fields.Integer(string='Label Position X', default=50)
    teif_label_position_y = fields.Integer(string='Label Position Y', default=50)
    teif_label_position_page = fields.Integer(string='Label Page', default=0)

    @api.depends('vat')
    def _compute_vat_regime(self):
        """Extract VAT regime from matricule fiscal"""
        for company in self:
            if company.vat and len(company.vat) >= 9:
                fiscal_id = company.vat.replace('TN', '').replace('tn', '')
                if len(fiscal_id) >= 9:
                    vat_code = fiscal_id[8]
                    company.tn_vat_regime = vat_code if vat_code in ['A', 'P', 'B', 'F', 'N'] else False
                else:
                    company.tn_vat_regime = False
            else:
                company.tn_vat_regime = False

    @api.constrains('vat', 'country_id')
    def _check_tn_vat(self):
        """Validate Tunisian Fiscal ID format"""
        for company in self:
            if company.country_id and company.country_id.code == 'TN' and company.vat:
                fiscal_id = company.vat.replace('TN', '').replace('tn', '')
                pattern = r'^[0-9]{7}[ABCDEFGHJKLMNPQRSTVWXYZ][ABDNP][CMNPE][0-9]{3}$'
                if not re.match(pattern, fiscal_id):
                    raise ValidationError(_(
                        "Le matricule fiscal tunisien doit respecter le format: "
                        "7 chiffres + lettre de contrôle + code TVA + catégorie + 3 chiffres d'établissement\n"
                        "Exemple: 0736202XAM000"
                    ))

    def get_tn_fiscal_id(self):
        """Get clean Tunisian fiscal ID without country prefix"""
        self.ensure_one()
        if self.vat:
            return self.vat.replace('TN', '').replace('tn', '')[:8]
        return False
