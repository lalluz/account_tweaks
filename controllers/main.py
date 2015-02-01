# -*- coding: utf-8 -*-

import base64

if __name__ == '__main__':
    import sys
    sys.path.insert (0, '/home/guido/src/openerp/server')

import openerp
import openerp.http as http
from openerp.http import request
from openerp.report.report_sxw import rml_parse

from openerp import SUPERUSER_ID

from collections import OrderedDict


TEMPLATE = '''
<style type="text/css">
  #liquidazione-iva {
    padding: 20px 10px;
  }

  #liquidazione-iva table td:last-child {
    padding-left: 40px;
    text-align: right;
  }
</style>

<div id="liquidazione-iva">
  <h2>Liquidazione IVA</h2>
  <table>
    <tr>
      <td>IVA a debito:</td>
      <td>%(debit_vat_amount).2f</td>
    </tr>
    <tr>
      <td>IVA a credito:</td>
      <td>%(credit_vat_amount).2f</td>
    </tr>
    <tr>
      <td>IVA a credito non detraibile:</td>
      <td>%(credit_n_vat_amount).2f</td>
    </tr>
    <tr>
      <td>IVA a credito non detraibile pro rata:</td>
      <td>%(credit_prorata_vat_amount).2f</td>
    </tr>

    <tr><td>&#160;<td></tr>

    <tr>
      <td>Ricavi 74ter CEE:</td>
      <td>%(debit_74ter_cee).2f</td>
    </tr>
    <tr>
      <td>Costi 74ter CEE:</td>
      <td>%(credit_74ter_cee).2f</td>
    </tr>
    <tr>
      <td>Guadagni 74ter CEE:</td>
      <td>%(amount_74ter_cee).2f</td>
    </tr>
    <tr>
      <td>Credito di costo 74ter:</td>
      <td>%(total_previous_74ter_credit).2f</td>
    </tr>
    <tr>
      <td>IVA 74ter:</td>
      <td>%(net_vat_74ter).2f</td>
    </tr>
  </table>
</div>
'''


def _get_liquidazione_iva (registry, cr, period_id, state):
    AccountPeriod = registry.get ('account.period')

    period = AccountPeriod.browse (cr, SUPERUSER_ID, [period_id])[0]

    liquidazione = period._compute_liquidazione (None, None, {'state': state}).items ()[0][1]

    liquidazione.update (period._total_previous_74ter_credit ().items ()[0][1])

    return liquidazione


class LiquidazioneIvaController (http.Controller):

    _cp_path = '/liquidazione-iva'

    @http.route ('/liquidazione-iva/json_url', type='json')
    def json_url (self, period_id=None, state=None):
        return TEMPLATE % _get_liquidazione_iva (
            request.registry,
            request.cr,
            period_id,
            state,
        )


class CompanyVsPrivateCustomerInvoicesActionController (http.Controller):

    _cp_path = '/company_vs_private_customer_invoices'

    def get_results (self, pool, cr, uid, start, end):
        account_invoice_obj = pool.get ('account.invoice')
        account_invoice_tax_obj = pool.get ('account.invoice.tax')
        util_parser = rml_parse (cr, uid, 'internal')
        util_parser.objects = [] #  FIXME
        util_parser.setLang ('it_IT') #  FIXME

        invoice_ids = account_invoice_obj.search (cr, uid, [
            ('type', 'in', ['out_invoice', 'out_refund']),
            ('date_invoice', '>=', start),
            ('date_invoice', '<=', end),
        ], order='number')
        invoice_tax_ids = account_invoice_tax_obj.search (cr, uid, [
            ('invoice_id', 'in', invoice_ids),
            ('tax_amount', '!=', 0),
        ])

        invoice_taxes = account_invoice_tax_obj.browse (
            cr, uid, invoice_tax_ids)

        tax_map = OrderedDict ()
        for tax in sorted (invoice_taxes, key=lambda t: t.invoice_id.number):
            tax.rate = int (round (tax.tax_amount * 100 / tax.base_amount))

            tax_map.setdefault (tax.invoice_id, []).append (tax)
            tax_map[tax.invoice_id].sort (key=lambda t: t.rate)

        char_attrs = "oe_list_field_cell oe_list_field_char"
        num_attrs = "oe_list_field_cell oe_list_field_float oe_number"
        date_attrs = "oe_list_field_cell oe_list_field_date"

        header_attrs = "oe_list_header"

        def to_number(number):
            return number if '/' not in number else number.split ('/')[-1]

        html = '<table class="oe_list_content"><tbody>'
        html += '<thead><tr class="oe_list_header_columns">'
        html += '<td class="%s">Kind</td>' % header_attrs
        html += '<td class="%s">Date</td>' % header_attrs
        html += '<td class="%s">Number</td>' % header_attrs
        html += '<td class="%s">Base Amount</td>' % header_attrs
        html += '<td class="%s">Tax Rate</td>' % header_attrs
        html += '<td class="%s">Tax Amount</td>' % header_attrs
        html += '<td class="%s">Total Amount</td>' % header_attrs
        html += '</tr></thead>'

        private_total_map = {}
        company_total_map = {}
        total_map = {}

        for invoice, taxes in tax_map.items ():
            kind = 'Company' if invoice.partner_id.vat else 'Private'
            for tax in taxes:
                html += '<tr>'
                html += '<td class="%s">%s</td>' % (char_attrs, kind)
                html += '<td class="%s">%s</td>' % (date_attrs, tax.invoice_id.date_invoice)
                html += '<td class="%s">%s</td>' % (num_attrs, to_number (tax.invoice_id.number))
                html += '<td class="%s">%s</td>' % (num_attrs, util_parser.formatLang (tax.base_amount))
                html += '<td class="%s">%d%%</td>' % (num_attrs, tax.rate)
                html += '<td class="%s">%s</td>' % (num_attrs, util_parser.formatLang (tax.tax_amount))
                html += '<td class="%s">%s</td>' % (num_attrs, util_parser.formatLang (tax.base_amount + tax.tax_amount))
                html += '</tr>'

                total_map.setdefault (tax.rate, {'base': 0, 'tax': 0, 'total': 0})
                total_map[tax.rate]['base'] += tax.base_amount
                total_map[tax.rate]['tax'] += tax.tax_amount
                total_map[tax.rate]['total'] += tax.base_amount + tax.tax_amount

                if kind == 'Company':
                    company_total_map.setdefault (tax.rate, {'base': 0, 'tax': 0, 'total': 0})
                    company_total_map[tax.rate]['base'] += tax.base_amount
                    company_total_map[tax.rate]['tax'] += tax.tax_amount
                    company_total_map[tax.rate]['total'] += tax.base_amount + tax.tax_amount
                else:
                    private_total_map.setdefault (tax.rate, {'base': 0, 'tax': 0, 'total': 0})
                    private_total_map[tax.rate]['base'] += tax.base_amount
                    private_total_map[tax.rate]['tax'] += tax.tax_amount
                    private_total_map[tax.rate]['total'] += tax.base_amount + tax.tax_amount

        html += '</tbody></table>'

        def get_column_headers ():
            html = '<thead><tr class="oe_list_header_columns">'
            html += '<td class="%s">Base Amount</td>' % header_attrs
            html += '<td class="%s">Rate</td>' % header_attrs
            html += '<td class="%s">Tax Amount</td>' % header_attrs
            html += '<td class="%s">Total Amount</td>' % header_attrs
            html += '</tr></thead>'

            return html

        def get_totals_table (title, t_map):
            html = '<h2 style="margin-top: 20px; margin-bottom: 10px;">%s</h2>' % title
            html += '<table class="oe_list_content"><tbody>'
            html += get_column_headers ()

            for rate, totals in t_map.items ():
                html += '<tr>'
                html += '<td class="%s">%s</td>' % (num_attrs, util_parser.formatLang (totals['base']))
                html += '<td class="%s">%d%%</td>' % (num_attrs, rate)
                html += '<td class="%s">%s</td>' % (num_attrs, util_parser.formatLang (totals['tax']))
                html += '<td class="%s">%s</td>' % (num_attrs, util_parser.formatLang (totals['total']))
                html += '</tr>'

            html += '</tbody></table>'

            return html

        html += get_totals_table ('Private Amounts', private_total_map)
        html += get_totals_table ('Company Amounts', company_total_map)
        html += get_totals_table ('Total Amounts', total_map)

        return html

    @http.route ('/company_vs_private_customer_invoices/json_url', type='json')
    def json_url (self, start=None, end=None):
        return self.get_results (request.registry, request.cr, request.uid, start, end)


if __name__ == '__main__':
    from openerp.modules.registry import RegistryManager

    from openerp.netsvc import init_logger
    init_logger ()

    import pprint

    registry = RegistryManager.get (sys.argv[1], update_module=False)
    cr = registry.db.cursor ()

    AccountPeriod = registry.get ('account.period')
    period_code = '01/2014' if len (sys.argv) < 2 else sys.argv[1]
    period_id = AccountPeriod.search (cr, SUPERUSER_ID, [('code', '=', period_code)])[0]

    liquidazione_iva = _get_liquidazione_iva (registry, cr, period_id, 'all')

    print "\nLiquidazione IVA for %s\n" % period_code
    pprint.pprint (liquidazione_iva.items ())
    print ""

    cr.close ()

