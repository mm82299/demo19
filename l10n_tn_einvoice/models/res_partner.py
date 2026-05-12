# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Using standard VAT field - add type selector
    tn_fiscal_id_type = fields.Selection([
        ('I-01', 'Matricule Fiscal'),
        ('I-02', 'Carte d\'Identité Nationale (CIN)'),
        ('I-03', 'Carte de Séjour'),
        ('I-04', 'Matricule Fiscal Non Tunisien'),
    ], string='Type Identifiant', default='I-01',
        help="Type d'identifiant fiscal utilisé dans le champ NIF/TVA")

    tn_partner_name_type = fields.Selection([
        ('Physical', 'Nom et Prénom'),
        ('Qualification', 'Raison Sociale'),
    ], string='Type de Nom', default='Qualification',
        compute='_compute_name_type', store=True, readonly=False)

    # Contact Details for TEIF
    tn_contact_person = fields.Char(string='Personne de Contact')
    tn_contact_phone = fields.Char(string='Téléphone Contact')
    tn_contact_fax = fields.Char(string='Fax Contact')
    tn_contact_email = fields.Char(string='Email Contact')


    public_company = fields.Boolean('Entreprise public')



    @api.depends('is_company', 'company_type')
    def _compute_name_type(self):
        """Auto-set name type based on partner type"""
        for partner in self:
            if partner.is_company or partner.company_type == 'company':
                partner.tn_partner_name_type = 'Qualification'
            else:
                partner.tn_partner_name_type = 'Physical'

    @api.constrains('vat', 'tn_fiscal_id_type', 'country_id')
    def _check_tn_vat(self):
        """Validate based on type and country"""
        for partner in self:
            if partner.vat and partner.country_id and partner.country_id.code == 'TN':
                # Remove TN prefix if exists
                fiscal_id = partner.vat.replace('TN', '').replace('tn', '')
                id_type = partner.tn_fiscal_id_type or 'I-01'

                if id_type == 'I-01':  # Matricule Fiscal
                    pattern = r'^[0-9]{7}[ABCDEFGHJKLMNPQRSTVWXYZ][ABDNP][CMNPE][0-9]{3}$'
                    if not re.match(pattern, fiscal_id):
                        raise ValidationError(_(
                            "Format matricule fiscal invalide.\n"
                            "Format attendu: 7 chiffres + lettre + code TVA + catégorie + 3 chiffres\n"
                            "Exemple: 0736202XAM000"
                        ))

                elif id_type == 'I-02':  # CIN
                    if not (len(fiscal_id) == 8 and fiscal_id.isdigit()):
                        raise ValidationError(_("La CIN doit contenir exactement 8 chiffres"))

                elif id_type == 'I-03':  # Carte Séjour
                    if not (len(fiscal_id) == 9 and fiscal_id.isdigit()):
                        raise ValidationError(_("La Carte de Séjour doit contenir exactement 9 chiffres"))

    def get_tn_fiscal_id(self):
        """Get clean Tunisian fiscal ID without country prefix"""
        self.ensure_one()
        if self.vat:
            return self.vat.replace('TN', '').replace('tn', '')
        return False

    @api.onchange('country_id')
    def _onchange_country_teif(self):
        """Set default fiscal ID type based on country"""
        if self.country_id and self.country_id.code == 'TN':
            if not self.tn_fiscal_id_type:
                self.tn_fiscal_id_type = 'I-01'
