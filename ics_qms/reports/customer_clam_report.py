from odoo import models, fields, _
import io
import base64

class CustomerClamXlsx(models.AbstractModel):
    _name = 'report.ics_qms.report_customer_clam_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Customer Claim XLSX Report'

    def generate_xlsx_report(self, workbook, data, wizard):
        # The 'wizard' argument here is the wizard record because I'm calling it from the wizard
        date_start = wizard.date_start
        date_end = wizard.date_end

        claims = self.env['customer.clam'].search([
            ('date', '>=', date_start),
            ('date', '<=', date_end)
        ], order='date asc')

        worksheet = workbook.add_worksheet('Registre des Réclamations')

        # Formats
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#f2f2f2'
        })
        title_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'size': 14, 'border': 1
        })
        cell_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})
        left_cell_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1})
        info_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'border': 1, 'size': 10})

        # Set Column Widths
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 12)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 25)
        worksheet.set_column('F:F', 15)
        worksheet.set_column('G:G', 12)
        worksheet.set_column('H:H', 12)
        worksheet.set_column('I:I', 15)

        # Header Section
        company = self.env.company
        if company.logo:
            logo_data = base64.b64decode(company.logo)
            image_data = io.BytesIO(logo_data)
            worksheet.insert_image('A1', 'logo.png', {'image_data': image_data, 'x_scale': 0.15, 'y_scale': 0.15, 'x_offset': 5, 'y_offset': 5})
        
        worksheet.merge_range('A1:B3', '', title_format)
        worksheet.merge_range('C1:E1', 'Information documentée', info_format)
        worksheet.merge_range('C2:E3', 'REGISTRE DES RECLAMATIONS CLIENTS', title_format)
        worksheet.merge_range('F1:G1', 'Code: ENR-COM-03', info_format)
        worksheet.merge_range('H1:I1', 'Version: 00', info_format)
        worksheet.merge_range('F2:G3', 'Date: ' + fields.Date.today().strftime('%d/%m/%Y'), info_format)
        worksheet.merge_range('H2:I3', 'Page : 1 sur 1', info_format)

        # Table Headers
        worksheet.merge_range('A5:A6', 'Réclamation N°', header_format)
        worksheet.merge_range('B5:B6', 'Date', header_format)
        worksheet.merge_range('C5:C6', 'Client', header_format)
        worksheet.merge_range('D5:D6', 'Objet de la réclamation', header_format)
        worksheet.merge_range('E5:E6', 'Action', header_format)
        worksheet.merge_range('F5:H5', 'Suivi de la réclamation', header_format)
        worksheet.write('F6', 'Responsable', header_format)
        worksheet.write('G6', 'Échéance', header_format)
        worksheet.write('H6', 'Date Clôture', header_format)
        worksheet.merge_range('I5:I6', 'N° fiche de NC', header_format)

        # Rows
        row = 6
        for claim in claims:
            worksheet.write(row, 0, claim.name or '', cell_format)
            worksheet.write(row, 1, claim.date.strftime('%d/%m/%Y') if claim.date else '', cell_format)
            worksheet.write(row, 2, claim.partner_id.name or '', cell_format)
            worksheet.write(row, 3, claim.description or '', left_cell_format)
            worksheet.write(row, 4, claim.action.name if claim.action else '', left_cell_format)
            worksheet.write(row, 5, claim.responsible_id.name or '', cell_format)
            worksheet.write(row, 6, claim.date_limit.strftime('%d/%m/%Y') if claim.date_limit else '', cell_format)
            worksheet.write(row, 7, claim.date_close.strftime('%d/%m/%Y') if claim.date_close else '', cell_format)
            worksheet.write(row, 8, claim.num_nc_file or '', cell_format)
            row += 1
