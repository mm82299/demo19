# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging
import base64
import os
from datetime import datetime
import re

_logger = logging.getLogger(__name__)

# Try to import zeep, fallback to manual SOAP if not available
try:
    from zeep import Client, Settings
    from zeep.transports import Transport
    from zeep.exceptions import Fault, TransportError, XMLSyntaxError, Error as ZeepError
    from zeep.cache import SqliteCache
    from requests import Session

    ZEEP_AVAILABLE = True
    _logger.info("✅ Zeep library available - using for SOAP communication")
except ImportError:
    ZEEP_AVAILABLE = False
    _logger.warning("⚠️  Zeep library not available - falling back to manual SOAP")
    import requests
    from lxml import etree


class TtnConnector(models.AbstractModel):
    _name = 'ttn.connector'
    _description = 'TTN El Fatoora SOAP API Connector'

    # ========== PUBLIC API METHODS ==========

    @api.model
    def submit_invoice_to_ttn(self, invoice):
        """Submit signed TEIF XML to TTN via SOAP API (saveEfact operation)"""
        if not invoice.teif_signed_xml:
            raise UserError(_("Le XML signé n'est pas disponible"))

        company = invoice.company_id
        self._validate_ttn_config(company)

        try:
            if ZEEP_AVAILABLE:
                result = self._submit_with_zeep(invoice, company)
            else:
                result = self._submit_with_lxml(invoice, company)

            _logger.info("Invoice %s submitted to TTN. Result: %s",
                         invoice.name, result.get('message'))

            return result

        except UserError:
            raise
        except Exception as e:
            _logger.error("Error submitting invoice %s to TTN: %s",
                          invoice.name, str(e), exc_info=True)
            raise UserError(_("Erreur lors de la soumission à TTN:\n%s") % str(e))

    @api.model
    def consult_invoice_from_ttn(self, invoice, criteria=None):
        """Consult invoice from TTN via SOAP API (consultEfact operation)"""
        company = invoice.company_id
        self._validate_ttn_config(company)

        try:
            if not criteria:
                criteria = {'documentNumber': invoice._get_ttn_invoice_name()}

            if ZEEP_AVAILABLE:
                result = self._consult_with_zeep(invoice, company, criteria)
            else:
                result = self._consult_with_lxml(invoice, company, criteria)
            print('ZEEP_AVAILABLE', ZEEP_AVAILABLE)
            print('result', result)
            _logger.info("Invoice %s consulted from TTN. Found %d results",
                         invoice.name, len(result))

            return result

        except UserError:
            raise
        except Exception as e:
            _logger.error("Error consulting invoice from TTN: %s", str(e), exc_info=True)
            raise UserError(_("Erreur lors de la consultation TTN:\n%s") % str(e))

    @api.model
    def verify_qr_code(self, qr_code_data, company):
        """Verify QR code from TTN via SOAP API (verifyQrCode operation)"""
        self._validate_ttn_config(company)

        try:
            if ZEEP_AVAILABLE:
                result = self._verify_qr_with_zeep(qr_code_data, company)
            else:
                result = self._verify_qr_with_lxml(qr_code_data, company)

            return result

        except UserError:
            raise
        except Exception as e:
            _logger.error("Error verifying QR code: %s", str(e), exc_info=True)
            raise UserError(_("Erreur lors de la vérification du QR code:\n%s") % str(e))

    @api.model
    def test_ttn_connection(self, company):
        """Test connection to TTN WSDL and service endpoint"""
        if not company.ttn_soap_url:
            raise UserError(_("L'URL du serveur SOAP TTN n'est pas configurée"))

        results = {
            'zeep_available': ZEEP_AVAILABLE,
            'wsdl_accessible': False,
            'wsdl_content': None,
            'service_accessible': False,
            'namespace': None,
            'operations': [],
            'errors': []
        }

        try:
            wsdl_url = company.ttn_soap_url + '?wsdl'
            _logger.info("Testing WSDL access: %s", wsdl_url)

            if ZEEP_AVAILABLE:
                # Test with Zeep
                try:
                    transport = Transport(timeout=10, operation_timeout=10)
                    settings = Settings(strict=False, xml_huge_tree=True)
                    client = Client(wsdl_url, transport=transport, settings=settings)

                    results['wsdl_accessible'] = True
                    results['namespace'] = client.wsdl.target_namespace
                    results['operations'] = [op for op in client.service._operations.keys()]

                    _logger.info("✅ WSDL accessible via Zeep")
                    _logger.info("Target Namespace: %s", results['namespace'])
                    _logger.info("Operations: %s", results['operations'])

                except Exception as e:
                    results['errors'].append(f"Zeep error: {str(e)}")
                    _logger.error("Zeep WSDL test failed: %s", str(e))
            else:
                # Test with requests
                import requests
                response = requests.get(wsdl_url, timeout=10, verify=True)

                if response.status_code == 200:
                    results['wsdl_accessible'] = True
                    results['wsdl_content'] = response.text[:2000]
                    _logger.info("✅ WSDL accessible")
                else:
                    results['errors'].append(f"HTTP {response.status_code}: {response.reason}")

        except Exception as e:
            results['errors'].append(f"Connection error: {str(e)}")
            _logger.error("Error testing TTN connection: %s", str(e))

        return results

    # ========== VALIDATION ==========

    def _validate_ttn_config(self, company):
        """Validate TTN configuration"""
        if not company.ttn_soap_url:
            raise UserError(_("L'URL du serveur SOAP TTN n'est pas configurée"))

        if not all([company.ttn_soap_username, company.ttn_soap_password, company.vat]):
            raise UserError(_(
                "Les identifiants TTN ne sont pas configurés.\n"
                "Vérifiez: login, password, matricule fiscal"
            ))

        if not company.ttn_soap_url.startswith(('http://', 'https://')):
            raise UserError(_("L'URL SOAP doit commencer par http:// ou https://"))

        _logger.info("TTN Config - URL: %s, Username: %s, Matricule: %s",
                     company.ttn_soap_url, company.ttn_soap_username, company.vat[:8])

    # ========== ZEEP IMPLEMENTATION ==========

    def _get_zeep_client(self, company):
        """Create and configure Zeep client"""
        try:
            # Configure session with timeout
            session = Session()
            session.verify = False  # SSL verification

            # Configure transport with timeouts
            transport = Transport(
                session=session,
                timeout=30,  # Timeout for WSDL/XSD loading
                operation_timeout=company.ttn_soap_timeout or 30  # Timeout for operations
            )

            # Configure settings
            settings = Settings(
                strict=False,  # Be lenient with WSDL compliance
                xml_huge_tree=True,  # Support large XML documents
                xsd_ignore_sequence_order=True  # More flexible parsing
            )

            # Create client with WSDL
            wsdl_url = company.ttn_soap_url + '?wsdl'
            client = Client(wsdl_url, transport=transport, settings=settings)

            _logger.info("Zeep client created successfully")
            _logger.info("Available operations: %s", list(client.service._operations.keys()))

            return client

        except Exception as e:
            _logger.error("Error creating Zeep client: %s", str(e), exc_info=True)
            raise UserError(_(
                "Impossible de créer le client SOAP.\n"
                "Vérifiez l'URL et la disponibilité du WSDL:\n%s\n\n"
                "Erreur: %s"
            ) % (company.ttn_soap_url, str(e)))

    def _submit_with_zeep(self, invoice, company):
        """Submit invoice using Zeep"""
        try:
            client = self._get_zeep_client(company)

            # Encode document as base64
            xml_bytes = invoice.teif_signed_xml.encode('utf-8')
            document_b64 = base64.b64encode(xml_bytes).decode('utf-8')
            print('XMl Teif', xml_bytes)

            # Save debug files
            self._save_debug_file(f'ttn_request_{invoice.name}_zeep.txt',
                                  f"login={company.ttn_soap_username}\n"
                                  f"matricule={company.get_tn_fiscal_id()}\n"
                                  f"document_size={len(document_b64)} bytes")

            _logger.info("=" * 80)
            _logger.info("CALLING TTN saveEfact via Zeep")
            _logger.info("=" * 80)
            _logger.info("Login: %s", company.ttn_soap_username)
            _logger.info("Matricule: %s", company.get_tn_fiscal_id())
            _logger.info("Document size: %d bytes (base64)", len(xml_bytes))

            # ⚠️ CORRECTION: Pass arguments by POSITION, not by name
            # Signature: arg0=login, arg1=password, arg2=matricule, arg3=documentEfact
            response = client.service.saveEfact(
                company.ttn_soap_username,  # arg0: login
                company.ttn_soap_password,  # arg1: password
                company.get_tn_fiscal_id(),  # arg2: matricule
                xml_bytes  # arg3: documentEfact (base64Binary)
            )

            _logger.info("Response received: %s", response)
            self._save_debug_file(f'ttn_response_{invoice.name}_zeep.txt', str(response))

            # Parse response
            result = {
                'success': False,
                'message': None,
                'id_save_efact': None
            }

            if response:
                if isinstance(response, str):
                    result['message'] = response
                    message_lower = response.lower()
                    # Extraire l'ID de la réponse
                    match = re.search(r'ID\s+(\d+)', response)
                    if match:
                        result['id_save_efact'] = int(match.group(1))
                    if any(keyword in message_lower for keyword in
                           ['success', 'validé', 'accepté', 'enregistree', 'succès']):
                        result['success'] = True
                elif isinstance(response, dict):
                    result['message'] = response.get('message') or response.get('return')
                    result['id_save_efact'] = response.get('idSaveEfact')
                    result['success'] = response.get('success', False)
                else:
                    # Handle object response
                    result['message'] = str(response)

            _logger.info("=" * 80)

            return result

        except Fault as fault:
            # SOAP Fault - extract TTN error details
            error_msg = self._parse_zeep_fault(fault)
            _logger.error("SOAP Fault: %s", error_msg)
            raise UserError(error_msg)

        except TransportError as e:
            _logger.error("Transport error: %s", str(e))
            raise UserError(_(
                "Erreur de communication avec TTN:\n"
                "Status: %s\n"
                "Message: %s"
            ) % (e.status_code if hasattr(e, 'status_code') else 'Unknown', str(e)))

        except XMLSyntaxError as e:
            _logger.error("XML Syntax error: %s", str(e))
            raise UserError(_("Erreur de syntaxe XML:\n%s") % str(e))

        except ZeepError as e:
            _logger.error("Zeep error: %s", str(e))
            raise UserError(_("Erreur Zeep:\n%s") % str(e))

        except TypeError as e:
            # Handle signature mismatch
            _logger.error("Type error (signature mismatch): %s", str(e))
            raise UserError(_(
                "Erreur de signature SOAP:\n%s\n\n"
                "Vérifiez que les paramètres sont passés dans le bon ordre."
            ) % str(e))

    def _consult_with_zeep(self, invoice, company, criteria):
        """Consult invoice using Zeep"""
        try:
            client = self._get_zeep_client(company)

            _logger.info("Calling TTN consultEfact via Zeep")
            _logger.info("Criteria: %s", criteria)

            # ✅ CORRECTION: Créer explicitement l'objet complexType
            # Récupérer le type complexe depuis le WSDL
            criteria_type = client.get_type('ns0:efactCriteria')

            # Créer l'objet avec les valeurs du dictionnaire
            criteria_obj = criteria_type(**criteria)

            _logger.info("Created criteria object: %s", criteria_obj)

            # Appel SOAP avec l'objet Zeep
            response = client.service.consultEfact(
                company.ttn_soap_username,  # arg0: login
                company.ttn_soap_password,  # arg1: password
                company.get_tn_fiscal_id(),  # arg2: matricule
                criteria_obj  # arg3: efactCriteria object (pas dict)
            )

            _logger.info("consultEfact response: %s", response)

            # Parse response
            results = []
            if response:
                # Sérialiser la réponse Zeep en dict Python
                from zeep.helpers import serialize_object
                serialized = serialize_object(response, dict)

                if isinstance(serialized, list):
                    for item in serialized:
                        results.append(self._parse_efact_item(item))
                else:
                    results.append(self._parse_efact_item(serialized))

            _logger.info("Invoice %s consulted from TTN. Found %d results",
                         invoice.name, len(results))

            return results

        except Fault as fault:
            error_msg = self._parse_zeep_fault(fault)
            _logger.error("SOAP Fault: %s", error_msg)
            raise UserError(error_msg)

        except Exception as e:
            _logger.error("Consultation error: %s", str(e), exc_info=True)
            raise UserError(_("Erreur lors de la consultation TTN:\n%s") % str(e))

    def _verify_qr_with_zeep(self, qr_code_data, company):
        """Verify QR code using Zeep"""
        try:
            client = self._get_zeep_client(company)

            _logger.info("Calling TTN verifyQrCode via Zeep")

            # ⚠️ CORRECTION: Pass arguments by POSITION
            # Signature: arg0=login, arg1=password, arg2=matricule, arg3=qrCode
            response = client.service.verifyQrCode(
                company.ttn_soap_username,  # arg0: login
                company.ttn_soap_password,  # arg1: password
                company.get_tn_fiscal_id(),  # arg2: matricule
                qr_code_data  # arg3: qrCode
            )

            _logger.info("verifyQrCode response: %s", response)

            result = {
                'valid': False,
                'message': None
            }

            if response:
                if isinstance(response, str):
                    result['message'] = response
                    if any(keyword in response.lower() for keyword in ['valid', 'valide']):
                        result['valid'] = True
                elif isinstance(response, dict):
                    result['message'] = response.get('message')
                    result['valid'] = response.get('valid', False)
                else:
                    result['message'] = str(response)

            return result

        except Fault as fault:
            error_msg = self._parse_zeep_fault(fault)
            _logger.error("SOAP Fault: %s", error_msg)
            raise UserError(error_msg)

        except TypeError as e:
            _logger.error("Type error: %s", str(e))
            raise UserError(_("Erreur de signature SOAP:\n%s") % str(e))

    def _parse_zeep_fault(self, fault):
        """Parse Zeep Fault exception to extract TTN error details"""
        error_msg = f"Erreur SOAP: {fault.message}"

        try:
            # Try to extract FaultBean details from fault.detail
            if hasattr(fault, 'detail') and fault.detail is not None:
                from lxml import etree

                if isinstance(fault.detail, etree._Element):
                    # Search for faultCode and faultMessage
                    for elem in fault.detail.iter():
                        if 'faultCode' in elem.tag:
                            fault_code = elem.text
                        if 'faultMessage' in elem.tag:
                            fault_message = elem.text
                            error_msg = f"Erreur TTN [{fault_code}]: {fault_message}"
                            break
        except Exception as e:
            _logger.warning("Could not parse fault detail: %s", str(e))

        return error_msg

    def _parse_efact_item(self, item):
        """Parse consultEfact response item"""
        print('Item', item)
        if item:
            efact_data = {
                'documentNumber': item['documentNumber'],
                'idSaveEfact': item['idSaveEfact'],
                'documentType': item['documentType'],
                'dateProcess': item['dateProcess'],
                'dateDocument': item['dateDocument'],
                'amountTax': item['amountTax'],
                'amount': item['amount'],
                'generatedRef': item['generatedRef'],
                'xmlContent': None,
                'listAcknowlegments': item['listAcknowlegments'],
                'listAttachement': item['listAttachement']
            }

            # Decode xmlContent if present
            if item.get('xmlContent'):
                try:
                    efact_data['xmlContent'] = base64.b64decode(item['xmlContent']).decode('utf-8')
                except:
                    efact_data['xmlContent'] = item['xmlContent']
            print('efact_data', efact_data)
            return efact_data

        return {}

    # ========== LXML FALLBACK IMPLEMENTATION ==========
    # (Keep all the previous lxml implementation methods here as fallback)

    def _submit_with_lxml(self, invoice, company):
        """Fallback: Submit invoice using manual SOAP with lxml"""
        _logger.info("Using lxml fallback for saveEfact")

        soap_request = self._build_soap_save_efact_request(
            company.ttn_soap_username,
            company.ttn_soap_password,
            company.get_tn_fiscal_id(),
            invoice.teif_signed_xml
        )

        self._save_debug_file(f'ttn_request_{invoice.name}.xml', soap_request)

        response = self._send_soap_request(
            company.ttn_soap_url,
            soap_request,
            company.ttn_soap_timeout or 30
        )

        self._save_debug_file(f'ttn_response_{invoice.name}.xml', response)

        return self._parse_save_efact_response(response)

    def _consult_with_lxml(self, invoice, company, criteria):
        """Fallback: Consult using lxml"""
        _logger.info("Using lxml fallback for consultEfact")

        soap_request = self._build_soap_consult_efact_request(
            company.ttn_soap_username,
            company.ttn_soap_password,
            company.get_tn_fiscal_id(),
            criteria
        )

        response = self._send_soap_request(
            company.ttn_soap_url,
            soap_request,
            company.ttn_soap_timeout or 30
        )

        return self._parse_consult_efact_response(response)

    def _verify_qr_with_lxml(self, qr_code_data, company):
        """Fallback: Verify QR using lxml"""
        _logger.info("Using lxml fallback for verifyQrCode")

        soap_request = self._build_soap_verify_qr_request(
            company.ttn_soap_username,
            company.ttn_soap_password,
            company.get_tn_fiscal_id(),
            qr_code_data
        )

        response = self._send_soap_request(
            company.ttn_soap_url,
            soap_request,
            company.ttn_soap_timeout or 30
        )

        return self._parse_verify_qr_response(response)

    def _build_soap_save_efact_request(self, login, password, matricule, xml_content):
        """Build SOAP request for saveEfact operation (lxml fallback)"""
        SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
        TNS = "http://services.elfatoura.tradenet.com.tn/"

        envelope = etree.Element(
            f"{{{SOAP_NS}}}Envelope",
            nsmap={'soapenv': SOAP_NS, 'ser': TNS}
        )
        body = etree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
        save_efact = etree.SubElement(body, f"{{{TNS}}}saveEfact")

        etree.SubElement(save_efact, f"{{{TNS}}}login").text = login
        etree.SubElement(save_efact, f"{{{TNS}}}password").text = password
        etree.SubElement(save_efact, f"{{{TNS}}}matricule").text = matricule

        document_elem = etree.SubElement(save_efact, f"{{{TNS}}}documentEfact")
        xml_bytes = xml_content.encode('utf-8')
        document_elem.text = base64.b64encode(xml_bytes).decode('ascii')

        return etree.tostring(envelope, pretty_print=False, xml_declaration=True, encoding='UTF-8')

    def _build_soap_consult_efact_request(self, login, password, matricule, criteria):
        """Build SOAP request for consultEfact (lxml fallback)"""
        SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
        TNS = "http://services.elfatoura.tradenet.com.tn/"

        envelope = etree.Element(f"{{{SOAP_NS}}}Envelope", nsmap={'soapenv': SOAP_NS, 'ser': TNS})
        body = etree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
        consult_efact = etree.SubElement(body, f"{{{TNS}}}consultEfact")

        etree.SubElement(consult_efact, f"{{{TNS}}}login").text = login
        etree.SubElement(consult_efact, f"{{{TNS}}}password").text = password
        etree.SubElement(consult_efact, f"{{{TNS}}}matricule").text = matricule

        criteria_elem = etree.SubElement(consult_efact, f"{{{TNS}}}efactCriteria")
        for key, value in criteria.items():
            if value:
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d')
                etree.SubElement(criteria_elem, f"{{{TNS}}}{key}").text = str(value)

        return etree.tostring(envelope, pretty_print=False, xml_declaration=True, encoding='UTF-8')

    def _build_soap_verify_qr_request(self, login, password, matricule, qr_data):
        """Build SOAP request for verifyQrCode (lxml fallback)"""
        SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
        TNS = "http://services.elfatoura.tradenet.com.tn/"

        envelope = etree.Element(f"{{{SOAP_NS}}}Envelope", nsmap={'soapenv': SOAP_NS, 'ser': TNS})
        body = etree.SubElement(envelope, f"{{{SOAP_NS}}}Body")
        verify_qr = etree.SubElement(body, f"{{{TNS}}}verifyQrCode")

        etree.SubElement(verify_qr, f"{{{TNS}}}login").text = login
        etree.SubElement(verify_qr, f"{{{TNS}}}password").text = password
        etree.SubElement(verify_qr, f"{{{TNS}}}matricule").text = matricule
        etree.SubElement(verify_qr, f"{{{TNS}}}qrCode").text = qr_data

        return etree.tostring(envelope, pretty_print=False, xml_declaration=True, encoding='UTF-8')

    def _send_soap_request(self, url, soap_request, timeout=30):
        """Send SOAP request (lxml fallback)"""
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '""',
            'Accept': 'text/xml, application/xml',
        }

        response = requests.post(url, data=soap_request, headers=headers, timeout=timeout, verify=True)
        response.raise_for_status()
        return response.content

    def _parse_save_efact_response(self, response):
        """Parse saveEfact response (lxml fallback)"""
        root = etree.fromstring(response)
        SOAP_NS = "{http://schemas.xmlsoap.org/soap/envelope/}"
        TNS = "{http://services.elfatoura.tradenet.com.tn/}"

        # Check for fault
        fault = root.find(f".//{SOAP_NS}Fault")
        if fault is not None:
            raise UserError(_("SOAP Fault: %s") % etree.tostring(fault, encoding='unicode'))

        body = root.find(f"{SOAP_NS}Body")
        save_response = body.find(f"{TNS}saveEfactResponse")

        result = {'success': False, 'message': None, 'id_save_efact': None}

        if save_response is not None:
            return_elem = save_response.find(f'{TNS}return')
            if return_elem is not None and return_elem.text:
                result['message'] = return_elem.text
                if any(kw in return_elem.text.lower() for kw in ['success', 'validé', 'accepté']):
                    result['success'] = True

        return result

    def _parse_consult_efact_response(self, response):
        """Parse consultEfact response (lxml fallback)"""
        # Implement similar to previous version
        return []

    def _parse_verify_qr_response(self, response):
        """Parse verifyQrCode response (lxml fallback)"""
        # Implement similar to previous version
        return {'valid': False, 'message': None}

    # ========== HELPERS ==========

    def _save_debug_file(self, filename, content):
        """Save debug files for troubleshooting"""
        try:
            debug_dir = '/tmp/ttn_debug'
            os.makedirs(debug_dir, exist_ok=True)

            safe_filename = filename.replace('/', '_').replace('\\', '_')
            filepath = os.path.join(debug_dir, safe_filename)

            if isinstance(content, bytes):
                with open(filepath, 'wb') as f:
                    f.write(content)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(str(content))

            _logger.debug("Debug file saved: %s", filepath)

        except Exception as e:
            _logger.warning("Could not save debug file: %s", str(e))
