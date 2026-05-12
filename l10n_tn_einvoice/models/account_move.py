# -*- coding: utf-8 -*-
from lxml import etree
import xml.dom.minidom
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging
import requests
import json
import base64
from zeep.helpers import serialize_object
from PIL import Image, ImageChops
from io import BytesIO

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # TEIF Fields
    teif_xml = fields.Text(string='TEIF XML', readonly=True, copy=False)
    teif_signed_xml = fields.Text(string='TEIF XML Signé', readonly=False, copy=False)
    teif_sealed_xml = fields.Text(string='TEIF XML Scellé TTN', readonly=True, copy=False)

    teif_ttn_id_save = fields.Char(
        string="TTN ID Save",
        help="Numéro unique généré par saveEfact avant traitement",
        copy=False,
        readonly=True
    )

    teif_ttn_message = fields.Text(
        string="Message TTN",
        help="Message de retour de TTN",
        copy=False,
        readonly=True
    )
    # ===== NEW BINARY FIELDS FOR DOWNLOADS =====
    teif_xml_file = fields.Binary(
        string='Fichier TEIF XML',
        compute='_compute_teif_xml_file',
        readonly=True,
        copy=False,
        attachment=True
    )
    teif_xml_filename = fields.Char(
        string='Nom Fichier TEIF XML',
        compute='_compute_teif_xml_filename',
        store=True
    )

    teif_signed_xml_file = fields.Binary(
        string='Fichier TEIF XML Signé',
        compute='_compute_teif_signed_xml_file',
        readonly=True,
        copy=False,
        attachment=True
    )
    teif_signed_xml_filename = fields.Char(
        string='Nom Fichier TEIF XML Signé',
        compute='_compute_teif_signed_xml_filename',
        store=True
    )

    teif_sealed_xml_file = fields.Binary(
        string='Fichier TEIF XML Scellé',
        compute='_compute_teif_sealed_xml_file',
        readonly=True,
        copy=False,
        attachment=True
    )
    teif_sealed_xml_filename = fields.Char(
        string='Nom Fichier TEIF XML Scellé',
        compute='_compute_teif_sealed_xml_filename',
        store=True
    )
    teif_status = fields.Selection([
        ('draft', 'Non Signé'),
        ('generated', 'XML Généré'),
        ('sent_ngsign', 'Envoyé à ANCE'),
        ('signed', 'Signé par ANCE'),
        ('sent_ttn', 'Envoyé à TTN'),
        ('ttn_validated', 'Validé par TTN'),
        ('ttn_rejected', 'Rejeté par TTN'),
        ('error', 'Erreur'),
    ], string='Statut TEIF', default='draft', copy=False)

    teif_ttn_reference = fields.Char(
        string='Référence TTN',
        readonly=True,
        copy=False,
        help="Référence unique générée par TTN"
    )
    teif_qr_code = fields.Binary(
        string='QR Code',
        store = True,
        readonly=True,
        copy=False,
        attachment=True
    )
    teif_ngsign_uuid = fields.Char(
        string='UUID ANCE',
        readonly=True,
        copy=False,
        help="UUID de transaction ANCE"
    )
    ngsign_transaction_uuid = fields.Char(
        string='Transaction UUID ANCE',
        readonly=True,
        copy=False,
        help="UUID de transaction ANCE"
    )
    teif_ttn_validation_date = fields.Datetime(
        string='Date Validation TTN',
        readonly=True,
        copy=False
    )
    teif_error_message = fields.Text(string='Message d\'Erreur', readonly=True, copy=False)

    # Additional TEIF Fields
    teif_document_type = fields.Selection([
        ('I-11', 'Facture'),
        ('I-12', 'Avoir'),
        ('I-13', "Note d’honoraire"),
        ('I-14', 'Décompte (marché public)'),
        ('I-15', 'Facture Export'),
        ('I-16', 'Bon de commande'),
    ], string='Type Document TEIF', default='I-11', compute='_compute_teif_document_type',
        store=True)

    teif_special_conditions = fields.Text(
        string='Conditions Spéciales',
        help="Ex: Ventes en suspension de taxes, Ventes à l'exportation"
    )

    saleorder_number = fields.Char('Numéro de bon de commande')
    suspension_number = fields.Char('Numéro de l’autorisation de suspension de la TVA', compute="compute_suspension_number")
    decompte_number = fields.Char('Numéro de décompte')
    public_procuerement = fields.Char('Numéro de marché public')
    public_procuerement_name = fields.Char('Nom marché public')
    public_company = fields.Boolean('Entreprise public', related="partner_id.public_company")
    # Le champ qui recevra le résultat HTML de l'API
    elfatoora_html_preview = fields.Html(string="Aperçu Facture Elfatoora", readonly=True)
    is_decamp = fields.Boolean(string="C'est un décompt")

    def _get_ttn_invoice_name(self):
        """ Get invoice name to send to TTN without slashes """
        self.ensure_one()
        return self.name.replace('/', '-') if self.name else ''

    def action_transform_xml_to_html(self):
        """
        Récupère le XML de teif_sealed_xml, l'envoie à Elfatoora
        et stocke le retour HTML.
        """
        self.ensure_one()

        if not self.teif_sealed_xml:
            raise UserError(_("Le champ 'XML Scellé' est vide. Impossible de transformer le document."))

        # 1. Encodage du texte XML en Base64
        # On encode d'abord le string en bytes (utf-8) puis en base64
        xml_bytes = self.teif_sealed_xml.encode('utf-8')
        base64_xml = base64.b64encode(xml_bytes).decode('utf-8')
        company = self.company_id
        # 2. Paramètres de l'API
        url = "https://test.elfatoora.tn/ElfatouraServicesRest/rest/api/transform"
        payload = {
            "login": company.ttn_soap_username,
            "password": company.ttn_soap_password,
            "matricule": company.get_tn_fiscal_id()[:8],
            "documentEfact": base64_xml
        }
        headers = {'Content-Type': 'application/json'}

        try:
            # 3. Appel au service
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            # Vérification de la réponse
            if response.status_code == 200:
                # On remplit le champ HTML avec le corps de la réponse
                self.elfatoora_html_preview = response.text
            else:
                _logger.error("Elfatoora Error %s: %s", response.status_code, response.text)
                raise UserError(_("L'API a retourné une erreur (Code %s).") % response.status_code)

        except requests.exceptions.RequestException as e:
            raise UserError(_("Erreur de communication avec Elfatoora : %s") % str(e))

    @api.depends('partner_id', 'invoice_date')
    def compute_suspension_number(self):
        for rec in self:
            if rec.invoice_date and rec.partner_id and rec.partner_id.get_certificate(rec.invoice_date):
                rec.suspension_number = rec.partner_id.get_certificate(rec.invoice_date).name
            else:
                rec.suspension_number = False




    @api.depends('move_type', 'partner_id', 'currency_id', 'company_id', 'company_id.currency_id','is_decamp')
    def _compute_teif_document_type(self):
        """Auto-set document type based on move type"""
        for move in self:
            # 1. Initialisation par défaut
            teif_type = False

            # 2. Extraction des variables pour éviter les appels répétés (Performance & Lisibilité)
            m_type = move.move_type
            company = move.company_id
            partner = move.partner_id
            is_foreign_curr = move.currency_id != company.currency_id

            # 3. Logique de décision hiérarchisée
            if m_type == 'out_refund':
                teif_type = 'I-12'

            elif m_type == 'out_invoice':
                if partner.public_company or move.is_decamp:
                    teif_type = 'I-14'
                elif company.honoraire_use:
                    teif_type = 'I-13'
                elif is_foreign_curr:
                    teif_type = 'I-15'
                else:
                    teif_type = 'I-11'
            print('partner.public_company', partner.public_company)
            print('company.honoraire_use', company.honoraire_use)
            print('is_foreign_curr', is_foreign_curr)
            # 4. Affectation unique
            move.teif_document_type = teif_type

    def get_ttn_payment_info(self):
        """Get TTN payment information from payment term"""
        self.ensure_one()
        payment_info = {
            'payment_terms_code': False,
            'payment_means_code': False,
            'payment_condition_code': 'I-121',
            'payment_description': False,
            'financial_institution_code': 'I-142',
            'financial_institution': False,
        }

        if self.invoice_payment_term_id:
            term = self.invoice_payment_term_id
            payment_info['payment_terms_code'] = term.ttn_payment_terms_code
            payment_info['payment_means_code'] = term.ttn_payment_means_code
            payment_info['payment_condition_code'] = term.ttn_payment_condition_code or 'I-121'
            payment_info['payment_description'] = term.get_ttn_payment_description()
            payment_info['financial_institution_code'] = term.ttn_payment_institution_code
            payment_info['financial_institution'] = term.ttn_financial_institution

        return payment_info

    # =====================================
    # STEP 1: Generate TEIF XML
    # =====================================

    def action_generate_teif_xml(self):
        """Generate TEIF XML from invoice"""
        self.ensure_one()
        if self.move_type not in ['out_invoice', 'out_refund']:
            raise UserError(_("La génération TEIF est disponible uniquement pour les factures clients"))

        company_fiscal_id = self.company_id.get_tn_fiscal_id()
        if not company_fiscal_id:
            raise UserError(_("Le matricule fiscal de la société n'est pas configuré dans le champ NIF/TVA"))

        partner_fiscal_id = self.partner_id.get_tn_fiscal_id()
        if not partner_fiscal_id:
            raise UserError(_("Le matricule fiscal du client n'est pas configuré dans le champ NIF/TVA"))

        try:
            teif_gen = self.env['teif.generator']
            xml_content = teif_gen.generate_teif_xml(self)
            self.write({
                'teif_xml': xml_content,
                'teif_status': 'generated',
                'teif_error_message': False,
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        except Exception as e:
            _logger.error("Error generating TEIF XML: %s", str(e))
            self.write({
                'teif_status': 'error',
                'teif_error_message': str(e)
            })
            raise UserError(_("Erreur lors de la génération du XML TEIF:\n%s") % str(e))

    # =====================================
    # STEP 2: Sign with ANCE ONLY
    # =====================================
    def action_sign_with_ngsign(self):
        """Sign TEIF XML with NGSign - Generate proper JSON payload"""
        self.ensure_one()

        company = self.company_id
        if not company.ngsign_api_token:
            raise UserError(_("Le token API ANCE n'est pas configuré"))

        try:
            # Step 1: Generate TEIF XML if not exists
            if not self.teif_xml:
                self.action_generate_teif_xml()

            # Step 2: Encode TEIF XML to base64
            teif_xml_bytes = self.teif_xml.encode('utf-8')
            teif_xml_b64 = base64.b64encode(teif_xml_bytes).decode('utf-8')

            # Step 3: Generate PDF invoice
            report = self.env.ref('account.account_invoices')
            pdf_content, dummy = report.sudo()._render_qweb_pdf(
                report_ref='account.account_invoices',
                res_ids=self.ids
            )

            # Validate PDF
            if pdf_content[:4] != b'%PDF':
                raise UserError(_("Erreur: Le système a généré du HTML au lieu d'un PDF. "
                                  "Vérifiez wkhtmltopdf."))

            # Step 4: Encode PDF to base64
            pdf_b64 = base64.b64encode(pdf_content).decode('utf-8')

            # Step 5: Prepare ANCE API payload
            url = f"{company.ngsign_api_url}/xml/transaction/create/"

            headers = {
                'Authorization': f'Bearer {company.ngsign_api_token}',
                'Content-Type': 'application/json'
            }

            payload = {
                'signerEmail': company.email or 'noreply@company.tn',
                'invoices': [{
                    'invoiceNumber': self._get_ttn_invoice_name(),
                    'invoiceTIEF': teif_xml_b64,  # XML TEIF encodé en base64
                    'invoiceFileB64': pdf_b64,  # PDF encodé en base64
                }]
            }

            _logger.info("Signing invoice %s with ANCE", self.name)

            # Step 6: Send to ANCE API
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()

                print('Response', result)
                transaction_uuid = result.get('object', {}).get('uuid')
                invoice = next(
                    (inv for inv in result['object']['invoices']
                     if inv['invoiceNumber'] == self._get_ttn_invoice_name()),
                    None
                )

                invoice_uuid = invoice['uuid'] if invoice else None
                # Get signing URL
                signing_url = f"{company.ngsign_api_url.replace('/server/protected/invoice', '')}/pds/#/teif/invoice/{transaction_uuid}"

                self.write({
                    'teif_ngsign_uuid': invoice_uuid,
                    'ngsign_transaction_uuid': transaction_uuid,
                    'teif_status': 'sent_ngsign',
                    'teif_error_message': False,
                })

                return {
                    'type': 'ir.actions.act_url',
                    'url': signing_url,
                    'target': 'new',
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                _logger.error("ANCE API error: %s", error_msg)
                self.write({
                    'teif_status': 'error',
                    'teif_error_message': error_msg
                })
                raise UserError(_("Erreur ANCE:\n%s") % error_msg)

        except Exception as e:
            _logger.error("Error signing with ANCE: %s", str(e))
            self.write({
                'teif_status': 'error',
                'teif_error_message': str(e)
            })
            raise UserError(_("Erreur lors de la signature:\n%s") % str(e))

    def action_download_signed_xml_from_ngsign(self):
        """Download signed XML from ANCE"""
        for rec in self:

            if not rec.teif_ngsign_uuid:
                return

            company = rec.company_id
            url = f"{company.ngsign_api_url}/xml/xml/{rec.teif_ngsign_uuid}"

            headers = {
                'Authorization': f'Bearer {company.ngsign_api_token}'
            }

            try:
                response = requests.get(url, headers=headers, timeout=30)
                if response.status_code == 200:
                    signed_xml = response.json()
                    b64_data = signed_xml["object"]
                    xml_bytes = base64.b64decode(b64_data)
                    xml_string = xml_bytes.decode("utf-8")
                    is_signed = self._check_xml_signature(xml_string)

                    try:
                        dom = xml.dom.minidom.parseString(xml_string)
                        pretty_xml = dom.toprettyxml(indent="  ")
                        # Remove empty lines
                        pretty_xml = "\n".join(line for line in pretty_xml.split("\n") if line.strip())
                    except Exception as e:
                        # Fallback if XML parsing fails
                        pretty_xml = xml_string
                    print('Is Signed', is_signed)
                    print('pretty_xml', pretty_xml)
                    if is_signed:
                        rec.write({
                            'teif_signed_xml': pretty_xml,
                            'teif_status': 'signed',
                        })
                        _logger.info("Signed XML downloaded for invoice %s", rec.name)

                        # Auto-submit to TTN if configured
                        if company.ttn_auto_submit:
                            rec.action_submit_to_ttn()
                    else:
                        rec.write({
                            'teif_signed_xml': pretty_xml,
                            'teif_status': 'sent_ngsign',
                        })
                        _logger.warning("XML received but not signed (missing SigFrs) for invoice %s", rec.name)
            except Exception as e:
                _logger.error("Error downloading signed XML: %s", str(e))

    def _check_xml_signature(self, xml_string):
        """Check if XML contains ds:Signature element with id='SigFrs'"""
        try:
            from lxml import etree

            # Parse XML
            root = etree.fromstring(xml_string.encode('utf-8'))

            # Define namespace
            namespaces = {
                'ds': 'http://www.w3.org/2000/09/xmldsig#'
            }

            # Search for Signature element with id="SigFrs"
            signature = root.xpath('//ds:Signature[@Id="SigFrs"]', namespaces=namespaces)

            return len(signature) > 0

        except ImportError:
            # Fallback to xml.etree if lxml is not available
            import xml.etree.ElementTree as ET

            try:
                root = ET.fromstring(xml_string)

                # Search for Signature element with namespace
                namespace = '{http://www.w3.org/2000/09/xmldsig#}'

                for elem in root.iter(f'{namespace}Signature'):
                    if elem.get('Id') == 'SigFrs':
                        return True

                return False

            except Exception as e:
                _logger.error("Error parsing XML for signature check: %s", str(e))
                return False

        except Exception as e:
            _logger.error("Error checking XML signature: %s", str(e))
            return False
    # =====================================
    # STEP 3: Submit to TTN via SOAP
    # =====================================

    def action_submit_to_ttn(self):
        """Submit signed invoice to TTN via SOAP (saveEfact)"""
        self.ensure_one()

        if not self.teif_signed_xml:
            raise UserError(_("Le XML signé n'est pas disponible. Veuillez d'abord signer avec ANCE"))

        if not self.company_id.ttn_soap_url:
            raise UserError(_("L'URL du serveur SOAP TTN n'est pas configurée"))

        try:
            ttn_connector = self.env['ttn.connector']
            result = ttn_connector.submit_invoice_to_ttn(self)
            print('Result : ', result)
            if result['success']:
                # Store the idSaveEfact returned by TTN

                self.write({
                    'teif_ttn_id_save': result.get('idSaveEfact'),
                    'teif_status': 'sent_ttn',
                    'teif_error_message': False,
                    'teif_ttn_message': result.get('message'),
                })

                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            else:
                error_msg = result.get('message', 'Erreur inconnue')
                self.write({
                    'teif_status': 'error',
                    'teif_error_message': error_msg,
                    'teif_ttn_message': error_msg,
                })
                raise UserError(_("Erreur TTN:\n%s") % error_msg)

        except Exception as e:
            _logger.error("Error submitting to TTN: %s", str(e))
            self.write({
                'teif_status': 'error',
                'teif_error_message': str(e)
            })
            raise UserError(_("Erreur lors de la soumission à TTN:\n%s") % str(e))

    # =====================================
    # STEP 4: Check TTN Status (consultEfact)
    # =====================================

    def action_check_ttn_status(self):
        """Check invoice status on TTN using consultEfact"""
        self.ensure_one()

        if not self.name:
            raise UserError(_("Aucun numéro de facture disponible"))

        try:
            ttn_connector = self.env['ttn.connector']

            # Prepare search criteria
            criteria = {
                'documentNumber': self._get_ttn_invoice_name(),
            }

            if self.teif_ttn_id_save:
                criteria['idSaveEfact'] = self.teif_ttn_id_save

            if self.teif_ttn_reference:
                criteria['generatedRef'] = self.teif_ttn_reference

            # Consult TTN - retourne déjà des données sérialisées
            results = ttn_connector.consult_invoice_from_ttn(self, criteria)
            if not results:
                raise UserError(_("Aucune facture trouvée sur TTN pour le numéro: %s") % self.name)

            # ✅ CORRECTION: Les données sont déjà sérialisées, pas besoin de serialize_object
            efact_data = results[0] if results else {}

            _logger.info(f"Parsed efact_data type: {type(efact_data)}")
            _logger.info(f"Parsed efact_data keys: {efact_data.keys() if efact_data else 'empty'}")

            if not efact_data:
                raise UserError(_("Données vides retournées par TTN"))

            # Update invoice with TTN data
            vals = {
                'teif_ttn_reference': efact_data.get('generatedRef'),
                'teif_ttn_id_save': efact_data.get('idSaveEfact'),
                'teif_ttn_validation_date': efact_data.get('dateProcess').replace(tzinfo=None) if efact_data.get('dateProcess') else False,
            }

            # Check if we have the sealed XML
            if efact_data.get('xmlContent'):
                vals['teif_sealed_xml'] = efact_data['xmlContent']
                vals['teif_status'] = 'ttn_validated'
                vals['teif_ttn_validation_date'] = efact_data.get('dateProcess').replace(tzinfo=None) if efact_data.get('dateProcess') else False

                self.write(vals)
                # Try to extract QR code from XML if present
                self._extract_qr_from_sealed_xml(efact_data['xmlContent'])
            # ✅ Si tout est OK, rafraîchir la page

            # Check for acknowledgments (errors/warnings)
            acknowledgments = efact_data.get('listAcknowlegments', [])
            if acknowledgments:
                ack_messages = []
                for ack in acknowledgments:
                    # Get the errors list from each acknowledgment
                    errors = ack.get('errors', [])
                    for error in errors:
                        has_errors = True
                        error_id = error.get('errorId')
                        error_desc = error.get('errorDescription', '').strip()
                        ack_messages.append(f"[{error_id}] {error_desc}")
                if ack_messages:
                    vals['teif_error_message'] = '\n'.join(ack_messages)

                # Update status based on presence of errors
                if has_errors:
                    vals['teif_status'] = 'ttn_rejected'

            self.write(vals)

            if vals.get('teif_status') == 'ttn_validated':
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            # Prepare notification message
            notification_msg = _('Référence TTN: %s') % efact_data.get('generatedRef', 'N/A')
            if acknowledgments:
                notification_msg += '\n' + _('Acquittements: %d') % len(acknowledgments)

            notification_type = 'success' if vals.get('teif_status') == 'ttn_validated' else 'warning'

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

        except Exception as e:
            _logger.error("Error checking TTN status: %s", str(e))
            raise UserError(_("Erreur lors de la vérification du statut:\n%s") % str(e))

    # =====================================
    # STEP 5: Download Sealed Invoice
    # =====================================

    def action_download_sealed_invoice(self):
        """Download sealed invoice with QR code from TTN using consultEfact"""
        self.ensure_one()

        if not self.teif_ttn_reference and not self.name:
            raise UserError(_("Aucune référence TTN ou numéro de facture disponible"))

        try:
            ttn_connector = self.env['ttn.connector']

            # Prepare search criteria - prefer generatedRef if available
            criteria = {}
            if self.teif_ttn_reference:
                criteria['generatedRef'] = self.teif_ttn_reference
            else:
                criteria['documentNumber'] = self._get_ttn_invoice_name()

            # Consult TTN
            results = ttn_connector.consult_invoice_from_ttn(self, criteria)

            if not results:
                raise UserError(_("Aucune facture trouvée sur TTN"))

            efact_data = results[0]

            # Check if sealed XML is available
            if not efact_data.get('xmlContent'):
                raise UserError(
                    _("Le XML scellé n'est pas encore disponible sur TTN. La facture est peut-être en cours de traitement."))
            print('date Time ', efact_data.get('dateProcess').replace(tzinfo=None))
            vals = {
                'teif_sealed_xml': efact_data['xmlContent'],
                'teif_ttn_reference': efact_data.get('generatedRef'),
                'teif_ttn_id_save': efact_data.get('idSaveEfact'),
                'teif_ttn_validation_date': efact_data.get('dateProcess').replace(tzinfo=None) if efact_data.get('dateProcess') else False,
                'teif_status': 'ttn_validated',
            }

            # Extract QR code from sealed XML
            qr_code = self._extract_qr_from_sealed_xml(efact_data['xmlContent'])
            if qr_code:
                vals['teif_qr_code'] = qr_code

            # Handle attachments if any
            attachments = efact_data.get('listAttachement', [])
            if attachments:
                self._process_ttn_attachments(attachments)

            self.write(vals)
            _logger.info("Sealed invoice downloaded for %s with reference %s",
                         self.name, efact_data.get('generatedRef'))

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

        except Exception as e:
            _logger.error("Error downloading sealed invoice: %s", str(e))
            raise UserError(_("Erreur lors du téléchargement:\n%s") % str(e))

    # =====================================
    # Helper Methods
    # =====================================
    def _extract_qr_from_sealed_xml(self, sealed_xml):
        """Extract QR code from sealed XML"""
        try:
            # Gérer les deux formats : bytes ou string
            if isinstance(sealed_xml, bytes):
                xml_bytes = sealed_xml
            elif isinstance(sealed_xml, str):
                xml_bytes = sealed_xml.encode('utf-8')
            else:
                _logger.warning("sealed_xml has unexpected type: %s", type(sealed_xml))
                return None

            root = etree.fromstring(xml_bytes)

            # Look for QR code in common locations
            # Adjust namespace and path based on actual TTN sealed XML structure
            # Définir les namespaces
            namespaces = {
                'ds': 'http://www.w3.org/2000/09/xmldsig#'
            }

            # Extraire le ReferenceCEV
            ref_cev = root.find('.//ReferenceCEV', namespaces)
            if ref_cev is not None and ref_cev.text:
                # Le ReferenceCEV contient déjà l'image PNG en base64
                # On la stocke directement dans le champ binaire
                qr_code = ref_cev.text.strip()
            else:
                qr_code = False

            return qr_code

        except Exception as e:
            _logger.warning("Could not extract QR code from sealed XML: %s", str(e))

        return None

    def _process_ttn_attachments(self, attachments):
        """Process attachments from TTN consultEfact response"""
        IrAttachment = self.env['ir.attachment']

        for att in attachments:
            filename = att.get('filename')
            content = att.get('content')

            if filename and content:
                try:
                    # Content is likely base64 encoded
                    IrAttachment.create({
                        'name': filename,
                        'type': 'binary',
                        'datas': content,
                        'res_model': self._name,
                        'res_id': self.id,
                        'description': 'TTN Attachment',
                    })
                    _logger.info("Attachment %s created for invoice %s", filename, self.name)
                except Exception as e:
                    _logger.warning("Could not create attachment %s: %s", filename, str(e))

    # =====================================
    # Combined Action: Submit & Monitor
    # =====================================

    def action_submit_and_monitor_ttn(self):
        """Submit to TTN and immediately check status"""
        self.ensure_one()

        # Submit
        self.action_submit_to_ttn()

        # Wait a bit for TTN processing
        import time
        time.sleep(2)

        # Check status
        try:
            self.action_check_ttn_status()
        except Exception as e:
            _logger.warning("Could not check status immediately after submission: %s", str(e))

        return True

    # =====================================
    # Cron Job: Auto-check pending invoices
    # =====================================

    @api.model
    def _cron_check_ttn_pending_invoices(self):
        """Cron job to check status of invoices pending on TTN"""
        pending_invoices = self.search([
            ('teif_status', 'in', ['sent_ttn']),
            ('teif_signed_xml', '!=', False),
        ])

        for invoice in pending_invoices:
            try:
                invoice.action_check_ttn_status()
                self.env.cr.commit()
            except Exception as e:
                _logger.error("Error checking status for invoice %s: %s", invoice.name, str(e))
                continue

    # ===== COMPUTE METHODS FOR BINARY FIELDS =====
    @api.depends('teif_xml')
    def _compute_teif_xml_file(self):
        """Convert teif_xml text to downloadable binary file"""
        for record in self:
            if record.teif_xml:
                xml_bytes = record.teif_xml.encode('utf-8')
                record.teif_xml_file = base64.b64encode(xml_bytes)
            else:
                record.teif_xml_file = False

    @api.depends('name', 'teif_xml')
    def _compute_teif_xml_filename(self):
        """Generate filename for TEIF XML"""
        for record in self:
            if record.name and record.teif_xml:
                clean_name = record.name.replace('/', '_')
                record.teif_xml_filename = f'TEIF_{clean_name}.xml'
            else:
                record.teif_xml_filename = False

    @api.depends('teif_signed_xml')
    def _compute_teif_signed_xml_file(self):
        """Convert teif_signed_xml text to downloadable binary file"""
        for record in self:
            if record.teif_signed_xml:
                xml_bytes = record.teif_signed_xml.encode('utf-8')
                record.teif_signed_xml_file = base64.b64encode(xml_bytes)
            else:
                record.teif_signed_xml_file = False

    @api.depends('name', 'teif_signed_xml')
    def _compute_teif_signed_xml_filename(self):
        """Generate filename for signed TEIF XML"""
        for record in self:
            if record.name and record.teif_signed_xml:
                clean_name = record.name.replace('/', '_')
                record.teif_signed_xml_filename = f'TEIF_SIGNED_{clean_name}.xml'
            else:
                record.teif_signed_xml_filename = False

    @api.depends('teif_sealed_xml')
    def _compute_teif_sealed_xml_file(self):
        """Convert teif_sealed_xml text to downloadable binary file"""
        for record in self:
            if record.teif_sealed_xml:
                xml_bytes = record.teif_sealed_xml.encode('utf-8')
                record.teif_sealed_xml_file = base64.b64encode(xml_bytes)
            else:
                record.teif_sealed_xml_file = False

    @api.depends('name', 'teif_sealed_xml')
    def _compute_teif_sealed_xml_filename(self):
        """Generate filename for sealed TEIF XML"""
        for record in self:
            if record.name and record.teif_sealed_xml:
                clean_name = record.name.replace('/', '_')
                record.teif_sealed_xml_filename = f'TEIF_SEALED_TTN_{clean_name}.xml'
            else:
                record.teif_sealed_xml_filename = False

    def button_draft(self):
        """Override reset to draft to check TEIF status"""
        # Vérifier le statut TEIF avant de réinitialiser
        for move in self:
            if move.teif_status not in ['draft', 'generated', False]:
                raise UserError(_(
                    "Vous ne pouvez pas réinitialiser cette facture à l'état brouillon.\n"
                    "La facture '%s' a le statut TEIF '%s'.\n"
                    "Seules les factures avec le statut 'Non Signé' ou 'XML Généré' "
                    "peuvent être réinitialisées."
                ) % (move.name, dict(move._fields['teif_status'].selection).get(move.teif_status)))
            if move.teif_status == 'generated':
                move.sudo().write({
                    'teif_status': 'draft',
                    'teif_error_message': False,
                    'teif_xml': False,
                })

        return super(AccountMove, self).button_draft()

    def button_cancel(self):
        """Override cancel to check TEIF status"""
        # Vérifier le statut TEIF avant d'annuler
        for move in self:
            if move.teif_status not in ['draft', 'generated', False]:
                raise UserError(_(
                    "Vous ne pouvez pas annuler cette facture.\n"
                    "La facture '%s' a le statut TEIF '%s'.\n"
                    "Les factures signées ou envoyées à TTN ne peuvent pas être annulées."
                ) % (move.name, dict(move._fields['teif_status'].selection).get(move.teif_status)))
            if move.teif_status == 'generated':
                move.sudo().write({
                    'teif_status': 'draft',
                    'teif_error_message': False,
                    'teif_xml': False,
                })
        return super(AccountMove, self).button_cancel()

    def unlink(self):
        """Override delete to check TEIF status"""
        # Vérifier le statut TEIF avant de supprimer
        for move in self:
            if move.teif_status not in ['draft', 'generated', False]:
                raise UserError(_(
                    "Vous ne pouvez pas supprimer cette facture.\n"
                    "La facture '%s' a le statut TEIF '%s'.\n"
                    "Seules les factures avec le statut 'Non Signé' ou 'XML Généré' "
                    "peuvent être supprimées."
                ) % (move.name, dict(move._fields['teif_status'].selection).get(move.teif_status)))

        return super(AccountMove, self).unlink()

    def write(self, vals):
        """Override write to prevent modification of critical fields when TEIF is validated"""
        # Vérifier si on essaie de modifier des champs critiques
        protected_fields = [
            'partner_id', 'invoice_line_ids', 'amount_total',
            'invoice_date', 'currency_id', 'company_id'
        ]

        if any(field in vals for field in protected_fields):
            for move in self:
                if move.teif_status in ['ttn_validated', 'sent_ttn']:
                    raise UserError(_(
                        "Vous ne pouvez pas modifier cette facture.\n"
                        "La facture '%s' a été envoyée ou validée par TTN (statut: %s).\n"
                        "Les modifications ne sont plus autorisées."
                    ) % (move.name, dict(move._fields['teif_status'].selection).get(move.teif_status)))

        return super(AccountMove, self).write(vals)